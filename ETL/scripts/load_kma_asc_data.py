"""
SKALA Physical Risk AI System - KMA ASC 기후 데이터 로딩
ASC 파일에서 기후 데이터를 각 기후 데이터 테이블에 로딩

최종 수정일: 2025-11-19
버전: v01

호출: 수동 실행
"""

import sys
import re
import gzip
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import date
from collections import defaultdict
import numpy as np
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir


# SSP scenario mapping
SSP_CODE_MAP = {
    "SSP126": "SSP1-2.6",
    "SSP245": "SSP2-4.5",
    "SSP370": "SSP3-7.0",
    "SSP585": "SSP5-8.5"
}

# Variable mapping to table names (daily/monthly admin data)
VARIABLE_TABLE_MAP = {
    "TAMAX": {"table": "tamax_data", "is_admin": True, "resolution": "daily"},
    "TAMIN": {"table": "tamin_data", "is_admin": True, "resolution": "daily"},
    "TA": {"table": "ta_data", "is_admin": False, "resolution": "monthly"},  # Grid data
    "RN": {"table": "rn_data", "is_admin": False, "resolution": "monthly"},  # Grid data
    "WS": {"table": "ws_data", "is_admin": False, "resolution": "monthly"},  # Grid data
    "RHM": {"table": "rhm_data", "is_admin": False, "resolution": "monthly"},  # Grid data
    "SI": {"table": "si_data", "is_admin": False, "resolution": "monthly"},  # Grid data
}


