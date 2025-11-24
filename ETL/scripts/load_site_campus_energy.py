"""
SKALA Physical Risk AI System - Load Site Campus Energy Usage

데이터 소스: 판교캠퍼스_에너지 사용량_요금(실납부월 기준_24년_25년)_251016.xlsx의 사본.xlsx
대상 테이블: site_campus_energy_usage (Datawarehouse)
용도: ESG 보고서, 대시보드, 탄소 배출량 계산

⚠️ 중요: site_id는 Application DB의 sites 테이블 참조 (Application-level)
   - 환경변수 PANGYO_CAMPUS_SITE_ID로 site_id 지정 필요
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
    parser = argparse.ArgumentParser(description='판교캠퍼스 에너지 사용량 데이터 로드')
    parser.add_argument(
        '--site-id',
        type=str,
        help='사이트 UUID (Application DB의 sites.site_id)',
        default=os.getenv('PANGYO_CAMPUS_SITE_ID')
    )
    parser.add_argument(
        '--site-name',
        type=str,
        default='판교캠퍼스',
        help='사이트명 (기본값: 판교캠퍼스)'
    )
    return parser.parse_args()


def load_site_campus_energy() -> None:
    """판교캠퍼스 에너지 사용량 데이터를 Excel 파일에서 로드하여 site_campus_energy_usage 테이블에 저장"""
    args = parse_arguments()
    logger = setup_logging("load_site_campus_energy")
    logger.info("=" * 60)
    logger.info("판교캠퍼스 에너지 사용량 데이터 로딩 시작")
    logger.info("=" * 60)

    # site_id 확인
    if not args.site_id:
        logger.error("❌ site_id가 지정되지 않았습니다")
        logger.error("   다음 중 하나의 방법으로 site_id를 지정하세요:")
        logger.error("   1. 환경변수: export PANGYO_CAMPUS_SITE_ID='your-uuid-here'")
        logger.error("   2. 명령행 옵션: python load_site_campus_energy.py --site-id 'your-uuid-here'")
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
    if not table_exists(conn, "site_campus_energy_usage"):
        logger.error("❌ site_campus_energy_usage 테이블이 존재하지 않습니다")
        logger.error("   먼저 11_create_site_energy_tables.sql을 실행하세요")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # Excel 파일 찾기
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("*판교캠퍼스*에너지*.xlsx"))

    if not xlsx_files:
        logger.error(f"❌ Excel 파일을 찾을 수 없습니다: *판교캠퍼스*에너지*.xlsx")
        logger.error(f"   디렉토리: {data_dir}")
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
        # 예상 컬럼: 년도, 월, 전력사용량, 가스사용량, 수도사용량, 전력요금, 가스요금, 수도요금, 탄소배출량 등

        # 기존 데이터 확인
        cursor.execute(
            "SELECT COUNT(*) FROM site_campus_energy_usage WHERE site_id = %s",
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
                "DELETE FROM site_campus_energy_usage WHERE site_id = %s",
                (args.site_id,)
            )
            conn.commit()
            logger.info("✅ 기존 데이터 삭제 완료")

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO site_campus_energy_usage (
                site_id,
                total_power_kwh, renewable_energy_kwh,
                gas_usage_m3, water_usage_m3,
                energy_cost_krw, power_cost_krw, gas_cost_krw, water_cost_krw,
                co2_emissions_ton,
                measurement_year, measurement_month, measurement_date,
                data_source, notes
            ) VALUES (
                %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s,
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
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="에너지 데이터 로딩"):
            try:
                # 날짜 파싱
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
                elif '납부년월' in row or '사용년월' in row:
                    date_str = str(row.get('납부년월', row.get('사용년월', '')))
                    if len(date_str) >= 6:
                        try:
                            year = int(date_str[:4])
                            month = int(date_str[4:6])
                            date = datetime(year, month, 1).date()
                        except:
                            pass

                # 에너지 데이터 추출 (컬럼명 조정 필요)
                total_power = float(row.get('전력사용량', row.get('total_power', 0))) if pd.notna(row.get('전력사용량', row.get('total_power'))) else None
                renewable = float(row.get('재생에너지', row.get('renewable_energy', 0))) if pd.notna(row.get('재생에너지', row.get('renewable_energy'))) else None
                gas_usage = float(row.get('가스사용량', row.get('gas_usage', 0))) if pd.notna(row.get('가스사용량', row.get('gas_usage'))) else None
                water_usage = float(row.get('수도사용량', row.get('water_usage', 0))) if pd.notna(row.get('수도사용량', row.get('water_usage'))) else None

                # 비용 데이터
                power_cost = int(row.get('전력요금', row.get('power_cost', 0))) if pd.notna(row.get('전력요금', row.get('power_cost'))) else None
                gas_cost = int(row.get('가스요금', row.get('gas_cost', 0))) if pd.notna(row.get('가스요금', row.get('gas_cost'))) else None
                water_cost = int(row.get('수도요금', row.get('water_cost', 0))) if pd.notna(row.get('수도요금', row.get('water_cost'))) else None

                # 총 에너지 비용
                energy_cost = None
                if power_cost or gas_cost or water_cost:
                    energy_cost = (power_cost or 0) + (gas_cost or 0) + (water_cost or 0)

                # 탄소 배출량
                co2 = float(row.get('탄소배출량', row.get('co2_emissions', 0))) if pd.notna(row.get('탄소배출량', row.get('co2_emissions'))) else None

                # 필수 값 검증
                if not year or not total_power:
                    continue

                cursor.execute(insert_sql, (
                    args.site_id,
                    total_power, renewable,
                    gas_usage, water_usage,
                    energy_cost, power_cost, gas_cost, water_cost,
                    co2,
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
            "SELECT COUNT(*) FROM site_campus_energy_usage WHERE site_id = %s",
            (args.site_id,)
        )
        final_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT measurement_year, COUNT(*)
            FROM site_campus_energy_usage
            WHERE site_id = %s
            GROUP BY measurement_year
            ORDER BY measurement_year
        """, (args.site_id,))
        year_stats = cursor.fetchall()

        cursor.execute("""
            SELECT
                AVG(total_power_kwh) as avg_power,
                AVG(gas_usage_m3) as avg_gas,
                AVG(water_usage_m3) as avg_water,
                AVG(co2_emissions_ton) as avg_co2,
                SUM(energy_cost_krw) as total_cost
            FROM site_campus_energy_usage
            WHERE site_id = %s
        """, (args.site_id,))
        avg_stats = cursor.fetchone()

        logger.info("=" * 60)
        logger.info("✅ 판교캠퍼스 에너지 사용량 데이터 로딩 완료")
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
        logger.info("🌱 평균 에너지 사용량:")
        if avg_stats[0]:
            logger.info(f"   - 전력: {avg_stats[0]:,.2f} kWh")
        if avg_stats[1]:
            logger.info(f"   - 가스: {avg_stats[1]:,.2f} m³")
        if avg_stats[2]:
            logger.info(f"   - 수도: {avg_stats[2]:,.2f} m³")
        if avg_stats[3]:
            logger.info(f"   - CO2 배출: {avg_stats[3]:,.2f} tCO2eq")
        if avg_stats[4]:
            logger.info(f"   - 총 비용: {avg_stats[4]:,.0f} 원")
        logger.info("=" * 60)
        logger.info("💡 이 데이터는 ESG 보고서 및 대시보드에 사용됩니다")
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
    load_site_campus_energy()
