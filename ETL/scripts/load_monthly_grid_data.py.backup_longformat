"""
SKALA Physical Risk AI System - 월별 그리드 기후 데이터 로딩
KMA 월별 그리드 NetCDF 데이터를 해당 테이블에 로딩

최종 수정일: 2025-11-20
버전: v02

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


# Variable mapping to table names (monthly grid data)
VARIABLE_MAPPING = {
    "TA": "ta_data",           # 평균기온
    "RN": "rn_data",           # 강수량
    "WS": "ws_data",           # 풍속
    "RHM": "rhm_data",         # 상대습도
    "SI": "si_data",           # 일사량
    "SPEI12": "spei12_data",   # SPEI 12개월 가뭄지수
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

    # 샘플 모드 확인
    sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
    if sample_limit > 0:
        logger.info(f"   ⚠️  샘플 모드: {sample_limit}개만 로딩합니다")

    # Check if locations already exist
    existing_count = get_row_count(conn, "location_grid")
    if existing_count > 0:
        logger.info(f"   Grid locations already exist ({existing_count} points), skipping...")
        cursor.close()
        return

    logger.info(f"   Loading grid locations...")

    lons = ds.variables['longitude'][:]
    lats = ds.variables['latitude'][:]

    # 샘플 모드: 유효한 데이터가 있는 그리드만 선택하기 위해 첫 타임스텝 데이터 읽기
    data_sample = None
    if sample_limit > 0:
        logger.info(f"   샘플 모드: 유효한 데이터가 있는 그리드를 찾는 중...")
        data_sample = ds.variables[list(ds.variables.keys())[-1]][0, :, :]  # First time step

    # Create grid points (grid_id explicitly calculated)
    insert_sql = """
    INSERT INTO location_grid (
        grid_id, longitude, latitude, geom
    ) VALUES (
        %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)
    )
    """

    grid_count = 0
    batch = []
    batch_size = 1000
    grid_id_map = {}  # Map (lat, lon) to grid_id

    for lat_idx, lat in enumerate(tqdm(lats, desc="Latitude", leave=False)):
        # 샘플 모드: limit 도달 시 종료
        if sample_limit > 0 and grid_count >= sample_limit:
            logger.info(f"   ✅ 샘플 모드: {sample_limit}개 그리드 로딩 완료")
            break

        for lon_idx, lon in enumerate(lons):
            # 샘플 모드: limit 도달 시 종료
            if sample_limit > 0 and grid_count >= sample_limit:
                break

            # 샘플 모드: 유효한 데이터가 있는 그리드만 삽입
            if sample_limit > 0 and data_sample is not None:
                value = data_sample[lat_idx, lon_idx]
                # masked value 또는 NaN이면 스킵
                if np.ma.is_masked(value) or (not np.ma.is_masked(value) and np.isnan(float(value))):
                    continue

            # Calculate grid_id explicitly (same formula as in load_variable_data)
            grid_id = lat_idx * len(lons) + lon_idx + 1
            batch.append((grid_id, float(lon), float(lat), float(lon), float(lat)))
            grid_count += 1

            if len(batch) >= batch_size:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                batch = []

    # Insert remaining
    if batch:
        cursor.executemany(insert_sql, batch)
        conn.commit()

    cursor.close()
    logger.info(f"   ✅ Loaded {grid_count} grid locations")


def load_variable_data(var_short, table_name, nc_files, conn, logger):
    """
    Load variable data from NetCDF files into database

    Args:
        var_short: Variable short name (e.g., 'TA')
        table_name: Target table name (e.g., 'ta_data')
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
        scenario_id, grid_id, observation_date, value
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
            # Open NetCDF directly (already extracted)
            ds = nc.Dataset(str(nc_file), 'r')

            # Get dimensions
            times = ds.variables['time'][:]
            time_units = ds.variables['time'].units
            lons = ds.variables['longitude'][:]
            lats = ds.variables['latitude'][:]
            data_var = ds.variables[var_short][:]

            # Parse time
            base_date = datetime(2021, 1, 1)  # from "days since 2021-01-01"

            # Batch insert
            batch = []
            batch_size = 10000
            total_inserted = 0
            skipped_nan = 0
            skipped_grid = 0

            logger.info(f"      Data shape: {data_var.shape}")
            logger.info(f"      Time steps: {len(times)}, Grid: {len(lats)} x {len(lons)}")

            # Iterate over time, lat, lon
            for t_idx in tqdm(range(len(times)), desc=f"      {ssp_name}", leave=False):
                # 샘플 모드: limit 도달 시 종료
                if sample_limit > 0 and total_inserted >= sample_limit:
                    logger.info(f"      ✅ 샘플 모드: {sample_limit}개 로딩 완료 (NaN skip: {skipped_nan}, grid skip: {skipped_grid})")
                    break

                obs_date = base_date + timedelta(days=float(times[t_idx]))

                for lat_idx in range(len(lats)):
                    # 샘플 모드: limit 도달 시 종료
                    if sample_limit > 0 and total_inserted >= sample_limit:
                        break

                    for lon_idx in range(len(lons)):
                        # 샘플 모드: limit 도달 시 종료
                        if sample_limit > 0 and total_inserted >= sample_limit:
                            break

                        # Calculate grid_id (same for all time steps)
                        # Grid is inserted row by row: lat1,lon1 | lat1,lon2 | ... | lat2,lon1 | ...
                        grid_id = lat_idx * len(lons) + lon_idx + 1

                        # 샘플 모드: grid_id가 location_grid에 없으면 skip
                        if sample_limit > 0 and valid_grid_ids and grid_id not in valid_grid_ids:
                            skipped_grid += 1
                            continue

                        raw_value = data_var[t_idx, lat_idx, lon_idx]

                        # Skip missing values (masked or NaN)
                        if np.ma.is_masked(raw_value):
                            skipped_nan += 1
                            continue

                        value = float(raw_value)
                        if np.isnan(value) or value == -999.0:
                            skipped_nan += 1
                            continue

                        batch.append((scenario_id, grid_id, obs_date, value))
                        total_inserted += 1

                        if len(batch) >= batch_size:
                            try:
                                cursor.executemany(insert_sql, batch)
                                conn.commit()
                            except Exception as batch_error:
                                conn.rollback()
                                logger.error(f"      ❌ Batch insert error: {batch_error}")
                                raise
                            batch = []

            # Insert remaining
            if batch:
                try:
                    cursor.executemany(insert_sql, batch)
                    conn.commit()
                except Exception as batch_error:
                    conn.rollback()
                    logger.error(f"      ❌ Final batch insert error: {batch_error}")
                    raise

            ds.close()
            logger.info(f"      ✅ Completed {ssp_name}")

        except Exception as e:
            conn.rollback()  # CRITICAL: Rollback transaction on error
            logger.error(f"      ❌ Error processing {nc_file.name}: {e}")
            continue

    cursor.close()

    # Report final count
    final_count = get_row_count(conn, table_name)
    logger.info(f"   ✅ Total rows in {table_name}: {final_count:,}")


