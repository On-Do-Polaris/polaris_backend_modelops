"""
SKALA Physical Risk AI System - 행정구역 데이터 적재
GeoJSON 파일에서 시군구 경계 데이터를 location_admin 테이블에 로드

데이터 소스: N3A_G0110000 (시군구 경계 GeoJSON)
대상 테이블: location_admin
예상 데이터: 약 5,000개 행정구역

최종 수정일: 2025-12-02
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_admin_regions() -> None:
    """시군구 경계 GeoJSON을 location_admin 테이블에 로드"""
    logger = setup_logging("load_admin_regions")
    logger.info("=" * 60)
    logger.info("행정구역 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 확인
    if not table_exists(conn, "location_admin"):
        logger.error("❌ location_admin 테이블이 존재하지 않습니다")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # GeoJSON 파일 찾기
    data_dir = get_data_dir()
    geojson_dir = data_dir / "N3A_G0110000"

    if not geojson_dir.exists():
        logger.error(f"❌ GeoJSON 디렉토리를 찾을 수 없습니다: {geojson_dir}")
        conn.close()
        sys.exit(1)

    geojson_files = list(geojson_dir.glob("*.geojson")) + list(geojson_dir.glob("*.json"))

    if not geojson_files:
        logger.error(f"❌ GeoJSON 파일을 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    logger.info(f"📂 {len(geojson_files)}개 GeoJSON 파일 발견")

    # 기존 데이터 확인 및 삭제
    existing_count = get_row_count(conn, "location_admin")
    if existing_count > 0:
        logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 삭제")
        cursor.execute("TRUNCATE TABLE location_admin CASCADE")
        conn.commit()

    # 데이터 로드
    insert_count = 0
    error_count = 0

    for geojson_file in geojson_files:
        logger.info(f"📖 처리 중: {geojson_file.name}")

        try:
            with open(geojson_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            features = data.get('features', [])
            logger.info(f"   {len(features):,}개 피처 발견")

            for feature in tqdm(features, desc=f"  {geojson_file.name}"):
                try:
                    props = feature.get('properties', {})
                    geom = feature.get('geometry')

                    if not geom:
                        continue

                    # 속성 추출 (GeoJSON 구조에 따라 조정 필요)
                    admin_code = props.get('ADM_CD', props.get('adm_cd', props.get('SIG_CD', '')))
                    admin_name = props.get('ADM_NM', props.get('adm_nm', props.get('SIG_KOR_NM', '')))

                    # 코드 파싱
                    sido_code = admin_code[:2] if len(admin_code) >= 2 else None
                    sigungu_code = admin_code[:5] if len(admin_code) >= 5 else None
                    emd_code = admin_code[:8] if len(admin_code) >= 8 else None

                    # 레벨 결정 (코드 길이로)
                    if len(admin_code) >= 8:
                        level = 3  # 읍면동
                    elif len(admin_code) >= 5:
                        level = 2  # 시군구
                    else:
                        level = 1  # 시도

                    cursor.execute("""
                        INSERT INTO location_admin (
                            admin_code, admin_name, level,
                            sido_code, sigungu_code, emd_code,
                            geom, centroid
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                            ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                        )
                    """, (
                        admin_code, admin_name, level,
                        sido_code, sigungu_code, emd_code,
                        json.dumps(geom), json.dumps(geom)
                    ))
                    insert_count += 1

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        logger.warning(f"⚠️  피처 처리 오류: {e}")

            conn.commit()

        except Exception as e:
            logger.error(f"❌ 파일 처리 오류 ({geojson_file.name}): {e}")
            error_count += 1

    # 결과 출력
    final_count = get_row_count(conn, "location_admin")

    logger.info("=" * 60)
    logger.info("✅ 행정구역 데이터 로딩 완료")
    logger.info(f"   - 삽입: {insert_count:,}개")
    logger.info(f"   - 오류: {error_count:,}개")
    logger.info(f"   - 최종: {final_count:,}개")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_admin_regions()
