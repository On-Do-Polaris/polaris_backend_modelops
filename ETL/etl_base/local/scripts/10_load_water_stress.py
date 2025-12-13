"""
SKALA Physical Risk AI System - 수자원 스트레스 데이터 적재
WRI Aqueduct 4.0 Excel 파일에서 물 스트레스 순위 데이터를 로드

데이터 소스: aqueduct40_rankings_*.xlsx
대상 테이블: water_stress_rankings
예상 데이터: 약 160,000개 레코드

최종 수정일: 2025-12-03
버전: v01
"""

import sys
import pandas as pd
from pathlib import Path
from tqdm import tqdm

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


def load_water_stress() -> None:
    """WRI Aqueduct 물 스트레스 데이터를 테이블에 로드"""
    logger = setup_logging("load_water_stress")
    logger.info("=" * 60)
    logger.info("수자원 스트레스 데이터 로딩 시작")
    logger.info("=" * 60)

    try:
        conn = get_db_connection()
        logger.info("데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        sys.exit(1)

    if not table_exists(conn, "water_stress_rankings"):
        logger.error("water_stress_rankings 테이블이 존재하지 않습니다")
        conn.close()
        sys.exit(1)

    cursor = conn.cursor()

    # Excel 파일 찾기 (대소문자 구분 없이)
    data_dir = get_data_dir()
    xlsx_files = list(data_dir.glob("aqueduct40*.xlsx")) + list(data_dir.glob("Aqueduct40*.xlsx"))

    if not xlsx_files:
        logger.error(f"Aqueduct Excel 파일을 찾을 수 없습니다")
        conn.close()
        sys.exit(1)

    xlsx_file = xlsx_files[0]
    logger.info(f"데이터 파일: {xlsx_file.name}")

    # 기존 데이터 삭제
    existing_count = get_row_count(conn, "water_stress_rankings")
    if existing_count > 0:
        logger.warning(f"기존 데이터 {existing_count:,}개 삭제")
        cursor.execute("TRUNCATE TABLE water_stress_rankings")
        conn.commit()

    # Excel 파일 읽기 (province_future 시트 - year 필수)
    logger.info("Excel 파일 읽는 중...")

    try:
        df = pd.read_excel(xlsx_file, sheet_name='province_future')
    except Exception as e:
        logger.error(f"Excel 파일 읽기 실패: {e}")
        conn.close()
        sys.exit(1)

    logger.info(f"{len(df):,}개 행 발견")

    # 컬럼명 소문자로 통일
    df.columns = [c.lower() for c in df.columns]
    logger.info(f"   컬럼: {list(df.columns)}")

    # 데이터 삽입
    insert_count = 0
    error_count = 0
    batch_size = 5000

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="데이터 로딩"):
        try:
            cursor.execute("""
                INSERT INTO water_stress_rankings (
                    gid_0, gid_1, name_0, name_1,
                    year, scenario, indicator_name,
                    weight, score, score_ranked,
                    cat, label, un_region, wb_region
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
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

            # 배치 커밋
            if insert_count % batch_size == 0:
                conn.commit()

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                logger.warning(f"삽입 오류 (row {idx}): {e}")

    conn.commit()

    # 통계 출력
    cursor.execute("""
        SELECT scenario, COUNT(*)
        FROM water_stress_rankings
        GROUP BY scenario
        ORDER BY scenario
    """)
    scenario_stats = cursor.fetchall()

    cursor.execute("""
        SELECT name_0, COUNT(*)
        FROM water_stress_rankings
        WHERE name_0 IN ('South Korea', 'Korea, Republic of', 'Republic of Korea')
        GROUP BY name_0
    """)
    korea_stats = cursor.fetchall()

    final_count = get_row_count(conn, "water_stress_rankings")

    logger.info("=" * 60)
    logger.info("수자원 스트레스 데이터 로딩 완료")
    logger.info(f"   - 삽입: {insert_count:,}개")
    logger.info(f"   - 오류: {error_count:,}개")
    logger.info(f"   - 최종: {final_count:,}개")
    logger.info("")
    logger.info("🌍 시나리오별 데이터:")
    for scenario, count in scenario_stats:
        logger.info(f"   - {scenario}: {count:,}개")

    if korea_stats:
        logger.info("")
        logger.info("🇰🇷 한국 데이터:")
        for name, count in korea_stats:
            logger.info(f"   - {name}: {count:,}개")

    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_water_stress()
