"""
SKALA Physical Risk AI System - 연별 그리드 기후 데이터 로딩
KMA 연별 그리드 NetCDF 데이터를 해당 테이블에 로딩

최종 수정일: 2025-11-20
버전: v01

호출: load_data.sh
"""

import sys
import os
import tarfile
import tempfile
from pathlib import Path
import netCDF4 as nc
import numpy as np
from tqdm import tqdm
from datetime import datetime, timedelta

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


# Variable mapping to table names (yearly grid data)
VARIABLE_MAPPING = {
    "CSDI": "csdi_data",           # 한랭야 계속기간 지수
    "RX1DAY": "rx1day_data",       # 1일 최다강수량
    "RX5DAY": "rx5day_data",       # 5일 최다강수량
    "CDD": "cdd_data",             # 연속 무강수일
    "WSDI": "wsdi_data",           # 고온 계속기간 지수
    "RAIN80": "rain80_data",       # 80mm 이상 강수일수
    "SDII": "sdii_data",           # 강수강도
    "TA": "ta_yearly_data",        # 연평균 기온
}

# SSP scenario mapping
SSP_MAPPING = {
    "SSP126": 1,
    "SSP245": 2,
    "SSP370": 3,
    "SSP585": 4,
}


def extract_netcdf_from_targz(targz_path):
    """
    Extract NetCDF file from .tar.gz archive

    Args:
        targz_path: Path to .tar.gz file

    Returns:
        Path to extracted NetCDF file
    """
    tmpdir = tempfile.mkdtemp()

    with tarfile.open(targz_path, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) == 0:
            raise ValueError(f"Empty tar archive: {targz_path}")

        # Extract first member (should be the NetCDF file)
        tar.extract(members[0], path=tmpdir)
        extracted_file = os.path.join(tmpdir, members[0].name)

    return extracted_file


def load_grid_locations(ds, conn, logger):
    """
    Load grid locations from NetCDF into location_grid table

    Args:
        ds: NetCDF dataset
        conn: Database connection
        logger: Logger instance
    """
    cursor = conn.cursor()

    # Check if locations already exist
    existing_count = get_row_count(conn, "location_grid")
    if existing_count > 0:
        logger.info(f"   Grid locations already exist ({existing_count} points), skipping...")
        cursor.close()
        return

    logger.info(f"   Loading grid locations...")

    lons = ds.variables['longitude'][:]
    lats = ds.variables['latitude'][:]

    # Create grid points
    insert_sql = """
    INSERT INTO location_grid (
        grid_id, longitude, latitude, geom
    ) VALUES (
        %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)
    )
    ON CONFLICT (grid_id) DO NOTHING
    """

    grid_id = 0
    batch = []
    batch_size = 1000

    for lat in tqdm(lats, desc="Latitude", leave=False):
        for lon in lons:
            grid_id += 1
            batch.append((grid_id, float(lon), float(lat), float(lon), float(lat)))

            if len(batch) >= batch_size:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                batch = []

    # Insert remaining
    if batch:
        cursor.executemany(insert_sql, batch)
        conn.commit()

    cursor.close()
    logger.info(f"   ✅ Loaded {grid_id} grid locations")


