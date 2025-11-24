"""
SKALA Physical Risk AI System - Load Site Campus Energy Usage (Simplified)
실제 Excel 구조에 맞게 간단히 작성된 버전
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
from utils import setup_logging, get_db_connection, get_data_dir, table_exists


def parse_arguments():
    parser = argparse.ArgumentParser(description='판교캠퍼스 에너지 사용량 데이터 로드')
    parser.add_argument('--site-id', type=str, help='사이트 UUID', default=os.getenv('PANGYO_CAMPUS_SITE_ID'))
    parser.add_argument('--site-name', type=str, default='판교캠퍼스', help='사이트명')
    parser.add_argument('--year', type=int, default=2024, help='데이터 연도')
    return parser.parse_args()


def main():
    args = parse_arguments()
    logger = setup_logging("load_site_campus_energy_simple")
    logger.info("=" * 60)
    logger.info("판교캠퍼스 에너지 사용량 데이터 로딩 시작")
    logger.info("=" * 60)

    if not args.site_id:
        logger.error("❌ site_id가 지정되지 않았습니다")
        logger.error("   export PANGYO_CAMPUS_SITE_ID='your-uuid-here'")
        sys.exit(1)

    logger.info(f"📍 사이트 ID: {args.site_id}")
    logger.info(f"📍 사이트명: {args.site_name}")
    logger.info(f"📅 연도: {args.year}")

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
        if unicodedata.normalize('NFD', '판교캠퍼스') in unicodedata.normalize('NFD', f.name)
        and unicodedata.normalize('NFD', '에너지') in unicodedata.normalize('NFD', f.name)
    ]

    if not xlsx_files:
        logger.error(f"❌ Excel 파일을 찾을 수 없습니다")
        logger.error(f"   발견된 .xlsx 파일: {[f.name for f in all_xlsx]}")
        conn.close()
        sys.exit(1)

    xlsx_file = xlsx_files[0]
    logger.info(f"📂 데이터 파일: {xlsx_file.name}")

    try:
        # Excel 읽기
        logger.info("📖 Excel 파일 읽는 중...")
        df = pd.read_excel(xlsx_file)
        logger.info(f"📊 총 {len(df):,}개 행 발견")

        # 기존 데이터 확인
        cursor.execute(
            "SELECT COUNT(*) FROM site_campus_energy_usage WHERE site_id = %s AND measurement_year = %s",
            (args.site_id, args.year)
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
                "DELETE FROM site_campus_energy_usage WHERE site_id = %s AND measurement_year = %s",
                (args.site_id, args.year)
            )
            conn.commit()

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO site_campus_energy_usage (
                site_id, measurement_year, measurement_month, measurement_date,
                total_power_kwh, water_usage_m3, gas_usage_m3,
                energy_cost_krw, water_cost_krw, gas_cost_krw,
                data_source, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        logger.info("💾 데이터 삽입 중...")
        insert_count = 0

        # 수도 데이터: row 1 (사용량)
        water_row = df.iloc[1]
        # 지역난방 데이터: row 8 (사용량 Gcal)
        heating_row = df.iloc[8]

        # 1월~12월 데이터 처리 (컬럼 2~13)
        months = list(range(1, 13))
        for month_idx, month in enumerate(months, start=2):
            try:
                # 수도 사용량 (ton)
                water_usage = float(water_row.iloc[month_idx]) if pd.notna(water_row.iloc[month_idx]) else None

                # 지역난방 (Gcal) -> kWh 변환 (1 Gcal = 1,163 kWh)
                heating_gcal = float(heating_row.iloc[month_idx]) if pd.notna(heating_row.iloc[month_idx]) else None
                total_power = (heating_gcal * 1163) if heating_gcal else None

                # 날짜 생성
                date = datetime(args.year, month, 1).date()

                cursor.execute(insert_sql, (
                    args.site_id,
                    args.year,
                    month,
                    date,
                    total_power,
                    water_usage,
                    heating_gcal,  # gas_usage_m3에 Gcal 저장 (임시)
                    None,  # energy_cost_krw
                    None,  # water_cost_krw
                    None,  # gas_cost_krw
                    args.site_name,
                    "간단 버전: 수도(ton), 지역난방(Gcal->kWh)"
                ))
                insert_count += 1
                logger.info(f"  ✅ {args.year}년 {month}월: 수도 {water_usage}ton, 난방 {heating_gcal}Gcal")

            except Exception as e:
                logger.error(f"❌ {month}월 처리 실패: {e}")

        conn.commit()
        logger.info("=" * 60)
        logger.info(f"✅ 총 {insert_count}개 월 데이터 삽입 완료")
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
