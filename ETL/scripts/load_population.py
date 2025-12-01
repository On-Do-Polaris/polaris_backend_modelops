"""
SKALA Physical Risk AI System - 인구 데이터 로딩
인구 전망 CSV를 데이터베이스에 로딩

최종 수정일: 2025-11-19
버전: v01

호출: load_data.sh
"""

import sys
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists


def load_population_data() -> None:
    """
    CSV에서 인구 전망 데이터 로드

    Source: data/시도별_총인구_구성비_2020_2050.csv
    Target: location_admin 테이블에 인구 데이터 생성 또는 업데이트
    """
    logger = setup_logging("load_population")
    logger.info("=" * 60)
    logger.info("인구 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결 가져오기
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # CSV 파일 찾기
    data_dir = get_data_dir()
    csv_files = list(data_dir.glob("*인구*.csv"))

    if not csv_files:
        logger.error(f"❌ {data_dir}에서 인구 CSV를 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    csv_file = csv_files[0]
    logger.info(f"📂 CSV 읽기: {csv_file.name}")

    # CSV 읽기
    try:
        df = pd.read_csv(csv_file, encoding="utf-8")
        logger.info(f"✅ CSV 로드 완료: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"   컬럼: {list(df.columns)}")
    except Exception as e:
        logger.error(f"❌ CSV 읽기 실패: {e}")
        conn.close()
        sys.exit(1)

    # location_admin 테이블 존재 여부 확인
    if not table_exists(conn, "location_admin"):
        logger.warning("⚠️  테이블 'location_admin'이 존재하지 않습니다")
        logger.info("💡 location_admin이 사용 가능해지면 인구 데이터가 저장됩니다")
        conn.close()
        return

    # 인구 컬럼이 없으면 추가
    cursor = conn.cursor()

    # 현재 컬럼 확인
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'location_admin'
    """)
    existing_columns = [row[0] for row in cursor.fetchall()]

    # population_2020과 population_2050이 없으면 추가
    if "population_2020" not in existing_columns:
        logger.info("🔧 population_2020 컬럼 추가 중...")
        cursor.execute("ALTER TABLE location_admin ADD COLUMN population_2020 BIGINT")
        conn.commit()

    if "population_2050" not in existing_columns:
        logger.info("🔧 population_2050 컬럼 추가 중...")
        cursor.execute("ALTER TABLE location_admin ADD COLUMN population_2050 BIGINT")
        conn.commit()

    logger.info("💾 인구 데이터 업데이트 중...")

    # CSV 지역명을 sido_code로 매핑
    # CSV는 '서울', '부산' 등과 같이 축약된 이름을 가짐
    # 이를 sido_code (admin_code의 첫 2자리)로 매핑 필요
    region_to_sido_code = {
        "전국": None,  # 전국 단위는 건너뜀
        "서울": "11",  # 서울특별시
        "부산": "26",  # 부산광역시
        "대구": "27",  # 대구광역시
        "인천": "28",  # 인천광역시
        "광주": "29",  # 광주광역시
        "대전": "30",  # 대전광역시
        "울산": "31",  # 울산광역시
        "세종": "36",  # 세종특별자치시
        "경기": "41",  # 경기도
        "강원": "42",  # 강원도
        "충북": "43",  # 충청북도
        "충남": "44",  # 충청남도
        "전북": "45",  # 전라북도
        "전남": "46",  # 전라남도
        "경북": "47",  # 경상북도
        "경남": "48",  # 경상남도
        "제주": "50",  # 제주특별자치도
    }

    # sido_code 매칭을 사용하여 인구 데이터 업데이트
    # CSV가 시도 수준 데이터를 가지므로, 해당 시도의 모든 지역 업데이트
    update_sql = """
    UPDATE location_admin
    SET population_2020 = %s, population_2050 = %s
    WHERE sido_code = %s
    """

    success_count = 0
    error_count = 0
    skipped_count = 0

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="업데이트 중"):
        try:
            # 첫 번째 컬럼에서 지역명 추출
            region_name = str(row.iloc[0]).strip()

            # sido_code로 매핑
            sido_code = region_to_sido_code.get(region_name)

            if sido_code is None:
                logger.debug(f"   건너뜀: {region_name} (매핑 없음)")
                skipped_count += 1
                continue

            # 인구 값 추출
            # CSV 형식: [지역, 2020년, 2025년, ..., 2050년, ...]
            # 인구는 만명 단위 (10,000)
            population_2020 = None
            population_2050 = None

            # 2020년과 2050년 컬럼 찾기
            for col in df.columns:
                if "2020" in str(col):
                    val = row[col]
                    if pd.notna(val) and val != '':
                        try:
                            # 실제 인구를 얻기 위해 10,000 곱하기
                            population_2020 = int(float(str(val).replace(",", "")) * 10000)
                        except:
                            pass
                elif "2050" in str(col):
                    val = row[col]
                    if pd.notna(val) and val != '':
                        try:
                            # 실제 인구를 얻기 위해 10,000 곱하기
                            population_2050 = int(float(str(val).replace(",", "")) * 10000)
                        except:
                            pass

            if population_2020 or population_2050:
                cursor.execute(update_sql, (
                    population_2020,
                    population_2050,
                    sido_code
                ))
                affected_rows = cursor.rowcount
                logger.info(f"   ✅ {region_name} (sido_code={sido_code}): {affected_rows} rows 업데이트됨")
                success_count += 1

        except Exception as e:
            logger.warning(f"⚠️  row {idx} 업데이트 실패: {e}")
            error_count += 1
            continue

    conn.commit()
    cursor.close()
    conn.close()

    logger.info("=" * 60)
    logger.info(f"✅ 인구 데이터 로딩 완료!")
    logger.info(f"   업데이트됨: {success_count}개 지역 (시도 수준)")
    logger.info(f"   건너뜀: {skipped_count} rows (매핑 없음)")
    logger.info(f"   오류: {error_count} rows")
    logger.info("=" * 60)


if __name__ == "__main__":
    load_population_data()
