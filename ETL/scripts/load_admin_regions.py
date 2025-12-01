"""
SKALA Physical Risk AI System - 행정구역 데이터 로딩
N3A_G0110000 shapefile 데이터를 location_admin 테이블에 로딩

최종 수정일: 2025-11-19
버전: v01

호출: load_data.sh
"""

import sys
import os
from pathlib import Path
import geopandas as gpd
from shapely import wkb
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_admin_regions() -> None:
    """
    shapefile에서 행정구역 데이터를 location_admin 테이블로 로딩

    원본: data/N3A_G0110000/*.shp
    대상: location_admin 테이블
    """
    logger = setup_logging("load_admin_regions")
    logger.info("=" * 60)
    logger.info("행정구역 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결 가져오기
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 확인
    if not table_exists(conn, "location_admin"):
        logger.error("❌ 테이블 'location_admin'이 존재하지 않습니다. create_tables.sh를 먼저 실행하세요.")
        conn.close()
        sys.exit(1)

    # 기존 데이터 확인
    existing_count = get_row_count(conn, "location_admin")
    if existing_count > 0:
        logger.warning(f"⚠️  테이블에 이미 {existing_count}개의 행이 존재합니다")
        response = input("기존 데이터를 삭제하고 다시 로딩하시겠습니까? (y/N): ")
        if response.lower() == 'y':
            cursor = conn.cursor()
            cursor.execute("TRUNCATE TABLE location_admin CASCADE")
            conn.commit()
            cursor.close()
            logger.info("✅ 테이블 초기화 완료")
        else:
            logger.info("로딩 건너뛰기")
            conn.close()
            return

    # shapefile 찾기
    data_dir = get_data_dir()
    shp_dir = data_dir / "N3A_G0110000"
    shp_files = list(shp_dir.glob("*.shp"))

    if not shp_files:
        logger.error(f"❌ {shp_dir}에서 shapefile을 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    shp_file = shp_files[0]
    logger.info(f"📂 Shapefile 읽기: {shp_file.name}")

    # shapefile 읽기 (한글 데이터를 위해 여러 인코딩 시도)
    try:
        try:
            gdf = gpd.read_file(shp_file, encoding="euc-kr")
        except:
            try:
                gdf = gpd.read_file(shp_file, encoding="cp949")
            except:
                gdf = gpd.read_file(shp_file, encoding="utf-8")

        logger.info(f"✅ Shapefile 로드 완료: {len(gdf)} features")
        logger.info(f"   원본 좌표계: {gdf.crs}")
    except Exception as e:
        logger.error(f"❌ Shapefile 읽기 실패: {e}")
        conn.close()
        sys.exit(1)

    # EPSG:5174 (한국 좌표계)로 재투영
    if gdf.crs.to_epsg() != 5174:
        logger.info("🔄 EPSG:5174로 재투영 중...")
        gdf = gdf.to_crs(epsg=5174)
        logger.info("✅ 재투영 완료")

    # 중심점 계산
    logger.info("🔄 중심점 계산 중...")
    gdf["centroid"] = gdf.geometry.centroid

    # 샘플 모드 확인
    sample_limit = int(os.environ.get("SAMPLE_LIMIT", 0))
    if sample_limit > 0:
        logger.info(f"⚠️  샘플 모드: {sample_limit}개만 로딩합니다")

    # 데이터 삽입
    logger.info("💾 데이터베이스에 데이터 삽입 중...")
    cursor = conn.cursor()

    insert_sql = """
    INSERT INTO location_admin (
        admin_code, admin_name, level,
        sido_code, sigungu_code,
        geom, centroid
    ) VALUES (
        %s, %s, %s,
        %s, %s,
        ST_GeomFromWKB(%s, 5174),
        ST_GeomFromWKB(%s, 5174)
    )
    """

    success_count = 0
    error_count = 0

    for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="삽입 중"):
        # 샘플 모드: limit 도달 시 종료
        if sample_limit > 0 and success_count >= sample_limit:
            logger.info(f"✅ 샘플 모드: {sample_limit}개 로딩 완료")
            break
        try:
            # shapefile에서 행정구역 코드와 이름 추출
            admin_code = row.get("BJCD", str(idx))
            admin_name = row.get("NAME", f"Region_{idx}")

            # sido_code (앞 2자리)와 sigungu_code (앞 5자리) 추출
            code_str = str(admin_code)
            sido_code = code_str[:2] if len(code_str) >= 2 else None
            sigungu_code = code_str[:5] if len(code_str) >= 5 else None

            # 코드 패턴 기반 행정 단계 결정
            # 시도=1, 시군구=2, 읍면동=3
            if len(code_str) >= 10:
                if code_str[2:] == "00000000":
                    admin_level = 1  # 시도 (XX00000000)
                elif code_str[5:] == "00000":
                    admin_level = 2  # 시군구 (XXXXX00000)
                else:
                    admin_level = 3  # 읍면동
            else:
                admin_level = 3  # 기본값 읍면동

            # geometry를 WKB로 변환
            geom_wkb = row.geometry.wkb
            centroid_wkb = row.centroid.wkb

            cursor.execute(insert_sql, (
                admin_code,
                admin_name,
                admin_level,
                sido_code,
                sigungu_code,
                geom_wkb,
                centroid_wkb
            ))

            success_count += 1

        except Exception as e:
            logger.warning(f"⚠️  행 {idx} 삽입 실패: {e}")
            error_count += 1
            continue

    conn.commit()
    cursor.close()
    conn.close()

    logger.info("=" * 60)
    logger.info(f"✅ 데이터 로딩 완료!")
    logger.info(f"   성공: {success_count} 행")
    logger.info(f"   오류: {error_count} 행")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_admin_regions()