def load_monthly_grid_data():
    """
    Load monthly grid climate data from NetCDF files

    Source: data/KMA/extracted/KMA/downloads_kma_ssp_gridraw/*/monthly/*.nc
    Target: ta_data, rn_data, ws_data, rhm_data, si_data tables
    """
    logger = setup_logging("load_monthly_grid_data")
    logger.info("=" * 60)
    logger.info("Loading Monthly Grid Climate Data")
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
    logger.info("📍 Loading grid locations...")
    sample_file = None
    for ssp_name in SSP_MAPPING.keys():
        ssp_dir = nc_dir / ssp_name / "monthly"
        if ssp_dir.exists():
            # Look for actual NetCDF files (after extraction: AR6_SSP126_5ENSMN_skorea_TA_*.nc)
            files = list(ssp_dir.glob("*_TA_*.nc"))
            if files:
                sample_file = files[0]
                break

    if sample_file:
        try:
            # Check if file is already extracted NetCDF
            import subprocess
            file_type = subprocess.check_output(['file', str(sample_file)], text=True)

            if 'NetCDF' in file_type:
                # Already a NetCDF file, use directly
                logger.info(f"   Using extracted NetCDF: {sample_file.name}")
                ds = nc.Dataset(str(sample_file), 'r')
                load_grid_locations(ds, conn, logger)
                ds.close()
            else:
                # Still compressed, extract it
                logger.info(f"   Extracting from tar.gz: {sample_file.name}")
                extracted_nc = extract_netcdf_from_targz(sample_file)
                ds = nc.Dataset(extracted_nc, 'r')
                load_grid_locations(ds, conn, logger)
                ds.close()
                os.remove(extracted_nc)
                os.rmdir(os.path.dirname(extracted_nc))
        except Exception as e:
            logger.error(f"❌ Failed to load grid locations: {e}")
            conn.close()
            sys.exit(1)

    # Process each variable
    for var_short, table_name in VARIABLE_MAPPING.items():
        logger.info("")
        logger.info(f"📊 Loading {var_short} data into {table_name}...")

        # Find all NetCDF files for this variable
        # Pattern matches both:
        # - SSP126_TA_*.nc (compressed)
        # - AR6_SSP126_5ENSMN_skorea_TA_*.nc (extracted)
        nc_files = []
        for ssp_name in SSP_MAPPING.keys():
            ssp_dir = nc_dir / ssp_name / "monthly"
            if ssp_dir.exists():
                pattern = f"*_{var_short}_*.nc"
                matching = list(ssp_dir.glob(pattern))
                nc_files.extend(matching)

        if not nc_files:
            logger.warning(f"   ⚠️  No NetCDF files found for {var_short}")
            continue

        logger.info(f"   Found {len(nc_files)} NetCDF files")

        # Estimate data size
        logger.info(f"   ⚠️  WARNING: Each file contains ~433 million data points")
        logger.info(f"   ⚠️  Total estimated: ~{len(nc_files) * 433:.0f} million points")
        logger.info(f"   ⚠️  This will take several hours to load!")

        # Load the data
        load_variable_data(var_short, table_name, nc_files, conn, logger)

    conn.close()

    logger.info("=" * 60)
    logger.info("✅ Monthly grid data loading complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_monthly_grid_data()
