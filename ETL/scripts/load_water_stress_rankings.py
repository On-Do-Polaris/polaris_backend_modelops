"""
SKALA Physical Risk AI System - Load Water Stress Rankings

데이터 소스: Aqueduct40_rankings_download_Y2023M07D05.xlsx (WRI Aqueduct 4.0)
대상 테이블: water_stress_rankings (Datawarehouse)
예상 데이터: 161,731개 순위 데이터

Last Modified: 2025-01-24
"""

import sys
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from utils import setup_logging, get_db_connection, get_data_dir, table_exists


def load_water_stress_rankings() -> None:
    """WRI Aqueduct 4.0 물 스트레스 순위 데이터를 Excel 파일에서 로드하여 water_stress_rankings 테이블에 저장"""
    logger = setup_logging("load_water_stress_rankings")
    logger.info("=" * 60)
    logger.info("WRI Aqueduct 4.0 물 스트레스 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결
    try:
        conn = get_db_connection()
        logger.info("✅ Datawarehouse 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # 테이블 존재 여부 확인
    if not table_exists(conn, "water_stress_rankings"):
        logger.error("❌ water_stress_rankings 테이블이 존재하지 않습니다")
        logger.error("   먼저 10_create_reference_data_tables.sql을 실행하세요")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # Excel 파일 찾기
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("Aqueduct40*.xlsx"))

    if not xlsx_files:
        logger.error(f"❌ Excel 파일을 찾을 수 없습니다: Aqueduct40*.xlsx")
        conn.close()
        sys.exit(1)

    xlsx_file = xlsx_files[0]
    logger.info(f"📂 데이터 파일: {xlsx_file}")

    try:
        # Excel 파일 읽기 (province_future 시트만 사용 - year가 필수이므로)
        logger.info("📖 Excel 파일 읽는 중 (province_future)...")
        df = pd.read_excel(xlsx_file, sheet_name='province_future')

        logger.info(f"📊 총 {len(df):,}개 행 발견")
        logger.info(f"📋 컬럼: {list(df.columns)}")

        # 컬럼명 매핑 (Excel 컬럼명 → DB 컬럼명)
        # WRI Aqueduct 파일의 실제 컬럼명에 맞춰 조정 필요
        column_mapping = {
            'gid_0': 'gid_0',
            'GID_0': 'gid_0',
            'gid_1': 'gid_1',
            'GID_1': 'gid_1',
            'name_0': 'name_0',
            'NAME_0': 'name_0',
            'name_1': 'name_1',
            'NAME_1': 'name_1',
            'year': 'year',
            'YEAR': 'year',
            'scenario': 'scenario',
            'SCENARIO': 'scenario',
            'indicator_name': 'indicator_name',
            'INDICATOR_NAME': 'indicator_name',
            'indicator': 'indicator_name',
            'weight': 'weight',
            'WEIGHT': 'weight',
            'score': 'score',
            'SCORE': 'score',
            'score_ranked': 'score_ranked',
            'SCORE_RANKED': 'score_ranked',
            'cat': 'cat',
            'CAT': 'cat',
            'category': 'cat',
            'label': 'label',
            'LABEL': 'label',
            'un_region': 'un_region',
            'UN_REGION': 'un_region',
            'wb_region': 'wb_region',
            'WB_REGION': 'wb_region',
        }

        # 실제 있는 컬럼만 매핑
        rename_dict = {}
        for excel_col in df.columns:
            if excel_col in column_mapping:
                rename_dict[excel_col] = column_mapping[excel_col]

        if rename_dict:
            df = df.rename(columns=rename_dict)
            logger.info(f"✅ 컬럼 매핑 완료: {len(rename_dict)}개")

        # 필수 컬럼 확인
        required_cols = ['gid_0', 'name_0', 'year', 'scenario', 'indicator_name']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            logger.error(f"❌ 필수 컬럼이 없습니다: {missing_cols}")
            logger.error(f"   현재 컬럼: {list(df.columns)}")
            conn.close()
            sys.exit(1)

        # 기존 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM water_stress_rankings")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            logger.warning(f"⚠️  기존 데이터 {existing_count:,}개 발견")
            response = input("기존 데이터를 삭제하고 새로 로드하시겠습니까? (y/N): ")
            if response.lower() != "y":
                logger.info("작업을 취소했습니다")
                conn.close()
                return

            logger.info("🗑️  기존 데이터 삭제 중...")
            cursor.execute("DELETE FROM water_stress_rankings")
            conn.commit()
            logger.info("✅ 기존 데이터 삭제 완료")

        # 데이터 삽입 SQL
        insert_sql = """
            INSERT INTO water_stress_rankings (
                gid_0, gid_1, name_0, name_1,
                year, scenario, indicator_name,
                weight, score, score_ranked,
                cat, label, un_region, wb_region
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
        """

        # 데이터 삽입
        logger.info("💾 데이터 삽입 중...")
        insert_count = 0
        error_count = 0

        for idx, row in tqdm(df.iterrows(), total=len(df), desc="데이터 로딩"):
            try:
                cursor.execute(insert_sql, (
                    row.get('gid_0'),
                    row.get('gid_1'),
                    row.get('name_0'),
                    row.get('name_1'),
                    int(row['year']) if pd.notna(row.get('year')) else None,
                    row.get('scenario'),
                    row.get('indicator_name'),
                    row.get('weight'),
                    float(row['score']) if pd.notna(row.get('score')) else None,
                    int(row['score_ranked']) if pd.notna(row.get('score_ranked')) else None,
                    int(row['cat']) if pd.notna(row.get('cat')) else None,
                    row.get('label'),
                    row.get('un_region'),
                    row.get('wb_region'),
                ))
                insert_count += 1

                # 주기적으로 커밋 (10,000개마다)
                if insert_count % 10000 == 0:
                    conn.commit()

            except Exception as e:
                error_count += 1
                if error_count <= 5:  # 처음 5개 에러만 출력
                    logger.error(f"❌ 데이터 삽입 실패 (row {idx}): {e}")
                if error_count > 100:
                    logger.error("❌ 오류가 너무 많아 작업을 중단합니다")
                    conn.rollback()
                    conn.close()
                    sys.exit(1)

        # 최종 커밋
        conn.commit()
        logger.info("✅ 데이터 삽입 완료")

        # 최종 통계
        cursor.execute("SELECT COUNT(*) FROM water_stress_rankings")
        final_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT scenario, COUNT(*)
            FROM water_stress_rankings
            GROUP BY scenario
            ORDER BY scenario
        """)
        scenario_stats = cursor.fetchall()

        cursor.execute("""
            SELECT indicator_name, COUNT(*)
            FROM water_stress_rankings
            GROUP BY indicator_name
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        indicator_stats = cursor.fetchall()

        cursor.execute("""
            SELECT name_0, COUNT(*)
            FROM water_stress_rankings
            WHERE name_0 IN ('South Korea', 'Korea, Republic of', 'Republic of Korea', 'Korea')
            GROUP BY name_0
        """)
        korea_stats = cursor.fetchall()

        logger.info("=" * 60)
        logger.info("✅ 물 스트레스 순위 데이터 로딩 완료")
        logger.info("=" * 60)
        logger.info(f"📊 통계:")
        logger.info(f"   - 총 데이터: {final_count:,}개")
        logger.info(f"   - 삽입 성공: {insert_count:,}개")
        logger.info(f"   - 삽입 실패: {error_count:,}개")
        logger.info("")
        logger.info("🌍 시나리오별 데이터:")
        for scenario, count in scenario_stats:
            logger.info(f"   - {scenario}: {count:,}개")
        logger.info("")
        logger.info("📈 주요 지표 (상위 10개):")
        for indicator, count in indicator_stats:
            logger.info(f"   - {indicator}: {count:,}개")

        if korea_stats:
            logger.info("")
            logger.info("🇰🇷 한국 데이터:")
            for name, count in korea_stats:
                logger.info(f"   - {name}: {count:,}개")

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
    load_water_stress_rankings()
