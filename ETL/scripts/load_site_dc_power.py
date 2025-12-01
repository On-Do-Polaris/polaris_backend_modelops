"""
SKALA Physical Risk AI System - Load Site DC Power Usage

데이터 소스: 판교DC 전력 사용량_2301-2510_수정.xlsx의 사본.xlsx
대상 테이블: site_dc_power_usage (Datawarehouse)
용도: Agent 2 (Impact Analysis Agent) - HEV 가중치 계산

⚠️ 중요: site_id는 Application DB의 sites 테이블 참조 (Application-level)
   - 환경변수 PANGYO_DC_SITE_ID로 site_id 지정 필요
   - 또는 스크립트 실행 시 --site-id 옵션으로 지정

Last Modified: 2025-01-24
"""

import sys
import os
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from utils import setup_logging, get_db_connection, get_data_dir, table_exists


def parse_arguments():
    """명령행 인자 파싱"""
    parser = argparse.ArgumentParser(description='판교DC 전력 사용량 데이터 로드')
    parser.add_argument(
        '--site-id',
        type=str,
        help='사이트 UUID (Application DB의 sites.site_id)',
        default=os.getenv('PANGYO_DC_SITE_ID')
    )
    parser.add_argument(
        '--site-name',
        type=str,
        default='판교DC',
        help='사이트명 (기본값: 판교DC)'
    )
    return parser.parse_args()


