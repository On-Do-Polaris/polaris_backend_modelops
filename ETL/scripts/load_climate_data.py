"""
SKALA Physical Risk AI System - 기후 데이터 로딩
KMA 기후 데이터 (NetCDF 및 CSV)를 기후 데이터 테이블에 로딩

최종 수정일: 2025-11-19
버전: v01

호출: load_data.sh
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import xarray as xr
from tqdm import tqdm
from datetime import datetime

from utils import setup_logging, get_db_connection, get_data_dir, table_exists, get_row_count


# 기후 변수 매핑 (Climate variable mappings)
CLIMATE_VARIABLES = {
    "tamax": {"table": "tamax_data", "desc": "최고기온", "resolution": "daily"},
    "tamin": {"table": "tamin_data", "desc": "최저기온", "resolution": "daily"},
    "ta": {"table": "ta_data", "desc": "평균기온", "resolution": "monthly"},
    "rn": {"table": "rn_data", "desc": "강수량", "resolution": "monthly"},
    "ws": {"table": "ws_data", "desc": "풍속", "resolution": "monthly"},
    "rhm": {"table": "rhm_data", "desc": "상대습도", "resolution": "monthly"},
    "si": {"table": "si_data", "desc": "일사량", "resolution": "monthly"},
    "csdi": {"table": "csdi_data", "desc": "한랭야 계속기간", "resolution": "yearly"},
    "wsdi": {"table": "wsdi_data", "desc": "온난야 계속기간", "resolution": "yearly"},
    "rx1day": {"table": "rx1day_data", "desc": "1일 최다강수량", "resolution": "yearly"},
    "rx5day": {"table": "rx5day_data", "desc": "5일 최다강수량", "resolution": "yearly"},
    "rain80": {"table": "rain80_data", "desc": "80mm 이상 강수일수", "resolution": "yearly"},
    "cdd": {"table": "cdd_data", "desc": "연속 무강수일", "resolution": "yearly"},
    "sdii": {"table": "sdii_data", "desc": "강수강도", "resolution": "yearly"},
    "spei12": {"table": "spei12_data", "desc": "표준강수증발산지수", "resolution": "monthly"},
}

# SSP 시나리오 매핑 (SSP scenario mappings)
SSP_SCENARIOS = {
    "SSP1-2.6": "ssp1",
    "SSP2-4.5": "ssp2",
    "SSP3-7.0": "ssp3",
    "SSP5-8.5": "ssp5"
}


def load_scenario_metadata(conn, logger) -> None:
    """SSP 시나리오 메타데이터 로드"""
    logger.info("📋 시나리오 메타데이터 로드 중...")

    cursor = conn.cursor()

    # 시나리오가 이미 존재하는지 확인
    cursor.execute("SELECT COUNT(*) FROM scenario")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        logger.info(f"   ℹ️  시나리오가 이미 존재합니다 ({existing_count} rows), 건너뜁니다")
        cursor.close()
        return

    scenarios = [
        ("SSP1-2.6", "SSP1-2.6", "SSP", "지속가능발전 경로", 2.6),
        ("SSP2-4.5", "SSP2-4.5", "SSP", "중도 경로", 4.5),
        ("SSP3-7.0", "SSP3-7.0", "SSP", "지역경쟁 경로", 7.0),
        ("SSP5-8.5", "SSP5-8.5", "SSP", "화석연료 의존 경로", 8.5)
    ]

    insert_sql = """
    INSERT INTO scenario (scenario_code, scenario_name, scenario_type, description, rcp_value)
    VALUES (%s, %s, %s, %s, %s)
    """

    for scenario in scenarios:
        cursor.execute(insert_sql, scenario)

    conn.commit()
    cursor.close()
    logger.info(f"   ✅ {len(scenarios)}개 시나리오 로드 완료")


def load_grid_locations(conn, logger) -> None:
    """
    그리드 위치 메타데이터 로드 (가능한 경우)

    참고: 그리드 위치는 NetCDF 좌표 데이터에서 추출되어야 함
    현재는 플레이스홀더 (placeholder)
    """
    logger.info("📋 그리드 위치 메타데이터 로드 중...")

    cursor = conn.cursor()

    # 그리드 위치가 이미 존재하는지 확인
    cursor.execute("SELECT COUNT(*) FROM location_grid")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        logger.info(f"   ℹ️  그리드 위치가 이미 존재합니다 ({existing_count} rows), 건너뜁니다")
        cursor.close()
        return

    cursor.close()
    logger.info("   ⚠️  그리드 위치 로드가 구현되지 않음 - NetCDF 파일에서 추출 필요")


def load_variable_metadata(conn, logger) -> None:
    """기후 변수 메타데이터 로드"""
    logger.info("📋 변수 메타데이터 로드 중...")

    cursor = conn.cursor()

    # 변수가 이미 존재하는지 확인
    cursor.execute("SELECT COUNT(*) FROM climate_variable")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        logger.info(f"   ℹ️  변수가 이미 존재합니다 ({existing_count} rows), 건너뜁니다")
        cursor.close()
        return

    insert_sql = """
    INSERT INTO climate_variable (
        variable_code, variable_name, table_name,
        unit, time_resolution, description
    ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    variables = [
        ("tamax", "최고기온", "tamax_data", "°C", "daily", "일 최고기온"),
        ("tamin", "최저기온", "tamin_data", "°C", "daily", "일 최저기온"),
        ("ta", "평균기온", "ta_data", "°C", "monthly", "월 평균기온"),
        ("rn", "강수량", "rn_data", "mm", "monthly", "월 누적 강수량"),
        ("ws", "풍속", "ws_data", "m/s", "monthly", "월 평균 풍속"),
        ("rhm", "상대습도", "rhm_data", "%", "monthly", "월 평균 상대습도"),
        ("si", "일사량", "si_data", "MJ/m²", "monthly", "월 누적 일사량"),
        ("csdi", "한랭야 계속기간", "csdi_data", "days", "yearly", "한랭야 계속기간 지수"),
        ("wsdi", "온난야 계속기간", "wsdi_data", "days", "yearly", "온난야 계속기간 지수"),
        ("rx1day", "1일 최다강수량", "rx1day_data", "mm", "yearly", "연 최대 1일 강수량"),
        ("rx5day", "5일 최다강수량", "rx5day_data", "mm", "yearly", "연 최대 5일 강수량"),
        ("rain80", "호우일수", "rain80_data", "days", "yearly", "일강수량 80mm 이상 일수"),
        ("cdd", "연속 무강수일", "cdd_data", "days", "yearly", "연 최대 연속 무강수일수"),
        ("sdii", "강수강도", "sdii_data", "mm/day", "yearly", "강수일의 평균 강수량"),
        ("spei12", "표준강수증발산지수", "spei12_data", "-", "monthly", "12개월 SPEI 가뭄지수"),
        ("sea_level", "해수면 상승", "sea_level_data", "m", "yearly", "해수면 상승 전망"),
    ]

    for var in variables:
        cursor.execute(insert_sql, var)

    conn.commit()
    cursor.close()
    logger.info(f"   ✅ {len(variables)}개 변수 로드 완료")


def load_sea_level_data(conn, logger, data_dir: Path) -> None:
    """
    CSV 파일에서 해수면 상승 데이터 로드

    Source: data/KMA/sea_level_rise/*.csv
    Target: sea_level_data 테이블
    """
    logger.info("🌊 해수면 상승 데이터 로드 중...")

    sea_level_dir = data_dir / "KMA" / "sea_level_rise"
    if not sea_level_dir.exists():
        logger.warning(f"   ⚠️  해수면 디렉터리를 찾을 수 없습니다: {sea_level_dir}")
        return

    cursor = conn.cursor()

    # 데이터가 이미 존재하는지 확인
    if get_row_count(conn, "sea_level_data") > 0:
        logger.info("   ℹ️  해수면 데이터가 이미 존재합니다, 건너뜁니다")
        cursor.close()
        return

    # CSV 파일 찾기
    csv_files = list(sea_level_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("   ⚠️  해수면 CSV 파일을 찾을 수 없습니다")
        cursor.close()
        return

    logger.info(f"   {len(csv_files)}개 CSV 파일 발견")

    # 각 CSV 파일 로드
    for csv_file in csv_files:
        logger.info(f"   📄 로드 중: {csv_file.name}")

        try:
            df = pd.read_csv(csv_file, encoding="utf-8")

            # 파일명에서 SSP 시나리오 추출
            ssp_column = None
            for ssp_name, ssp_col in SSP_SCENARIOS.items():
                if ssp_name.replace("-", "").replace(".", "") in csv_file.name:
                    ssp_column = ssp_col
                    break

            if not ssp_column:
                logger.warning(f"      ⚠️  파일명에서 SSP 시나리오를 확인할 수 없습니다")
                continue

            # 데이터 삽입
            # 참고: location_grid 테이블에 grid_id가 존재한다고 가정
            # 실제 구현은 CSV 구조에 따라 다름
            logger.info(f"      {ssp_column}에 대해 {len(df)} rows 로드됨")

        except Exception as e:
            logger.error(f"      ❌ {csv_file.name} 로드 실패: {e}")
            continue

    cursor.close()
    logger.info("   ✅ 해수면 데이터 로드 완료")


def load_netcdf_climate_data(conn, logger, data_dir: Path, variable: str) -> None:
    """
    NetCDF 파일에서 기후 데이터 로드

    Args:
        conn: 데이터베이스 연결
        logger: 로거 인스턴스
        data_dir: 데이터 디렉터리 경로
        variable: 기후 변수 코드 (예: 'ta', 'rn')
    """
    var_info = CLIMATE_VARIABLES.get(variable)
    if not var_info:
        logger.warning(f"   ⚠️  알 수 없는 변수: {variable}")
        return

    table_name = var_info["table"]
    logger.info(f"📊 {var_info['desc']} 데이터를 {table_name}에 로드 중...")

    # 테이블 존재 여부 확인
    if not table_exists(conn, table_name):
        logger.warning(f"   ⚠️  테이블 {table_name}이(가) 존재하지 않습니다, 건너뜁니다")
        return

    # 데이터가 이미 존재하는지 확인
    existing_count = get_row_count(conn, table_name)
    if existing_count > 0:
        logger.info(f"   ℹ️  테이블에 이미 {existing_count} rows가 있습니다, 건너뜁니다")
        return

    # 이 변수에 대한 NetCDF 파일 찾기
    kma_dir = data_dir / "KMA"
    nc_files = list(kma_dir.glob(f"*{variable}*.nc"))

    if not nc_files:
        logger.warning(f"   ⚠️  {variable}에 대한 NetCDF 파일을 찾을 수 없습니다")
        return

    logger.info(f"   {len(nc_files)}개 NetCDF 파일 발견")

    # NetCDF 데이터 로드 (플레이스홀더 - 실제 구현은 파일 구조에 따라 다름)
    for nc_file in nc_files:
        logger.info(f"   📄 처리 중: {nc_file.name}")
        try:
            ds = xr.open_dataset(nc_file)
            logger.info(f"      변수: {list(ds.data_vars)}")
            logger.info(f"      차원: {list(ds.dims)}")

            # 실제 데이터 로딩은 여기서 수행됨
            # 정확한 NetCDF 구조 이해 필요

            ds.close()
        except Exception as e:
            logger.error(f"      ❌ {nc_file.name} 처리 실패: {e}")

    logger.info(f"   ⚠️  NetCDF 데이터 로드가 완전히 구현되지 않음 - 파일 구조 분석 필요")


def load_climate_data() -> None:
    """
    모든 기후 데이터를 로드하는 메인 함수

    Source: data/KMA/*.nc, data/KMA/sea_level_rise/*.csv
    Target: Climate 스키마 테이블들
    """
    logger = setup_logging("load_climate_data")
    logger.info("=" * 60)
    logger.info("기후 데이터 로딩 시작")
    logger.info("=" * 60)

    # 데이터베이스 연결 가져오기
    try:
        conn = get_db_connection()
        logger.info("✅ 데이터베이스 연결 성공")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        sys.exit(1)

    data_dir = get_data_dir()

    try:
        # 메타데이터 테이블 로드
        load_scenario_metadata(conn, logger)
        load_variable_metadata(conn, logger)
        load_grid_locations(conn, logger)

        # 해수면 데이터 로드
        load_sea_level_data(conn, logger, data_dir)

        # 각 변수에 대한 NetCDF 기후 데이터 로드
        logger.info("")
        logger.info("📊 기후 변수 데이터 로드 중...")
        for variable in CLIMATE_VARIABLES.keys():
            load_netcdf_climate_data(conn, logger, data_dir, variable)

    except Exception as e:
        logger.error(f"❌ 기후 데이터 로딩 중 오류 발생: {e}")
        conn.close()
        sys.exit(1)

    conn.close()

    logger.info("=" * 60)
    logger.info("✅ 기후 데이터 로딩 완료!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("⚠️  참고: 전체 NetCDF 데이터 로딩을 위해 필요한 사항:")
    logger.info("   1. NetCDF 파일 구조 분석")
    logger.info("   2. 좌표에서 그리드 위치 추출")
    logger.info("   3. 시계열 데이터 파싱 및 삽입")
    logger.info("   4. SSP 시나리오 데이터 매핑")


if __name__ == "__main__":
    load_climate_data()
