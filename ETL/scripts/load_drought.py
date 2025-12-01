"""
SKALA Physical Risk AI System - 가뭄 데이터 로딩
MODIS 및 SMAP HDF/H5 파일을 raw_drought 테이블에 로딩

최종 수정일: 2025-11-20
버전: v01

호출: load_data.sh
"""

import sys
import os
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def extract_modis_date(filename):
    """
    Extract observation date from MODIS filename

    Example: MOD13Q1.A2025289.h15v00.061.2025306093723.hdf
    -> 2025289 = Year 2025, Day 289
    """
    match = re.search(r'A(\d{7})', filename)
    if match:
        date_str = match.group(1)
        year = int(date_str[:4])
        day_of_year = int(date_str[4:])
        date_obj = datetime(year, 1, 1) + timedelta(days=day_of_year - 1)
        return date_obj.strftime("%Y-%m-%d")
    return None


def extract_smap_date(filename):
    """
    Extract observation date from SMAP filename

    Example: SMAP_L4_SM_aup_20251114T000000_Vv8011_001.h5
    -> 20251114 = 2025-11-14
    """
    match = re.search(r'_(\d{8})T', filename)
    if match:
        date_str = match.group(1)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return None


def load_hdf_to_postgres(hdf_path, table_name, data_source, obs_date, append=False, logger=None):
    """
    Load HDF/H5 file subdatasets into PostgreSQL using GDAL + raster2pgsql

    Args:
        hdf_path: Path to HDF/H5 file
        table_name: Target table name
        data_source: Data source name (MODIS, SMAP)
        obs_date: Observation date
        append: If True, append to table
        logger: Logger instance

    Returns:
        Number of successful subdatasets loaded
    """
    success_count = 0

    try:
        # Get DB credentials
        db_host = os.getenv("DW_HOST", "localhost")
        db_port = os.getenv("DW_PORT", "5433")
        db_name = os.getenv("DW_NAME", "skala_datawarehouse")
        db_user = os.getenv("DW_USER", "skala_dw_user")
        db_password = os.getenv("DW_PASSWORD", "skala_dev_2025")

        # Get list of subdatasets using gdalinfo
        gdalinfo_cmd = ["gdalinfo", str(hdf_path)]
        gdalinfo_proc = subprocess.run(
            gdalinfo_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )

        if gdalinfo_proc.returncode != 0:
            if logger:
                logger.warning(f"⚠️  gdalinfo failed: {gdalinfo_proc.stderr.decode()}")
            return 0

        # Parse subdatasets from gdalinfo output
        output = gdalinfo_proc.stdout.decode()
        subdatasets = []
        for line in output.split('\n'):
            if 'SUBDATASET_' in line and '_NAME=' in line:
                # Extract subdataset path
                parts = line.split('=', 1)
                if len(parts) == 2:
                    subdatasets.append(parts[1].strip())

        if not subdatasets:
            # No subdatasets, treat as single raster
            subdatasets = [str(hdf_path)]

        if logger:
            logger.info(f"      Found {len(subdatasets)} subdataset(s)")

        # Check SAMPLE_LIMIT for subdatasets
        sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
        if sample_limit > 0 and len(subdatasets) > sample_limit:
            if logger:
                logger.info(f"      ⚠️  샘플 모드: {sample_limit}개 subdataset만 로딩합니다")
            subdatasets = subdatasets[:sample_limit]

        # Load each subdataset
        for idx, subdataset in enumerate(subdatasets):
            try:
                # Use raster2pgsql to load subdataset
                cmd = ["raster2pgsql"]

                if append or idx > 0:
                    cmd.append("-a")  # Append
                else:
                    cmd.append("-c")  # Create

                cmd.extend([
                    "-I",  # Create index
                    "-C",  # Constraints
                    "-M",  # Vacuum
                    "-F",  # Filename
                    "-t", "100x100",  # Tile size
                    "-s", "4326",  # SRID (WGS84 for global data)
                    subdataset,
                    table_name
                ])

                raster_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                psql_cmd = [
                    "psql",
                    "-h", db_host,
                    "-p", db_port,
                    "-U", db_user,
                    "-d", db_name,
                    "-q"
                ]

                psql_env = os.environ.copy()
                if db_password:
                    psql_env["PGPASSWORD"] = db_password

                psql_proc = subprocess.Popen(
                    psql_cmd,
                    stdin=raster_proc.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=psql_env
                )

                raster_proc.stdout.close()
                stdout, stderr = psql_proc.communicate(timeout=120)

                if psql_proc.returncode == 0:
                    success_count += 1
                else:
                    if logger:
                        logger.warning(f"⚠️  Subdataset {idx+1} failed")

            except Exception as e:
                if logger:
                    logger.warning(f"⚠️  Subdataset {idx+1} error: {e}")
                continue

        return success_count

    except Exception as e:
        if logger:
            logger.warning(f"⚠️  Error: {e}")
        return 0


