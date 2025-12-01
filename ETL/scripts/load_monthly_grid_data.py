"""
SKALA Physical Risk AI System - 월별 그리드 기후 데이터 로딩 (Wide Format)
KMA 월별 그리드 NetCDF 데이터를 해당 테이블에 로딩

최종 수정일: 2025-11-25
버전: v03 (Wide Format)

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

# SSP scenario mapping (Wide Format: column names)
SSP_SCENARIOS = ["SSP126", "SSP245", "SSP370", "SSP585"]
SSP_COLUMN_NAMES = {
    "SSP126": "ssp1",
    "SSP245": "ssp2",
    "SSP370": "ssp3",
    "SSP585": "ssp5",
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


def load_variable_data_wide(var_short, table_name, nc_files_by_ssp, conn, logger):
    """
    Load variable data from NetCDF files into database (Wide Format)

    Args:
        var_short: Variable short name (e.g., 'TA')
        table_name: Target table name (e.g., 'ta_data')
        nc_files_by_ssp: Dictionary mapping SSP scenario to NetCDF file path
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

    # Open all 4 NetCDF files (one for each SSP scenario)
    datasets = {}
    for ssp_name in SSP_SCENARIOS:
        if ssp_name not in nc_files_by_ssp:
            logger.error(f"   ❌ Missing NetCDF file for {ssp_name}")
            cursor.close()
            return

        nc_file = nc_files_by_ssp[ssp_name]
        logger.info(f"   Opening {ssp_name}: {nc_file.name}")
        try:
            datasets[ssp_name] = nc.Dataset(str(nc_file), 'r')
        except Exception as e:
            logger.error(f"   ❌ Failed to open {nc_file}: {e}")
            # Close already opened datasets
            for ds in datasets.values():
                ds.close()
            cursor.close()
            return

    # Get dimensions from first dataset (all should be identical)
    ds_first = datasets[SSP_SCENARIOS[0]]
    times = ds_first.variables['time'][:]
    lons = ds_first.variables['longitude'][:]
    lats = ds_first.variables['latitude'][:]

    logger.info(f"   Data shape: time={len(times)}, lat={len(lats)}, lon={len(lons)}")

    # Parse time
    base_date = datetime(2021, 1, 1)  # from "days since 2021-01-01"

    # Wide Format INSERT SQL
    insert_sql = f"""
    INSERT INTO {table_name} (
        grid_id, observation_date, ssp1, ssp2, ssp3, ssp5
    ) VALUES (
        %s, %s, %s, %s, %s, %s
    )
    """

    # Batch insert
    batch = []
    batch_size = 10000
    total_inserted = 0
    skipped_nan = 0
    skipped_grid = 0

    # Iterate over time, lat, lon
    for t_idx in tqdm(range(len(times)), desc=f"      Loading {var_short}", leave=False):
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
                grid_id = lat_idx * len(lons) + lon_idx + 1

                # 샘플 모드: grid_id가 location_grid에 없으면 skip
                if sample_limit > 0 and valid_grid_ids and grid_id not in valid_grid_ids:
                    skipped_grid += 1
                    continue

                # Read values from all 4 SSP scenarios
                ssp_values = {}
                has_valid_data = False

                for ssp_name in SSP_SCENARIOS:
                    ds = datasets[ssp_name]
                    raw_value = ds.variables[var_short][t_idx, lat_idx, lon_idx]

                    # Check if valid
                    if np.ma.is_masked(raw_value):
                        ssp_values[ssp_name] = None
                        continue

                    value = float(raw_value)
                    if np.isnan(value) or value == -999.0:
                        ssp_values[ssp_name] = None
                        continue

                    ssp_values[ssp_name] = value
                    has_valid_data = True

                # Skip if all 4 scenarios are NULL
                if not has_valid_data:
                    skipped_nan += 1
                    continue

                # Insert row with 4 SSP values
                batch.append((
                    grid_id,
                    obs_date,
                    ssp_values.get("SSP126"),
                    ssp_values.get("SSP245"),
                    ssp_values.get("SSP370"),
                    ssp_values.get("SSP585"),
                ))
                total_inserted += 1

                if len(batch) >= batch_size:
                    try:
                        cursor.executemany(insert_sql, batch)
                        conn.commit()
                    except Exception as batch_error:
                        conn.rollback()
                        logger.error(f"      ❌ Batch insert error: {batch_error}")
                        # Close datasets
                        for ds in datasets.values():
                            ds.close()
                        cursor.close()
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
            # Close datasets
            for ds in datasets.values():
                ds.close()
            cursor.close()
            raise

    # Close all datasets
    for ds in datasets.values():
        ds.close()

    cursor.close()

    # Report final count
    final_count = get_row_count(conn, table_name)
    logger.info(f"   ✅ Total rows in {table_name}: {final_count:,}")
    logger.info(f"   ℹ️  Skipped: {skipped_nan} (NaN), {skipped_grid} (grid not in location_grid)")


def load_monthly_grid_data():
    """
    Load monthly grid climate data from NetCDF files (Wide Format)

    Source: data/KMA/extracted/KMA/downloads_kma_ssp_gridraw/*/monthly/*.nc
    Target: ta_data, rn_data, ws_data, rhm_data, si_data tables
    """
    logger = setup_logging("load_monthly_grid_data")
    logger.info("=" * 60)
    logger.info("Loading Monthly Grid Climate Data (Wide Format)")
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
    for ssp_name in SSP_SCENARIOS:
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

        # Find NetCDF files for all 4 SSP scenarios
        nc_files_by_ssp = {}
        for ssp_name in SSP_SCENARIOS:
            ssp_dir = nc_dir / ssp_name / "monthly"
            if ssp_dir.exists():
                pattern = f"*_{var_short}_*.nc"
                matching = list(ssp_dir.glob(pattern))
                if matching:
                    nc_files_by_ssp[ssp_name] = matching[0]  # Use first match

        if len(nc_files_by_ssp) != 4:
            logger.warning(f"   ⚠️  Found only {len(nc_files_by_ssp)}/4 NetCDF files for {var_short}")
            logger.warning(f"   Missing scenarios: {set(SSP_SCENARIOS) - set(nc_files_by_ssp.keys())}")
            continue

        logger.info(f"   Found {len(nc_files_by_ssp)} NetCDF files (all 4 SSP scenarios)")

        # Estimate data size (Wide Format: 1/4 of Long Format)
        logger.info(f"   ⚠️  WARNING: Wide Format reduces storage by 75%")
        logger.info(f"   ⚠️  Expected: ~108 million rows (vs. ~433M in Long Format)")
        logger.info(f"   ⚠️  This will take several hours to load!")

        # Load the data (Wide Format)
        load_variable_data_wide(var_short, table_name, nc_files_by_ssp, conn, logger)

    conn.close()

    logger.info("=" * 60)
    logger.info("✅ Monthly grid data loading complete! (Wide Format)")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_monthly_grid_data()
