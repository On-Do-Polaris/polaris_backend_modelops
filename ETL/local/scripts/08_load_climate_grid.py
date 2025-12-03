"""
SKALA Physical Risk AI System - 기후 그리드 데이터 적재
NetCDF 파일에서 월별/연간 기후 데이터를 로드

데이터 소스: KMA/extracted/KMA/downloads_kma_ssp_gridraw/*/monthly/*.nc
            KMA/extracted/KMA/downloads_kma_ssp_gridraw/*/yearly/*.nc
대상 테이블: location_grid, ta_data, rn_data, ta_yearly_data 등
예상 데이터: 약 1,000,000개 레코드

최종 수정일: 2025-12-02
"""

import sys
import gzip
import shutil
import tempfile
from pathlib import Path
from datetime import date
from tqdm import tqdm
import numpy as np

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def decompress_if_gzip(file_path: Path) -> Path:
    """gzip 압축 파일이면 압축 해제"""
    import subprocess

    result = subprocess.run(['file', str(file_path)], capture_output=True, text=True)

    if 'gzip' in result.stdout.lower():
        # gzip 파일이면 압축 해제
        decompressed_path = Path(tempfile.mktemp(suffix='.nc'))
        with gzip.open(file_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return decompressed_path

    return file_path


def load_climate_grid() -> None:
    """기후 그리드 데이터를 테이블들에 로드"""
    logger = setup_logging("load_climate_grid")
    logger.info("=" * 60)
    logger.info("기후 그리드 데이터 로딩 시작")
    logger.info("=" * 60)

    try:
        import netCDF4 as nc
    except ImportError:
        logger.error("❌ netCDF4 모듈이 필요합니다. pip install netCDF4")
        sys.exit(1)

    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # 데이터 디렉토리
    data_dir = get_data_dir()
    kma_dir = data_dir / "KMA" / "extracted" / "KMA" / "downloads_kma_ssp_gridraw"

    if not kma_dir.exists():
        logger.error(f"❌ KMA 디렉토리를 찾을 수 없습니다: {kma_dir}")
        conn.close()
        sys.exit(1)

    # SSP 시나리오 디렉토리 찾기
    ssp_dirs = list(kma_dir.glob("SSP*"))
    logger.info(f"📂 {len(ssp_dirs)}개 SSP 시나리오 발견")

    # 1. location_grid 테이블 생성/초기화
    logger.info("\n📊 location_grid 테이블 초기화")
    cursor.execute("TRUNCATE TABLE location_grid CASCADE")
    conn.commit()

    # 첫 번째 NetCDF에서 그리드 좌표 추출
    sample_files = list(kma_dir.glob("**/monthly/*_ta_*.nc"))
    if not sample_files:
        sample_files = list(kma_dir.glob("**/*.nc"))

    if not sample_files:
        logger.error("❌ NetCDF 파일을 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    # 샘플 파일에서 그리드 좌표 추출
    sample_file = decompress_if_gzip(sample_files[0])
    ds = nc.Dataset(sample_file)

    lon_name = 'longitude' if 'longitude' in ds.variables else 'lon'
    lat_name = 'latitude' if 'latitude' in ds.variables else 'lat'

    lon = ds.variables[lon_name][:]
    lat = ds.variables[lat_name][:]

    logger.info(f"   그리드: {len(lon)} x {len(lat)} = {len(lon) * len(lat):,} points")

    # 한반도 영역만 필터링 (유효 데이터가 있는 영역)
    # 첫 번째 변수에서 유효 데이터 위치 찾기
    var_names = [v for v in ds.variables.keys() if v.upper() not in ['TIME', 'LON', 'LAT', 'LONGITUDE', 'LATITUDE']]
    if var_names:
        sample_data = ds.variables[var_names[0]][0] if len(ds.variables[var_names[0]].shape) > 2 else ds.variables[var_names[0]][:]

        # 유효 데이터 인덱스 찾기
        valid_mask = ~np.ma.getmaskarray(sample_data)
        valid_lat_idx = np.where(valid_mask.any(axis=1))[0]
        valid_lon_idx = np.where(valid_mask.any(axis=0))[0]

        if len(valid_lat_idx) > 0 and len(valid_lon_idx) > 0:
            lat_start, lat_end = valid_lat_idx[0], valid_lat_idx[-1] + 1
            lon_start, lon_end = valid_lon_idx[0], valid_lon_idx[-1] + 1
        else:
            lat_start, lat_end = 0, len(lat)
            lon_start, lon_end = 0, len(lon)
    else:
        lat_start, lat_end = 0, len(lat)
        lon_start, lon_end = 0, len(lon)

    ds.close()

    # location_grid에 그리드 포인트 삽입
    grid_map = {}  # (lon_idx, lat_idx) -> grid_id
    insert_count = 0

    logger.info(f"   유효 범위: lat[{lat_start}:{lat_end}], lon[{lon_start}:{lon_end}]")

    for lat_idx in tqdm(range(lat_start, lat_end, 5), desc="그리드 생성"):  # 5 간격으로 샘플링
        for lon_idx in range(lon_start, lon_end, 5):
            cursor.execute("""
                INSERT INTO location_grid (longitude, latitude, geom)
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                RETURNING grid_id
            """, (float(lon[lon_idx]), float(lat[lat_idx]), float(lon[lon_idx]), float(lat[lat_idx])))
            grid_id = cursor.fetchone()[0]
            grid_map[(lon_idx, lat_idx)] = grid_id
            insert_count += 1

    conn.commit()
    logger.info(f"   ✅ location_grid: {insert_count:,}개 포인트")

    # 2. 월별 데이터 로드 (ta_data, rn_data)
    logger.info("\n📊 월별 기후 데이터 로딩")

    # 테이블별 변수 매핑
    table_var_map = {
        'ta_data': ['ta', 'TA'],       # 기온
        'rn_data': ['rn', 'RN'],       # 강수량
        'rhm_data': ['rhm', 'RHM'],    # 상대습도
        'ws_data': ['ws', 'WS'],       # 풍속
    }

    for ssp_dir in ssp_dirs:
        ssp_name = ssp_dir.name  # SSP126, SSP245 등
        monthly_dir = ssp_dir / "monthly"

        if not monthly_dir.exists():
            continue

        logger.info(f"\n   📂 {ssp_name} 처리 중...")

        for table_name, var_names in table_var_map.items():
            if not table_exists(conn, table_name):
                logger.warning(f"   ⚠️  {table_name} 테이블 없음, 건너뜀")
                continue

            # 해당 변수 파일 찾기
            nc_files = []
            for var in var_names:
                nc_files.extend(list(monthly_dir.glob(f"*_{var}_*.nc")))
                nc_files.extend(list(monthly_dir.glob(f"*_{var.lower()}_*.nc")))

            if not nc_files:
                continue

            nc_file = decompress_if_gzip(nc_files[0])

            try:
                ds = nc.Dataset(nc_file)

                # 변수 찾기
                data_var = None
                for v in ds.variables.keys():
                    if v.upper() in [vn.upper() for vn in var_names]:
                        data_var = v
                        break

                if not data_var:
                    ds.close()
                    continue

                data = ds.variables[data_var][:]
                time_steps = data.shape[0]

                # SSP 컬럼 매핑
                ssp_col = {
                    'SSP126': 'ssp1',
                    'SSP245': 'ssp2',
                    'SSP370': 'ssp3',
                    'SSP585': 'ssp5',
                }.get(ssp_name, 'ssp1')

                # 기존 데이터는 첫 번째 SSP에서만 삭제
                if ssp_name == 'SSP126':
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
                    conn.commit()

                insert_count = 0
                for t_idx in tqdm(range(min(time_steps, 960)), desc=f"  {table_name}", leave=False):  # 80년 * 12개월
                    year = 2021 + (t_idx // 12)
                    month = (t_idx % 12) + 1
                    obs_date = date(year, month, 1)

                    for (lon_idx, lat_idx), grid_id in grid_map.items():
                        if lat_idx >= data.shape[1] or lon_idx >= data.shape[2]:
                            continue

                        val = data[t_idx, lat_idx, lon_idx]
                        if np.ma.is_masked(val) or np.isnan(val):
                            continue

                        if ssp_name == 'SSP126':
                            cursor.execute(f"""
                                INSERT INTO {table_name} (grid_id, observation_date, {ssp_col})
                                VALUES (%s, %s, %s)
                            """, (grid_id, obs_date, float(val)))
                        else:
                            cursor.execute(f"""
                                UPDATE {table_name}
                                SET {ssp_col} = %s
                                WHERE grid_id = %s AND observation_date = %s
                            """, (float(val), grid_id, obs_date))

                        insert_count += 1

                    if t_idx % 12 == 0:
                        conn.commit()

                conn.commit()
                ds.close()
                logger.info(f"   ✅ {table_name} ({ssp_name}): {insert_count:,}개")

            except Exception as e:
                logger.warning(f"   ⚠️  {table_name} 오류: {e}")

    # 3. 연간 데이터 로드
    logger.info("\n📊 연간 기후 데이터 로딩")

    for ssp_dir in ssp_dirs:
        ssp_name = ssp_dir.name
        yearly_dir = ssp_dir / "yearly"

        if not yearly_dir.exists():
            continue

        # ta_yearly_data
        if table_exists(conn, "ta_yearly_data"):
            nc_files = list(yearly_dir.glob("*aii*.nc")) + list(yearly_dir.glob("*ta*.nc"))

            if nc_files:
                nc_file = decompress_if_gzip(nc_files[0])

                try:
                    ds = nc.Dataset(nc_file)

                    # 변수 찾기
                    var_names = [v for v in ds.variables.keys()
                                if v.upper() not in ['TIME', 'LON', 'LAT', 'LONGITUDE', 'LATITUDE']]

                    if var_names:
                        data = ds.variables[var_names[0]][:]

                        ssp_col = {
                            'SSP126': 'ssp1', 'SSP245': 'ssp2',
                            'SSP370': 'ssp3', 'SSP585': 'ssp5'
                        }.get(ssp_name, 'ssp1')

                        if ssp_name == 'SSP126':
                            cursor.execute("TRUNCATE TABLE ta_yearly_data")
                            conn.commit()

                        insert_count = 0
                        for year_idx in range(min(data.shape[0], 80)):
                            year = 2021 + year_idx

                            for (lon_idx, lat_idx), grid_id in grid_map.items():
                                if lat_idx >= data.shape[1] or lon_idx >= data.shape[2]:
                                    continue

                                val = data[year_idx, lat_idx, lon_idx]
                                if np.ma.is_masked(val) or np.isnan(val):
                                    continue

                                if ssp_name == 'SSP126':
                                    cursor.execute(f"""
                                        INSERT INTO ta_yearly_data (grid_id, year, {ssp_col})
                                        VALUES (%s, %s, %s)
                                    """, (grid_id, year, float(val)))
                                else:
                                    cursor.execute(f"""
                                        UPDATE ta_yearly_data
                                        SET {ssp_col} = %s
                                        WHERE grid_id = %s AND year = %s
                                    """, (float(val), grid_id, year))

                                insert_count += 1
                                break  # 첫 번째 유효값만

                        conn.commit()
                        ds.close()
                        logger.info(f"   ✅ ta_yearly_data ({ssp_name}): {insert_count:,}개")

                except Exception as e:
                    logger.warning(f"   ⚠️  ta_yearly_data 오류: {e}")

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("✅ 기후 그리드 데이터 로딩 완료")
    logger.info(f"   - location_grid: {get_row_count(conn, 'location_grid'):,}개")
    logger.info(f"   - ta_data: {get_row_count(conn, 'ta_data'):,}개")
    logger.info(f"   - rn_data: {get_row_count(conn, 'rn_data'):,}개")
    logger.info(f"   - ta_yearly_data: {get_row_count(conn, 'ta_yearly_data'):,}개")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_climate_grid()
