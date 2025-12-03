"""
SKALA Physical Risk AI System - 가뭄 데이터 적재
HDF/NetCDF 파일에서 가뭄 지수를 raw_drought 테이블에 로드

데이터 소스: drought/*.hdf, drought/*.nc
대상 테이블: raw_drought
예상 데이터: 약 10,000개 레코드

최종 수정일: 2025-12-02
"""

import sys
from pathlib import Path
from tqdm import tqdm
import numpy as np

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_drought() -> None:
    """가뭄 데이터를 raw_drought 테이블에 로드"""
    logger = setup_logging("load_drought")
    logger.info("=" * 60)
    logger.info("가뭄 데이터 로딩 시작")
    logger.info("=" * 60)

    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    if not table_exists(conn, "raw_drought"):
        logger.error("❌ raw_drought 테이블이 존재하지 않습니다")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # 데이터 파일 찾기
    data_dir = get_data_dir()
    drought_dir = data_dir / "drought"

    if not drought_dir.exists():
        logger.warning(f"⚠️  drought 디렉토리를 찾을 수 없습니다: {drought_dir}")
        # NetCDF 파일이 KMA 디렉토리에 있을 수 있음
        drought_dir = data_dir / "KMA" / "extracted"

    # 다양한 포맷 파일 찾기
    nc_files = list(drought_dir.glob("**/*drought*.nc")) + list(drought_dir.glob("**/*spei*.nc"))
    hdf_files = list(drought_dir.glob("**/*.hdf")) + list(drought_dir.glob("**/*.h5"))

    logger.info(f"📂 NetCDF 파일: {len(nc_files)}개")
    logger.info(f"   HDF 파일: {len(hdf_files)}개")

    # 기존 데이터 삭제
    existing_count = get_row_count(conn, "raw_drought")
    if existing_count > 0:
        logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 삭제")
        cursor.execute("TRUNCATE TABLE raw_drought")
        conn.commit()

    insert_count = 0
    error_count = 0

    # NetCDF 파일 처리
    try:
        import netCDF4 as nc

        for nc_file in tqdm(nc_files, desc="NetCDF 처리"):
            try:
                ds = nc.Dataset(nc_file)

                # 변수명 찾기 (spei, drought, spi 등)
                var_names = [v for v in ds.variables.keys()
                            if v.lower() not in ['time', 'lat', 'lon', 'latitude', 'longitude', 'x', 'y']]

                if not var_names:
                    continue

                var_name = var_names[0]
                data = ds.variables[var_name][:]

                # 좌표 찾기
                lat_name = 'latitude' if 'latitude' in ds.variables else 'lat'
                lon_name = 'longitude' if 'longitude' in ds.variables else 'lon'

                lat = ds.variables[lat_name][:]
                lon = ds.variables[lon_name][:]

                # 시간 처리
                time_dim = data.shape[0] if len(data.shape) > 2 else 1

                for t in range(min(time_dim, 100)):  # 처음 100개 시간스텝
                    if len(data.shape) > 2:
                        slice_data = data[t]
                    else:
                        slice_data = data

                    for i in range(min(len(lat), 50)):
                        for j in range(min(len(lon), 50)):
                            val = slice_data[i, j] if len(slice_data.shape) > 1 else slice_data[i]

                            if np.ma.is_masked(val) or np.isnan(val):
                                continue

                            cursor.execute("""
                                INSERT INTO raw_drought (
                                    drought_index, latitude, longitude, time_index, value
                                ) VALUES (%s, %s, %s, %s, %s)
                            """, (var_name, float(lat[i]), float(lon[j]), t, float(val)))
                            insert_count += 1

                    if insert_count % 5000 == 0:
                        conn.commit()

                ds.close()

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    logger.warning(f"⚠️  NetCDF 처리 오류 ({nc_file.name}): {e}")

    except ImportError:
        logger.warning("⚠️  netCDF4 모듈이 없습니다. NetCDF 파일 건너뜀")

    conn.commit()

    # 결과 출력
    final_count = get_row_count(conn, "raw_drought")

    logger.info("=" * 60)
    logger.info("✅ 가뭄 데이터 로딩 완료")
    logger.info(f"   - 삽입: {insert_count:,}개")
    logger.info(f"   - 오류: {error_count:,}개")
    logger.info(f"   - 최종: {final_count:,}개")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_drought()