def load_site_dc_power() -> None:
    """판교DC 전력 사용량 데이터를 Excel 파일에서 로드하여 site_dc_power_usage 테이블에 저장"""
    args = parse_arguments()
    logger = setup_logging("load_site_dc_power")
    logger.info("=" * 60)
    logger.info("판교DC 전력 사용량 데이터 로딩 시작")
    logger.info("=" * 60)

    # site_id 확인
    if not args.site_id:
        logger.error("❌ site_id가 지정되지 않았습니다")
        logger.error("   다음 중 하나의 방법으로 site_id를 지정하세요:")
        logger.error("   1. 환경변수: export PANGYO_DC_SITE_ID='your-uuid-here'")
        logger.error("   2. 명령행 옵션: python load_site_dc_power.py --site-id 'your-uuid-here'")
        logger.error("")
        logger.error("   💡 Application DB에서 site_id 조회:")
        logger.error("      psql -h localhost -p 5432 -U skala_app_user -d skala_application")
        logger.error("      SELECT site_id, site_name FROM sites WHERE site_name LIKE '%판교%';")
        sys.exit(1)

    logger.info(f"📍 사이트 ID: {args.site_id}")
    logger.info(f"📍 사이트명: {args.site_name}")

    # 데이터베이스 연결
    try:
        conn = get_db_connection()
        logger.info("✅ Datawarehouse 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 여부 확인
    if not table_exists(conn, "site_dc_power_usage"):
        logger.error("❌ site_dc_power_usage 테이블이 존재하지 않습니다")
        logger.error("   먼저 11_create_site_energy_tables.sql을 실행하세요")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # Excel 파일 찾기
    import unicodedata
    data_dir = get_data_dir()
    # macOS Unicode NFD 정규화 문제 해결
    all_xlsx = list(data_dir.glob("*.xlsx"))
    xlsx_files = [
        f for f in all_xlsx
        if unicodedata.normalize('NFD', '판교DC') in unicodedata.normalize('NFD', f.name)
        and unicodedata.normalize('NFD', '전력') in unicodedata.normalize('NFD', f.name)
    ]

    if not xlsx_files:
        logger.error(f"❌ Excel 파일을 찾을 수 없습니다: *판교DC*전력*.xlsx")
        logger.error(f"   디렉토리: {data_dir}")
        logger.error(f"   발견된 .xlsx 파일: {[f.name for f in all_xlsx]}")
        conn.close()
        sys.exit(1)

    xlsx_file = xlsx_files[0]
    logger.info(f"📂 데이터 파일: {xlsx_file.name}")

    try:
        # Excel 파일 읽기
        logger.info("📖 Excel 파일 읽는 중...")
        df = pd.read_excel(xlsx_file)

        logger.info(f"📊 총 {len(df):,}개 행 발견")
        logger.info(f"📋 컬럼: {list(df.columns)}")

        # 컬럼 정리 (실제 Excel 파일 구조에 맞춰 조정 필요)
        # 예상 컬럼: 년도, 월, IT전력, 냉방전력, 조명전력, 기타전력, 합계전력, 전력요금 등

        # 기존 데이터 확인
        cursor.execute(
            "SELECT COUNT(*) FROM site_dc_power_usage WHERE site_id = %s",
            (args.site_id,)
        )
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 발견 (site_id={args.site_id})")
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
            logger.info("✅ 기존 데이터 삭제 완료")

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO site_dc_power_usage (
                site_id,
                it_power_kwh, cooling_power_kwh, lighting_power_kwh, other_power_kwh,
                total_power_kwh, power_cost_krw,
                measurement_year, measurement_month, measurement_date,
                data_source, notes
            ) VALUES (
                %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s
            )
        """

        # 데이터 삽입
        logger.info("💾 데이터 삽입 중...")
        insert_count = 0
        error_count = 0

        # Excel 파일 구조에 맞춰 컬럼 매핑 (예시)
        # 실제 파일 구조를 확인한 후 수정 필요
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="전력 데이터 로딩"):
            try:
                # 날짜 파싱 (예: '2023-01' 형식)
                year = None
                month = None
                date = None

                # 컬럼명에 따라 조정 필요
                if '년도' in row and '월' in row:
                    year = int(row['년도']) if pd.notna(row.get('년도')) else None
                    month = int(row['월']) if pd.notna(row.get('월')) else None
                    if year and month:
                        try:
                            date = datetime(year, month, 1).date()
                        except:
                            date = None

                # 전력 데이터 추출 (컬럼명 조정 필요)
                it_power = float(row.get('IT전력', row.get('it_power', 0))) if pd.notna(row.get('IT전력', row.get('it_power'))) else 0
                cooling_power = float(row.get('냉방전력', row.get('cooling_power', 0))) if pd.notna(row.get('냉방전력', row.get('cooling_power'))) else 0
                lighting_power = float(row.get('조명전력', row.get('lighting_power', 0))) if pd.notna(row.get('조명전력', row.get('lighting_power'))) else None
                other_power = float(row.get('기타전력', row.get('other_power', 0))) if pd.notna(row.get('기타전력', row.get('other_power'))) else None
                total_power = float(row.get('총전력', row.get('total_power', row.get('합계', 0)))) if pd.notna(row.get('총전력', row.get('total_power', row.get('합계')))) else it_power + cooling_power

                # 전력 요금
                cost = int(row.get('전력요금', row.get('power_cost', 0))) if pd.notna(row.get('전력요금', row.get('power_cost'))) else None

                # 필수 값 검증
                if not year or it_power <= 0:
                    continue

                cursor.execute(insert_sql, (
                    args.site_id,
                    it_power, cooling_power, lighting_power, other_power,
                    total_power, cost,
                    year, month, date,
                    args.site_name, None
                ))
                insert_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    logger.error(f"❌ 데이터 삽입 실패 (row {idx}): {e}")
                if error_count > 20:
                    logger.error("❌ 오류가 너무 많아 작업을 중단합니다")
                    logger.error("   Excel 파일 구조를 확인하고 컬럼 매핑을 수정하세요")
                    conn.rollback()
                    conn.close()
                    sys.exit(1)

        # 커밋
        conn.commit()
        logger.info("✅ 데이터 삽입 완료")

        # 최종 통계
        cursor.execute(
            "SELECT COUNT(*) FROM site_dc_power_usage WHERE site_id = %s",
            (args.site_id,)
        )
        final_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT measurement_year, COUNT(*)
            FROM site_dc_power_usage
            WHERE site_id = %s
            GROUP BY measurement_year
            ORDER BY measurement_year
        """, (args.site_id,))
        year_stats = cursor.fetchall()

        cursor.execute("""
            SELECT
                AVG(it_power_kwh) as avg_it,
                AVG(cooling_power_kwh) as avg_cooling,
                AVG(total_power_kwh) as avg_total
            FROM site_dc_power_usage
            WHERE site_id = %s
        """, (args.site_id,))
        avg_stats = cursor.fetchone()

        logger.info("=" * 60)
        logger.info("✅ 판교DC 전력 사용량 데이터 로딩 완료")
        logger.info("=" * 60)
        logger.info(f"📊 통계:")
        logger.info(f"   - 총 데이터: {final_count:,}개")
        logger.info(f"   - 삽입 성공: {insert_count:,}개")
        logger.info(f"   - 삽입 실패: {error_count:,}개")
        logger.info("")
        logger.info("📅 연도별 데이터:")
        for year, count in year_stats:
            logger.info(f"   - {year}년: {count:,}개")
        logger.info("")
        logger.info("⚡ 평균 전력 사용량:")
        logger.info(f"   - IT 전력: {avg_stats[0]:,.2f} kWh")
        logger.info(f"   - 냉방 전력: {avg_stats[1]:,.2f} kWh")
        logger.info(f"   - 총 전력: {avg_stats[2]:,.2f} kWh")
        logger.info("=" * 60)
        logger.info("💡 이 데이터는 Agent 2 (Impact Analysis)의 HEV 가중치 계산에 사용됩니다")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    load_site_dc_power()