def load_variable_data(var_short, table_name, nc_files, conn, logger):
    """
    Load yearly variable data from NetCDF files into database

    Args:
        var_short: Variable short name (e.g., 'CSDI')
        table_name: Target table name (e.g., 'csdi_data')
        nc_files: List of NetCDF file paths
        conn: Database connection
        logger: Logger instance
    """
    cursor = conn.cursor()

    # 샘플 모드 확인
    sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
    valid_grid_ids = None
    if sample_limit > 0:
        logger.info(f"   ⚠️  샘플 모드: {sample_limit}개만 로딩합니다")
        # 샘플 모드: location_grid의 실제 grid_id 목록 가져오기
        cursor_temp = conn.cursor()
        cursor_temp.execute("SELECT grid_id FROM location_grid ORDER BY grid_id")
        valid_grid_ids = set([row[0] for row in cursor_temp.fetchall()])
        cursor_temp.close()
        logger.info(f"   ⚠️  location_grid grid_ids: {sorted(valid_grid_ids)}")

    # Check if data already exists
    existing_count = get_row_count(conn, table_name)
    if existing_count > 0:
        logger.info(f"   ⚠️  Table {table_name} already contains {existing_count} rows")
        response = input(f"   Clear and reload {table_name}? (y/N): ")
        if response.lower() != 'y':
            logger.info(f"   Skipping {table_name}")
            cursor.close()
            return
        cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        conn.commit()

    logger.info(f"   Processing {len(nc_files)} NetCDF files...")

    insert_sql = f"""
    INSERT INTO {table_name} (
        scenario_id, grid_id, year, value
    ) VALUES (
        %s, %s, %s, %s
    )
    """

    for nc_file in nc_files:
        # Extract SSP scenario from filename
        ssp_name = nc_file.parent.parent.name  # e.g., SSP585
        scenario_id = SSP_MAPPING.get(ssp_name)

        if not scenario_id:
            logger.warning(f"   ⚠️  Unknown scenario: {ssp_name}, skipping {nc_file.name}")
            continue

        logger.info(f"   Loading {ssp_name} from {nc_file.name}...")

        try:
            # Extract NetCDF from tar.gz
            extracted_nc = extract_netcdf_from_targz(nc_file)

            # Open NetCDF
            ds = nc.Dataset(extracted_nc, 'r')

            # Get dimensions
            times = ds.variables['time'][:]
            lons = ds.variables['longitude'][:]
            lats = ds.variables['latitude'][:]
            data_var = ds.variables[var_short][:]

            # Parse time (yearly data, base year 2021)
            base_year = 2021

            # Batch insert
            batch = []
            batch_size = 10000
            total_inserted = 0
            skipped_nan = 0
            skipped_grid = 0

            logger.info(f"      Data shape: {data_var.shape}")
            logger.info(f"      Years: {len(times)}, Grid: {len(lats)} x {len(lons)}")

            # Iterate over years, lat, lon
            for t_idx in tqdm(range(len(times)), desc=f"      {ssp_name}", leave=False):
                # 샘플 모드: limit 도달 시 종료
                if sample_limit > 0 and total_inserted >= sample_limit:
                    logger.info(f"      ✅ 샘플 모드: {sample_limit}개 로딩 완료 (NaN skip: {skipped_nan}, grid skip: {skipped_grid})")
                    break

                year = base_year + t_idx  # Yearly data: 2021, 2022, ...

                for lat_idx in range(len(lats)):
                    # 샘플 모드: limit 도달 시 종료
                    if sample_limit > 0 and total_inserted >= sample_limit:
                        break

                    for lon_idx in range(len(lons)):
                        # 샘플 모드: limit 도달 시 종료
                        if sample_limit > 0 and total_inserted >= sample_limit:
                            break

                        # Calculate grid_id (same formula as in load_grid_locations)
                        grid_id = lat_idx * len(lons) + lon_idx + 1

                        # 샘플 모드: grid_id가 location_grid에 없으면 skip
                        if sample_limit > 0 and valid_grid_ids and grid_id not in valid_grid_ids:
                            skipped_grid += 1
                            continue

                        value = float(data_var[t_idx, lat_idx, lon_idx])

                        # Skip missing values
                        if np.isnan(value) or value == -999.0:
                            skipped_nan += 1
                            continue

                        batch.append((scenario_id, grid_id, year, value))
                        total_inserted += 1

                        if len(batch) >= batch_size:
                            cursor.executemany(insert_sql, batch)
                            conn.commit()
                            batch = []

            # Insert remaining
            if batch:
                cursor.executemany(insert_sql, batch)
                conn.commit()

            ds.close()

            # Clean up temp file
            os.remove(extracted_nc)
            os.rmdir(os.path.dirname(extracted_nc))

            logger.info(f"      ✅ Completed {ssp_name}")

        except Exception as e:
            logger.error(f"      ❌ Error processing {nc_file.name}: {e}")
            continue

    cursor.close()

    # Report final count
    final_count = get_row_count(conn, table_name)
    logger.info(f"   ✅ Total rows in {table_name}: {final_count:,}")


def load_yearly_grid_data():
    """
    Load yearly grid climate data from NetCDF files

    Source: data/KMA/extracted/KMA/downloads_kma_ssp_gridraw/*/yearly/*.nc
    Target: csdi_data, rx1day_data, etc. tables
    """
    logger = setup_logging("load_yearly_grid_data")
    logger.info("=" * 60)
    logger.info("Loading Yearly Grid Climate Data")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Get data directory
    data_dir = get_data_dir()
    nc_dir = data_dir / "KMA" / "extracted" / "KMA" / "downloads_kma_ssp_gridraw"

    if not nc_dir.exists():
        logger.error(f"❌ NetCDF directory not found: {nc_dir}")
        conn.close()
        sys.exit(1)

    # Check if location_grid table exists
    if not table_exists(conn, "location_grid"):
        logger.error("❌ Table 'location_grid' does not exist. Run create_tables.sh first.")
        conn.close()
        sys.exit(1)

    # Load grid locations (only once, using first NetCDF file)
    logger.info("📍 Checking grid locations...")
    sample_file = None
    for ssp_name in SSP_MAPPING.keys():
        ssp_dir = nc_dir / ssp_name / "yearly"
        if ssp_dir.exists():
            files = list(ssp_dir.glob("*_CSDI_*.nc"))
            if files:
                sample_file = files[0]
                break

    if sample_file:
        try:
            extracted_nc = extract_netcdf_from_targz(sample_file)
            ds = nc.Dataset(extracted_nc, 'r')
            load_grid_locations(ds, conn, logger)
            ds.close()
            os.remove(extracted_nc)
            os.rmdir(os.path.dirname(extracted_nc))
        except Exception as e:
            logger.warning(f"⚠️  Failed to load grid locations: {e}")

    # Process each variable
    for var_short, table_name in VARIABLE_MAPPING.items():
        logger.info("")
        logger.info(f"📊 Loading {var_short} data into {table_name}...")

        # Find all NetCDF files for this variable
        nc_files = []
        for ssp_name in SSP_MAPPING.keys():
            ssp_dir = nc_dir / ssp_name / "yearly"
            if ssp_dir.exists():
                pattern = f"{ssp_name}_{var_short}_*.nc"
                matching = list(ssp_dir.glob(pattern))
                nc_files.extend(matching)

        if not nc_files:
            logger.warning(f"   ⚠️  No NetCDF files found for {var_short}")
            continue

        logger.info(f"   Found {len(nc_files)} NetCDF files")

        # Estimate data size
        logger.info(f"   ⚠️  Each file contains ~36 million data points (80 years × 451,351 grid)")
        logger.info(f"   ⚠️  This will take several hours to load!")

        # Load the data
        load_variable_data(var_short, table_name, nc_files, conn, logger)

    conn.close()

    logger.info("=" * 60)
    logger.info("✅ Yearly grid data loading complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_yearly_grid_data()
