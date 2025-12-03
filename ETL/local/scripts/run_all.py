#!/usr/bin/env python3
"""
SKALA Physical Risk AI System - 전체 ETL 실행
모든 Local 데이터를 순차적으로 적재

사용법:
    python run_all.py              # 전체 실행
    python run_all.py --skip 1,2   # 특정 단계 건너뛰기
    python run_all.py --only 3,4   # 특정 단계만 실행

최종 수정일: 2025-12-02
"""

import sys
import argparse
import importlib
from datetime import datetime

from utils import setup_logging, get_db_connection, get_row_count


# ETL 스크립트 순서 및 정보
ETL_SCRIPTS = [
    ("01_load_admin_regions", "행정구역 데이터", "location_admin"),
    ("02_load_weather_stations", "기상관측소 데이터", "weather_stations"),
    ("03_load_grid_station_mappings", "그리드-관측소 매핑", "grid_station_mappings"),
    ("04_load_population", "인구 데이터", "location_admin"),
    ("05_load_landcover", "토지피복 데이터", "raw_landcover"),
    ("06_load_dem", "DEM 데이터", "raw_dem"),
    ("07_load_drought", "가뭄 데이터", "raw_drought"),
    ("08_load_climate_grid", "기후 그리드 데이터", "location_grid,ta_data,rn_data"),
    ("09_load_sea_level", "해수면 상승 데이터", "sea_level_data"),
    ("10_load_water_stress", "수자원 스트레스 데이터", "water_stress_rankings"),
    ("11_load_site_data", "사이트 데이터", "site_dc_power_usage,site_campus_energy_usage"),
]


def run_etl(script_name: str, description: str, tables: str, logger) -> bool:
    """개별 ETL 스크립트 실행"""
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"📂 {description} 적재 시작")
        logger.info(f"   스크립트: {script_name}.py")
        logger.info(f"   테이블: {tables}")
        logger.info(f"{'='*60}")

        # 모듈 동적 로드 및 실행
        module = importlib.import_module(script_name)

        # main 함수 찾기
        func_name = script_name.replace("_load_", "_").replace("_", "")
        main_func = None

        for attr in dir(module):
            if attr.startswith("load"):
                main_func = getattr(module, attr)
                break

        if main_func and callable(main_func):
            main_func()
        else:
            logger.warning(f"⚠️  실행 함수를 찾을 수 없습니다: {script_name}")
            return False

        logger.info(f"✅ {description} 적재 완료")
        return True

    except Exception as e:
        logger.error(f"❌ {description} 적재 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="SKALA ETL 전체 실행")
    parser.add_argument("--skip", type=str, help="건너뛸 단계 (쉼표 구분, 예: 1,2,3)")
    parser.add_argument("--only", type=str, help="실행할 단계만 (쉼표 구분, 예: 4,5)")
    parser.add_argument("--list", action="store_true", help="ETL 단계 목록 출력")
    args = parser.parse_args()

    logger = setup_logging("run_all")

    # 단계 목록 출력
    if args.list:
        print("\n📋 ETL 단계 목록:")
        print("-" * 60)
        for i, (script, desc, tables) in enumerate(ETL_SCRIPTS, 1):
            print(f"  {i:2}. {desc:20} → {tables}")
        print("-" * 60)
        return

    # 실행할 단계 결정
    skip_steps = set()
    only_steps = set()

    if args.skip:
        skip_steps = {int(x) for x in args.skip.split(",")}

    if args.only:
        only_steps = {int(x) for x in args.only.split(",")}

    # 시작
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 SKALA ETL 전체 실행 시작")
    logger.info(f"   시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # DB 연결 테스트
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 확인 완료")
        conn.close()
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    # ETL 실행
    success_count = 0
    fail_count = 0

    for i, (script, desc, tables) in enumerate(ETL_SCRIPTS, 1):
        # 건너뛰기 체크
        if i in skip_steps:
            logger.info(f"\n⏭️  {i}. {desc} - 건너뜀")
            continue

        if only_steps and i not in only_steps:
            logger.info(f"\n⏭️  {i}. {desc} - 건너뜀")
            continue

        # 실행
        if run_etl(script, f"{i}. {desc}", tables, logger):
            success_count += 1
        else:
            fail_count += 1

    # 최종 결과
    end_time = datetime.now()
    duration = end_time - start_time

    logger.info("\n" + "=" * 60)
    logger.info("🏁 SKALA ETL 전체 실행 완료")
    logger.info(f"   종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   소요 시간: {duration}")
    logger.info(f"   성공: {success_count}개, 실패: {fail_count}개")
    logger.info("=" * 60)

    # 테이블별 결과 출력
    logger.info("\n📊 테이블별 적재 결과:")
    logger.info("-" * 40)

    conn = get_db_connection()
    tables_to_check = [
        "location_admin", "weather_stations", "grid_station_mappings",
        "location_grid", "raw_landcover", "raw_dem", "raw_drought",
        "ta_data", "rn_data", "ta_yearly_data",
        "sea_level_grid", "sea_level_data",
        "water_stress_rankings",
        "site_dc_power_usage", "site_campus_energy_usage"
    ]

    for table in tables_to_check:
        count = get_row_count(conn, table)
        status = "✅" if count > 0 else "❌"
        logger.info(f"   {status} {table:30} {count:>10,}개")

    conn.close()

    logger.info("-" * 40)

    # 실패가 있으면 종료 코드 1
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
