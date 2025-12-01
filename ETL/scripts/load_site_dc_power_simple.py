"""
SKALA Physical Risk AI System - Load Site DC Power Usage (Simplified)
실제 Excel 구조에 맞게 시간별 데이터를 월별로 집계하는 버전
"""

import sys
import os
import argparse
import pandas as pd
import unicodedata
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# 상위 디렉토리의 utils import
sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, get_db_connection, get_data_dir


def parse_arguments():
    parser = argparse.ArgumentParser(description='판교DC 전력 사용량 데이터 로드')
    parser.add_argument('--site-id', type=str, help='사이트 UUID', default=os.getenv('PANGYO_DC_SITE_ID'))
    parser.add_argument('--site-name', type=str, default='판교DC', help='사이트명')
    return parser.parse_args()


def main():
    args = parse_arguments()
    logger = setup_logging("load_site_dc_power_simple")
    logger.info("=" * 60)
    logger.info("판교DC 전력 사용량 데이터 로딩 시작")
    logger.info("=" * 60)

    if not args.site_id:
        logger.error("❌ site_id가 지정되지 않았습니다")
        logger.error("   export PANGYO_DC_SITE_ID='your-uuid-here'")
        sys.exit(1)

    logger.info(f"📍 사이트 ID: {args.site_id}")
    logger.info(f"📍 사이트명: {args.site_name}")

    # DB 연결
    try:
        conn = get_db_connection()
        logger.info("✅ Datawarehouse 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # Excel 파일 찾기 (NFD 정규화)
    data_dir = get_data_dir()
    all_xlsx = list(data_dir.glob("*.xlsx"))
    xlsx_files = [
        f for f in all_xlsx
        if unicodedata.normalize('NFD', '판교DC') in unicodedata.normalize('NFD', f.name)
        and unicodedata.normalize('NFD', '전력') in unicodedata.normalize('NFD', f.name)
    ]

    if not xlsx_files:
        logger.error(f"❌ Excel 파일을 찾을 수 없습니다")
        logger.error(f"   발견된 .xlsx 파일: {[f.name for f in all_xlsx]}")
        conn.close()
        sys.exit(1)

    xlsx_file = xlsx_files[0]
    logger.info(f"📂 데이터 파일: {xlsx_file.name}")

    try:
        # Excel 읽기 (헤더는 row 6)
        logger.info("📖 Excel 파일 읽는 중...")
        df = pd.read_excel(xlsx_file, header=6)
        logger.info(f"📊 총 {len(df):,}개 시간별 행 발견")

        # 컬럼명 확인
        logger.info(f"📋 컬럼: {df.columns.tolist()}")

        # 컬럼명을 먼저 명시적으로 지정
        # Excel 구조: Unnamed:0(idx 0), 측정일(idx 1), 측정시간대(idx 2),
        #             IT평균(idx 3), IT최대(idx 4),
        #             냉방평균(idx 5), 냉방최대(idx 6),
        #             일반평균(idx 7), 일반최대(idx 8),
        #             합계평균(idx 9), 합계최대(idx 10)
        df.columns = ['index', '측정일', '측정시간대',
                      'IT전력_평균', 'IT전력_최대',
                      '냉방전력_평균', '냉방전력_최대',
                      '일반전력_평균', '일반전력_최대',
                      '합계_평균', '합계_최대']

        logger.info(f"📊 사용할 컬럼: IT전력_평균, 냉방전력_평균, 일반전력_평균")

        # 날짜 컬럼 파싱 (측정일)
        # Excel에서 날짜는 24시간마다 한 번만 표시되고 나머지는 NaN이므로 forward fill 사용
        df['측정일'] = pd.to_datetime(df['측정일'], errors='coerce')
        df['측정일'] = df['측정일'].ffill()  # NaN을 이전 값으로 채움
        df = df.dropna(subset=['측정일'])

        # 년-월-시 추출
        df['year'] = df['측정일'].dt.year
        df['month'] = df['측정일'].dt.month
        df['day'] = df['측정일'].dt.day

        # 측정시간대 파싱 (예: "01시" → 0, "02시" → 1)
        # 시간은 0-23으로 저장 (01시 = 0시대, 02시 = 1시대)
        df['hour'] = df['측정시간대'].str.extract(r'(\d+)')[0].astype(int) - 1

        # 중복 제거 (같은 날짜/시간에 여러 데이터가 있는 경우 첫 번째 유지)
        before_dedup = len(df)
        df = df.drop_duplicates(subset=['year', 'month', 'day', 'hour'], keep='first')
        after_dedup = len(df)
        if before_dedup > after_dedup:
            logger.warning(f"⚠️  중복 데이터 {before_dedup - after_dedup}개 제거")

        logger.info(f"📅 데이터 기간: {df['측정일'].min()} ~ {df['측정일'].max()}")
        logger.info(f"📊 총 {len(df):,}개 시간별 데이터 준비 완료")

        # 기존 데이터 확인
        cursor.execute(
            "SELECT COUNT(*) FROM site_dc_power_usage WHERE site_id = %s",
            (args.site_id,)
        )
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 발견")
            response = input("기존 데이터를 삭제하고 새로 로드하시겠습니까? (y/N): ")
            if response.lower() != "y":
                logger.info("작업을 취소했습니다")
                conn.close()
                return

            logger.info("🗑️  기존 데이터 삭제 중...")
            cursor.execute(
                "DELETE FROM site_dc_power_usage WHERE site_id = %s",
                (args.site_id,)
            )
            conn.commit()

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO site_dc_power_usage (
                site_id, measurement_year, measurement_month, measurement_date, measurement_hour,
                it_power_kwh, cooling_power_kwh, other_power_kwh, total_power_kwh,
                data_source, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        logger.info("💾 데이터 삽입 중...")
        insert_count = 0

        for _, row in tqdm(df.iterrows(), total=len(df), desc="시간별 데이터 삽입"):
            try:
                year = int(row['year'])
                month = int(row['month'])
                day = int(row['day'])
                hour = int(row['hour'])

                it_power = float(row['IT전력_평균']) if pd.notna(row['IT전력_평균']) else None
                cooling_power = float(row['냉방전력_평균']) if pd.notna(row['냉방전력_평균']) else None
                other_power = float(row['일반전력_평균']) if pd.notna(row['일반전력_평균']) else None

                # 합계 계산
                total_power = None
                if it_power and cooling_power and other_power:
                    total_power = it_power + cooling_power + other_power

                # 날짜 생성
                date = datetime(year, month, day).date()

                cursor.execute(insert_sql, (
                    args.site_id,
                    year,
                    month,
                    date,
                    hour,
                    it_power,
                    cooling_power,
                    other_power,
                    total_power,
                    args.site_name,
                    "시간별 데이터 저장"
                ))
                insert_count += 1

            except Exception as e:
                logger.error(f"❌ {year}년 {month}월 {day}일 {hour}시 처리 실패: {e}")

        conn.commit()
        logger.info("=" * 60)
        logger.info(f"✅ 총 {insert_count:,}개 시간별 데이터 삽입 완료")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