def load_drought():
    """
    Load drought data from MODIS and SMAP HDF/H5 files

    Source: data/drought/*.hdf and *.h5
    Target: raw_drought table
    """
    logger = setup_logging("load_drought")
    logger.info("=" * 60)
    logger.info("Loading Drought Data (MODIS/SMAP)")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Check if table exists
    if not table_exists(conn, "raw_drought"):
        logger.error("❌ Table 'raw_drought' does not exist. Run create_tables.sh first.")
        conn.close()
        sys.exit(1)

    # Check if data already exists
    existing_count = get_row_count(conn, "raw_drought")
    if existing_count > 0:
        logger.warning(f"⚠️  Table already contains {existing_count} rows")
        response = input("Do you want to clear and reload? (y/N): ")
        if response.lower() != 'y':
            logger.info("Skipping load")
            conn.close()
            return

        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS raw_drought CASCADE")
        conn.commit()
        cursor.close()
        logger.info("✅ Table dropped, will recreate")

    conn.close()

    # Get data directory
    data_dir = get_data_dir()
    drought_dir = data_dir / "drought"

    if not drought_dir.exists():
        logger.error(f"❌ Drought directory not found: {drought_dir}")
        sys.exit(1)

    # Find HDF and H5 files
    hdf_files = list(drought_dir.glob("*.hdf"))
    h5_files = list(drought_dir.glob("*.h5"))

    all_files = hdf_files + h5_files

    logger.info(f"📂 Found {len(hdf_files)} HDF files and {len(h5_files)} H5 files")
    logger.info(f"   Total: {len(all_files)} files to process")
    logger.info("")
    logger.info("⚠️  This will use GDAL + raster2pgsql")
    logger.info("⚠️  HDF/H5 files contain multiple subdatasets")

    success_count = 0
    error_count = 0
    first_file = True

    # Process all HDF/H5 files
    for hdf_file in tqdm(all_files, desc="Processing HDF/H5"):
        try:
            # Determine data source and observation date
            if "MOD13Q1" in hdf_file.name or "MODIS" in hdf_file.name:
                data_source = "MODIS"
                obs_date = extract_modis_date(hdf_file.name)
            elif "SMAP" in hdf_file.name:
                data_source = "SMAP"
                obs_date = extract_smap_date(hdf_file.name)
            else:
                data_source = "Unknown"
                obs_date = None

            logger.info(f"   Processing {hdf_file.name} ({data_source}, {obs_date})")

            # Load file
            loaded = load_hdf_to_postgres(
                hdf_file,
                "raw_drought",
                data_source,
                obs_date,
                append=not first_file,
                logger=logger
            )

            if loaded > 0:
                success_count += loaded
                first_file = False
                logger.info(f"      ✅ Loaded {loaded} subdatasets")
            else:
                error_count += 1
                logger.warning(f"      ❌ Failed to load")

        except Exception as e:
            logger.warning(f"⚠️  Error processing {hdf_file.name}: {e}")
            error_count += 1
            continue

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"✅ Drought data loading complete!")
    logger.info(f"   Success: {success_count} subdatasets")
    logger.info(f"   Errors: {error_count} files")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_drought()