def parse_asc_file(asc_file: Path, logger) -> Dict:
    """
    Parse gzip-compressed tar archive ASC file and return structured data

    File format:
    - Tar header lines (skip)
    - 3 Korean header lines with "년-월-일" (skip)
    - Data lines: YYYY-MM-DD,value1,value2,...,value261

    Returns:
        Dictionary with structure: {(year, month, day): {region_idx: value}}
    """
    logger.debug(f"Parsing {asc_file.name}")

    data = {}

    try:
        with gzip.open(asc_file, 'rt', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return data

        # Skip tar header and Korean headers - find first data line
        data_start_idx = 0
        for i, line in enumerate(lines):
            line = line.strip()
            # Data lines start with YYYY-MM-DD format
            if line and '-' in line and not line.startswith('년-월-일'):
                parts = line.split(',')
                if len(parts) > 1 and parts[0].count('-') == 2:
                    # Check if first part looks like a date
                    try:
                        date_parts = parts[0].split('-')
                        int(date_parts[0])  # Try to parse year
                        data_start_idx = i
                        break
                    except:
                        continue

        # Parse data lines
        for line in lines[data_start_idx:]:
            if not line.strip():
                continue

            parts = line.strip().split(',')
            if len(parts) < 2:  # Need at least date,value
                continue

            # Parse date in YYYY-MM-DD format
            try:
                date_str = parts[0]
                date_parts = date_str.split('-')
                year = int(date_parts[0])
                month = int(date_parts[1])
                day = int(date_parts[2])
            except:
                continue

            # Store values for each region (261 regions)
            region_values = {}
            for i, val_str in enumerate(parts[1:], start=1):
                if val_str and val_str.strip():
                    try:
                        value = float(val_str)
                        if not np.isnan(value):
                            region_values[i] = value
                    except ValueError:
                        continue

            if region_values:
                data[(year, month, day)] = region_values

        return data

    except Exception as e:
        logger.error(f"Failed to parse {asc_file.name}: {e}")
        return {}


def load_admin_daily_data(
    conn,
    logger,
    asc_files: Dict[str, Path],
    variable: str,
    table_name: str
) -> None:
    """
    Load daily administrative region data (TAMAX, TAMIN)

    Table structure: time (date), admin_id (int), ssp1-5 (real)
    """
    logger.info(f"📊 Loading {variable} data into {table_name}...")

    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    existing = cursor.fetchone()[0]

    if existing > 0:
        logger.info(f"   ℹ️  Data already exists ({existing} rows)")
        response = input(f"   Clear {table_name} and reload? (y/N): ")
        if response.lower() != 'y':
            logger.info("   Skipping")
            cursor.close()
            return
        cursor.execute(f"TRUNCATE TABLE {table_name}")
        conn.commit()

    # Get admin region mapping (admin_id from location_admin)
    # Assume regions 1-261 map to admin_ids
    cursor.execute("SELECT admin_id FROM location_admin WHERE level = 2 ORDER BY admin_id LIMIT 261")
    admin_ids = [row[0] for row in cursor.fetchall()]

    if len(admin_ids) < 261:
        logger.warning(f"   ⚠️  Only found {len(admin_ids)} level-2 admin regions (expected 261)")

    # Parse all SSP scenarios
    logger.info("   📂 Parsing ASC files...")
    ssp_data = {}

    for ssp_code, asc_file in asc_files.items():
        if not asc_file.exists():
            logger.warning(f"      ⚠️  File not found: {asc_file}")
            continue

        scenario_name = SSP_CODE_MAP.get(ssp_code)
        if not scenario_name:
            continue

        data = parse_asc_file(asc_file, logger)
        ssp_data[ssp_code] = data
        logger.info(f"      ✅ Parsed {ssp_code}: {len(data)} time steps")

    if not ssp_data:
        logger.warning("   ⚠️  No data parsed")
        cursor.close()
        return

    # Combine data from all scenarios
    logger.info("   💾 Inserting data...")

    # Get all unique time steps
    all_times = set()
    for data in ssp_data.values():
        all_times.update(data.keys())

    insert_sql = f"""
    INSERT INTO {table_name} (time, admin_id, ssp1, ssp2, ssp3, ssp5)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    success_count = 0

    for time_tuple in tqdm(sorted(all_times), desc=f"   {table_name}"):
        year, month, day = time_tuple
        time_date = date(year, month, day)

        # For each admin region
        for region_idx, admin_id in enumerate(admin_ids, start=1):
            # Collect values from all SSP scenarios
            ssp_values = {
                'ssp1': None,
                'ssp2': None,
                'ssp3': None,
                'ssp5': None
            }

            for ssp_code, ssp_col in [("SSP126", "ssp1"), ("SSP245", "ssp2"),
                                       ("SSP370", "ssp3"), ("SSP585", "ssp5")]:
                if ssp_code in ssp_data:
                    region_data = ssp_data[ssp_code].get(time_tuple, {})
                    ssp_values[ssp_col] = region_data.get(region_idx)

            # Skip if all values are None
            if all(v is None for v in ssp_values.values()):
                continue

            cursor.execute(insert_sql, (
                time_date,
                admin_id,
                ssp_values['ssp1'],
                ssp_values['ssp2'],
                ssp_values['ssp3'],
                ssp_values['ssp5']
            ))
            success_count += 1

        # Commit periodically
        if success_count % 10000 == 0:
            conn.commit()

    conn.commit()
    cursor.close()

    logger.info(f"   ✅ Loaded {success_count} records into {table_name}")


def load_all_kma_asc_data() -> None:
    """
    Main function to load all KMA ASC climate data
    """
    logger = setup_logging("load_kma_asc_data")
    logger.info("=" * 60)
    logger.info("Loading KMA ASC Climate Data")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    data_dir = get_data_dir()
    kma_dir = data_dir / "KMA" / "extracted" / "KMA" / "downloads_kma_ssp_sgg261"

    if not kma_dir.exists():
        logger.error(f"❌ Directory not found: {kma_dir}")
        logger.info("   Make sure ZIP files are extracted first")
        conn.close()
        sys.exit(1)

    try:
        # Load TAMAX (daily, admin)
        tamax_files = {}
        for ssp in ["SSP126", "SSP245", "SSP370", "SSP585"]:
            file_path = kma_dir / ssp / "daily" / f"{ssp}_TAMAX_sgg261_daily_2021-2100.asc"
            if file_path.exists():
                tamax_files[ssp] = file_path

        if tamax_files:
            load_admin_daily_data(conn, logger, tamax_files, "TAMAX", "tamax_data")

        logger.info("")

        # Load TAMIN (daily, admin)
        tamin_files = {}
        for ssp in ["SSP126", "SSP245", "SSP370", "SSP585"]:
            file_path = kma_dir / ssp / "daily" / f"{ssp}_TAMIN_sgg261_daily_2021-2100.asc"
            if file_path.exists():
                tamin_files[ssp] = file_path

        if tamin_files:
            load_admin_daily_data(conn, logger, tamin_files, "TAMIN", "tamin_data")

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ KMA ASC data loading complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("⚠️  Note: Only TAMAX and TAMIN (admin-level daily) loaded")
        logger.info("   Other variables (TA, RN, WS, etc.) are grid-based")
        logger.info("   and would require grid location mapping")

    except Exception as e:
        logger.error(f"❌ Error during data loading: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    load_all_kma_asc_data()
