"""
SKALA Physical Risk AI System - 해수면 상승 NetCDF 데이터 로딩
해수면 상승 NetCDF 파일을 location_grid 및 sea_level_data 테이블에 로딩

최종 수정일: 2025-11-19
버전: v02

호출: load_data.sh
"""

import sys
import os
from pathlib import Path
from typing import Dict, Tuple
from collections import defaultdict
import numpy as np
import xarray as xr
from tqdm import tqdm
from datetime import date

from utils import setup_logging, get_db_connection, get_data_dir, get_row_count


# SSP scenario mapping
SSP_MAPPING = {
    "ssp1_2_6": "ssp1",
    "ssp2_4_5": "ssp2",
    "ssp3_7_0": "ssp3",
    "ssp5_8_5": "ssp5"
}


def load_grid_locations(conn, logger, nc_file: Path) -> Dict[Tuple[int, int], int]:
    """
    Load grid locations from NetCDF file into location_grid table

    Returns:
        Dictionary mapping (grid_x, grid_y) to grid_id
    """
    logger.info("📍 Loading grid locations...")

    # 샘플 모드 확인
    sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
    if sample_limit > 0:
        logger.info(f"   ⚠️  샘플 모드: {sample_limit}개만 로딩합니다")

    cursor = conn.cursor()

    # Check if grid locations already exist
    existing_count = get_row_count(conn, "sea_level_grid")
    if existing_count > 0:
        logger.info(f"   ℹ️  Grid locations already exist ({existing_count} rows)")
        logger.info("   Loading existing grid IDs...")

        # Load existing grid IDs (using lon/lat as keys since we don't have grid_x/grid_y)
        cursor.execute("SELECT grid_id, longitude, latitude FROM sea_level_grid")
        grid_map = {(round(float(row[1]), 4), round(float(row[2]), 4)): row[0] for row in cursor.fetchall()}
        cursor.close()
        return grid_map

    # Open NetCDF to get coordinates
    ds = xr.open_dataset(nc_file)

    lat = ds['latitude'].values
    lon = ds['longitude'].values
    j_coords = ds['j'].values
    i_coords = ds['i'].values

    logger.info(f"   Found {lat.size} grid points")
    logger.info(f"   Latitude range: {lat.min():.2f}°N to {lat.max():.2f}°N")
    logger.info(f"   Longitude range: {lon.min():.2f}°E to {lon.max():.2f}°E")

    # Insert grid locations into sea_level_grid table
    # Note: geom uses EPSG:4326 (WGS84 coordinate system) for sea level grid
    insert_sql = """
    INSERT INTO sea_level_grid (
        longitude, latitude, geom
    ) VALUES (
        %s, %s,
        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
    ) RETURNING grid_id
    """

    grid_map = {}
    grid_count = 0

    for j_idx, j in enumerate(tqdm(j_coords, desc="Inserting grids")):
        # 샘플 모드: limit 도달 시 종료
        if sample_limit > 0 and grid_count >= sample_limit:
            logger.info(f"   ✅ 샘플 모드: {sample_limit}개 그리드 로딩 완료")
            break

        for i_idx, i in enumerate(i_coords):
            # 샘플 모드: limit 도달 시 종료
            if sample_limit > 0 and grid_count >= sample_limit:
                break

            lat_val = float(lat[j_idx, i_idx])
            lon_val = float(lon[j_idx, i_idx])

            cursor.execute(insert_sql, (
                lon_val,
                lat_val,
                lon_val,  # For ST_MakePoint (lon, lat) in WGS84
                lat_val
            ))

            grid_id = cursor.fetchone()[0]
            # Use lon/lat as key (rounded to avoid floating point precision issues)
            grid_map[(round(lon_val, 4), round(lat_val, 4))] = grid_id
            grid_count += 1

    conn.commit()
    cursor.close()
    ds.close()

    logger.info(f"   ✅ Loaded {len(grid_map)} grid locations")
    return grid_map


