"""
SKALA Physical Risk AI System - 인구 데이터 적재
CSV 파일에서 시도별 인구 전망 데이터를 location_admin 테이블에 업데이트

데이터 소스: 시도별_총인구_구성비_2020_2050.csv
대상 테이블: location_admin (population_2020, population_2050 컬럼)
예상 데이터: 17개 시도

최종 수정일: 2025-12-02
"""

import sys
import pandas as pd
from pathlib import Path

from utils import setup_logging, get_db_connection, get_data_dir, table_exists


# 지역명 매핑 (CSV 약칭 → 정식 명칭)
REGION_MAP = {
    '서울': '서울특별시',
    '부산': '부산광역시',
    '대구': '대구광역시',
    '인천': '인천광역시',
    '광주': '광주광역시',
    '대전': '대전광역시',
    '울산': '울산광역시',
    '세종': '세종특별자치시',
    '경기': '경기도',
    '강원': '강원특별자치도',
    '충북': '충청북도',
    '충남': '충청남도',
    '전북': '전북특별자치도',
    '전남': '전라남도',
    '경북': '경상북도',
    '경남': '경상남도',
    '제주': '제주특별자치도',
}


def load_population() -> None:
    """인구 전망 CSV를 location_admin 테이블에 업데이트"""
    logger = setup_logging("load_population")
    logger.info("=" * 60)
    logger.info("인구 데이터 로딩 시작")
    logger.info("=" * 60)

    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    if not table_exists(conn, "location_admin"):
        logger.error("❌ location_admin 테이블이 존재하지 않습니다")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # CSV 파일 찾기
    data_dir = get_data_dir()
    csv_files = list(data_dir.glob("*인구*.csv"))

    if not csv_files:
        logger.error(f"❌ 인구 CSV 파일을 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    csv_file = csv_files[0]
    logger.info(f"📂 데이터 파일: {csv_file.name}")

    # CSV 로드
    try:
        df = pd.read_csv(csv_file, encoding='utf-8')
    except Exception as e:
        logger.error(f"❌ CSV 파일 읽기 실패: {e}")
        conn.close()
        sys.exit(1)

    logger.info(f"📊 {len(df)}개 지역 데이터 발견")
    logger.info(f"   컬럼: {list(df.columns)}")

    # 인구 데이터 업데이트
    update_count = 0

    for _, row in df.iterrows():
        region = row['지역']
        if region == '전국':
            continue

        full_name = REGION_MAP.get(region, region)

        # 인구 단위 확인 (만 단위면 10000 곱함)
        pop_2020 = row.get('2020년', 0)
        pop_2050 = row.get('2050년', 0)

        # 값이 1000 미만이면 만 단위로 가정
        if pop_2020 < 10000:
            pop_2020 = int(pop_2020 * 10000)
            pop_2050 = int(pop_2050 * 10000)
        else:
            pop_2020 = int(pop_2020)
            pop_2050 = int(pop_2050)

        # 해당 시도에 속한 모든 행정구역 업데이트
        cursor.execute("""
            UPDATE location_admin
            SET population_2020 = %s, population_2050 = %s
            WHERE admin_name LIKE %s OR admin_name LIKE %s
        """, (pop_2020, pop_2050, f'{full_name}%', f'%{region}%'))

        rows_updated = cursor.rowcount
        if rows_updated > 0:
            update_count += rows_updated
            logger.info(f"   ✅ {full_name}: {rows_updated:,}개 행 업데이트 (2020: {pop_2020:,}명)")

    conn.commit()

    logger.info("=" * 60)
    logger.info("✅ 인구 데이터 로딩 완료")
    logger.info(f"   - 업데이트: {update_count:,}개 행정구역")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_population()