def load_all_ssp_scenarios(
    conn,
    logger,
    slr_dir: Path,
    grid_map: Dict[Tuple[int, int], int]
) -> None:
    """
    Load all SSP scenarios into sea_level_data table

    The table structure requires all SSP values in one row per (time, grid_id)
    """
    logger.info("🌊 Loading all SSP scenarios...")

    # 샘플 모드 확인
    sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
    if sample_limit > 0:
        logger.info(f"   ⚠️  샘플 모드: {sample_limit}개만 로딩합니다")

    # Find all annual mean NetCDF files
    nc_files = {}
    for ssp_key, ssp_col in SSP_MAPPING.items():
        pattern = f"*{ssp_key}_slr_annual_mean_*.nc"
        files = list(slr_dir.glob(pattern))
        if files:
            nc_files[ssp_col] = files[0]
            logger.info(f"   Found {ssp_col}: {files[0].name}")

    if not nc_files:
        logger.warning("   ⚠️  No NetCDF files found")
        return

    # Check if data already exists
    cursor = conn.cursor()
    existing_count = get_row_count(conn, "sea_level_data")
    if existing_count > 0:
        logger.info(f"   ℹ️  Sea level data already exists ({existing_count} rows)")
        response = input("   Clear and reload? (y/N): ")
        if response.lower() != 'y':
            logger.info("   Skipping")
            cursor.close()
            return
        cursor.execute("TRUNCATE TABLE sea_level_data")
        conn.commit()
        logger.info("   ✅ Table truncated")

    # Load all SSP data into memory
    logger.info("   📂 Loading NetCDF data...")
    ssp_data = {}

    for ssp_col, nc_file in nc_files.items():
        ds = xr.open_dataset(nc_file)
        ssp_data[ssp_col] = {
            'data': ds['slr_cm_annual_mean'].values,  # Shape: (time, j, i)
            'time': ds['time'].values,
            'latitude': ds['latitude'].values,  # Shape: (j, i)
            'longitude': ds['longitude'].values,  # Shape: (j, i)
            'j': ds['j'].values,
            'i': ds['i'].values
        }
        ds.close()
        logger.info(f"      ✅ Loaded {ssp_col}")

    # Get time values (should be same for all scenarios)
    time_values = list(ssp_data.values())[0]['time']
    j_coords = list(ssp_data.values())[0]['j']
    i_coords = list(ssp_data.values())[0]['i']

    logger.info(f"   Time range: {len(time_values)} years")
    logger.info(f"   Grid size: {len(j_coords)} x {len(i_coords)}")

    # SSP scenario_id 매핑
    ssp_scenario_map = {
        'ssp1': 1,  # SSP126
        'ssp2': 2,  # SSP245
        'ssp3': 3,  # SSP370
        'ssp5': 4   # SSP585
    }

    # Prepare insert SQL (정규화된 형태: 각 SSP별로 별도 row)
    insert_sql = """
    INSERT INTO sea_level_data (
        scenario_id, grid_id, year, value
    ) VALUES (%s, %s, %s, %s)
    """

    success_count = 0
    cursor = conn.cursor()

    # Insert data
    logger.info("   💾 Inserting data...")

    for t_idx in tqdm(range(len(time_values)), desc="   Processing time steps"):
        # 샘플 모드: limit 도달 시 종료
        if sample_limit > 0 and success_count >= sample_limit:
            logger.info(f"   ✅ 샘플 모드: {sample_limit}개 로딩 완료")
            break

        year = int(str(time_values[t_idx])[:4])
        time_date = date(year, 1, 1)

        for j_idx, j in enumerate(j_coords):
            # 샘플 모드: limit 도달 시 종료
            if sample_limit > 0 and success_count >= sample_limit:
                break

            for i_idx, i in enumerate(i_coords):
                # 샘플 모드: limit 도달 시 종료
                if sample_limit > 0 and success_count >= sample_limit:
                    break
                # Get lat/lon for this grid point from first dataset
                lat_val = float(list(ssp_data.values())[0]['latitude'][j_idx, i_idx])
                lon_val = float(list(ssp_data.values())[0]['longitude'][j_idx, i_idx])

                # Get grid_id using lon/lat coordinates
                grid_id = grid_map.get((round(lon_val, 4), round(lat_val, 4)))
                if not grid_id:
                    continue

                # 각 SSP 시나리오별로 별도의 row 삽입
                for ssp_col, data_dict in ssp_data.items():
                    val = float(data_dict['data'][t_idx, j_idx, i_idx])

                    # Skip NaN values
                    if np.isnan(val):
                        continue

                    scenario_id = ssp_scenario_map.get(ssp_col)
                    if not scenario_id:
                        continue

                    # Insert one row per SSP scenario
                    cursor.execute(insert_sql, (
                        scenario_id,
                        grid_id,
                        year,
                        val
                    ))
                    success_count += 1

                    # 샘플 모드: limit 도달 시 종료
                    if sample_limit > 0 and success_count >= sample_limit:
                        break

        # Commit periodically
        if (t_idx + 1) % 10 == 0:
            conn.commit()

    conn.commit()
    cursor.close()

    logger.info(f"   ✅ Loaded {success_count} records")


def load_all_sea_level_data() -> None:
    """
    Main function to load all sea level rise data
    """
    logger = setup_logging("load_sea_level_netcdf")
    logger.info("=" * 60)
    logger.info("Loading Sea Level Rise NetCDF Data")
    logger.info("=" * 60)

    # Get database connection
    try:
        conn = get_db_connection()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    data_dir = get_data_dir()
    slr_dir = data_dir / "KMA" / "sea_level_rise"

    if not slr_dir.exists():
        logger.error(f"❌ Directory not found: {slr_dir}")
        conn.close()
        sys.exit(1)

    try:
        # Find a NetCDF file to extract grid coordinates
        nc_files = list(slr_dir.glob("*_slr_annual_mean_*.nc"))
        if not nc_files:
            logger.warning("⚠️  No sea level NetCDF files found")
            conn.close()
            return

        logger.info("")

        # Step 1: Load grid locations
        grid_map = load_grid_locations(conn, logger, nc_files[0])
        logger.info("")

        # Step 2: Load all SSP scenarios
        load_all_ssp_scenarios(conn, logger, slr_dir, grid_map)

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Sea level data loading complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error during data loading: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    load_all_sea_level_data()
