'''
파일명: hazard_probability_timeseries_batch.py
최종 수정일: 2025-12-13
버전: v01
파일 개요: 모든 격자점에 대해 SSP 시나리오별 H, P(H) 시계열 계산 (2021-2100)
변경 이력:
    - 2025-12-13: v01 - 최초 생성
        * SSP126, SSP245, SSP370, SSP585 4개 시나리오
        * 2021-2100년 (80년) 1년 단위 계산
        * 모든 격자점 순회
        * 9개 리스크 타입별 H, P(H) 계산
'''

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
import sys

# Hazard Agents
from ..agents.hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent
from ..agents.hazard_calculate.extreme_cold_hscore_agent import ExtremeColdHScoreAgent
from ..agents.hazard_calculate.drought_hscore_agent import DroughtHScoreAgent
from ..agents.hazard_calculate.river_flood_hscore_agent import RiverFloodHScoreAgent
from ..agents.hazard_calculate.urban_flood_hscore_agent import UrbanFloodHScoreAgent
from ..agents.hazard_calculate.sea_level_rise_hscore_agent import SeaLevelRiseHScoreAgent
from ..agents.hazard_calculate.typhoon_hscore_agent import TyphoonHScoreAgent
from ..agents.hazard_calculate.wildfire_hscore_agent import WildfireHScoreAgent
from ..agents.hazard_calculate.water_stress_hscore_agent import WaterStressHScoreAgent

# Probability Agents
from ..agents.probability_calculate.extreme_heat_probability_agent import ExtremeHeatProbabilityAgent
from ..agents.probability_calculate.extreme_cold_probability_agent import ExtremeColdProbabilityAgent
from ..agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent
from ..agents.probability_calculate.river_flood_probability_agent import RiverFloodProbabilityAgent
from ..agents.probability_calculate.urban_flood_probability_agent import UrbanFloodProbabilityAgent
from ..agents.probability_calculate.sea_level_rise_probability_agent import SeaLevelRiseProbabilityAgent
from ..agents.probability_calculate.typhoon_probability_agent import TyphoonProbabilityAgent
from ..agents.probability_calculate.wildfire_probability_agent import WildfireProbabilityAgent
from ..agents.probability_calculate.water_stress_probability_agent import WaterStressProbabilityAgent

# Utils
from ..utils.hazard_data_collector import HazardDataCollector
from ..database.connection import DatabaseConnection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========== 상수 정의 ==========
SCENARIOS = ["SSP126", "SSP245", "SSP370", "SSP585"]
YEARS = list(range(2021, 2101))  # 2021-2100 (80년)

RISK_TYPES = [
    'extreme_heat',
    'extreme_cold',
    'wildfire',
    'drought',
    'water_stress',
    'sea_level_rise',
    'river_flood',
    'urban_flood',
    'typhoon'
]


# ========== Agent 매핑 ==========
HAZARD_AGENTS = {
    'extreme_heat': ExtremeHeatHScoreAgent(),
    'extreme_cold': ExtremeColdHScoreAgent(),
    'drought': DroughtHScoreAgent(),
    'river_flood': RiverFloodHScoreAgent(),
    'urban_flood': UrbanFloodHScoreAgent(),
    'sea_level_rise': SeaLevelRiseHScoreAgent(),
    'typhoon': TyphoonHScoreAgent(),
    'wildfire': WildfireHScoreAgent(),
    'water_stress': WaterStressHScoreAgent()
}

PROBABILITY_AGENTS = {
    'extreme_heat': ExtremeHeatProbabilityAgent(),
    'extreme_cold': ExtremeColdProbabilityAgent(),
    'drought': DroughtProbabilityAgent(),
    'river_flood': RiverFloodProbabilityAgent(),
    'urban_flood': UrbanFloodProbabilityAgent(),
    'sea_level_rise': SeaLevelRiseProbabilityAgent(),
    'typhoon': TyphoonProbabilityAgent(),
    'wildfire': WildfireProbabilityAgent(),
    'water_stress': WaterStressProbabilityAgent()
}


# ========== 격자점 조회 ==========
def get_all_grid_points() -> List[Tuple[float, float]]:
    """
    DB에서 모든 격자점 좌표 조회

    Returns:
        [(latitude, longitude), ...]
    """
    try:
        db = DatabaseConnection()
        grid_points = db.fetch_all_grid_points()
        logger.info(f"Total grid points fetched: {len(grid_points)}")
        return grid_points
    except Exception as e:
        logger.error(f"Failed to fetch grid points: {e}")
        raise


# ========== H 계산 ==========
def calculate_hazard(
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    risk_type: str
) -> Dict[str, Any]:
    """
    단일 격자점, 시나리오, 연도, 리스크에 대한 H 계산

    Args:
        latitude: 위도
        longitude: 경도
        scenario: SSP 시나리오
        target_year: 분석 연도
        risk_type: 리스크 타입

    Returns:
        {
            'hazard_score': float,           # 0-1 정규화
            'hazard_score_100': float,       # 0-100 점수
            'hazard_level': str,             # Very High/High/Medium/Low/Very Low
            'raw_data': Dict
        }
    """
    try:
        # HazardDataCollector로 데이터 수집
        collector = HazardDataCollector(scenario=scenario, target_year=target_year)
        collected_data = collector.collect_data(
            lat=latitude,
            lon=longitude,
            risk_type=risk_type
        )

        # HazardAgent 호출
        agent = HAZARD_AGENTS[risk_type]
        h_result = agent.calculate_hazard_score(collected_data)

        # DB 값 추적 로그 (calculation_details에서 실제 사용된 값 확인)
        calc_details = collected_data.get('calculation_details', {}).get(risk_type, {})
        data_source = collected_data.get('climate_data', {}).get('data_source', 'unknown')
        logger.debug(
            f"[H] {risk_type}: score={h_result.get('hazard_score', 0):.4f}, "
            f"source={data_source}, details={calc_details}"
        )

        return {
            'hazard_score': h_result.get('hazard_score', 0.0),  # 0-1
            'hazard_score_100': h_result.get('hazard_score_100', 0.0),  # 0-100
            'hazard_level': h_result.get('hazard_level', 'Very Low'),
            'raw_data': h_result,
            'calculation_details': calc_details,
            'data_source': data_source
        }

    except Exception as e:
        logger.error(f"Hazard calculation failed for {risk_type} at ({latitude}, {longitude}): {e}")
        return {
            'hazard_score': 0.0,
            'hazard_score_100': 0.0,
            'hazard_level': 'Very Low',
            'raw_data': {},
            'error': str(e)
        }


# ========== P(H) 계산 ==========
def calculate_probability(
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    risk_type: str,
    hazard_score: float
) -> Dict[str, Any]:
    """
    단일 격자점, 시나리오, 연도, 리스크에 대한 P(H) 계산

    Args:
        latitude: 위도
        longitude: 경도
        scenario: SSP 시나리오
        target_year: 분석 연도
        risk_type: 리스크 타입
        hazard_score: H 점수 (0-1) - 현재 미사용

    Returns:
        {
            'aal': float,                    # Annual Average Loss (확률)
            'bin_probabilities': List,       # bin별 발생확률
            'probability_level': str,        # Very High/High/Medium/Low/Very Low
            'raw_data': Dict
        }
    """
    try:
        # ProbabilityAgent의 calculate() 메서드 호출 (Hazard/Exposure 패턴)
        agent = PROBABILITY_AGENTS[risk_type]
        p_result = agent.calculate(
            lat=latitude,
            lon=longitude,
            ssp_scenario=scenario,
            start_year=2021,
            end_year=2100
        )

        # AAL 기반 확률 레벨 분류
        aal = p_result.get('aal', 0.0)
        if aal >= 0.03:
            probability_level = 'Very High'
        elif aal >= 0.02:
            probability_level = 'High'
        elif aal >= 0.01:
            probability_level = 'Medium'
        elif aal >= 0.005:
            probability_level = 'Low'
        else:
            probability_level = 'Very Low'

        # DB 값 추적 로그
        calc_details = p_result.get('calculation_details', {})
        data_source = p_result.get('data_source', 'unknown')
        logger.debug(
            f"[P] {risk_type}: aal={aal:.6f}, source={data_source}, "
            f"method={calc_details.get('method', 'N/A')}, years={calc_details.get('total_years', 0)}"
        )

        return {
            'aal': aal,
            'bin_probabilities': p_result.get('bin_probabilities', []),
            'probability_level': probability_level,
            'raw_data': p_result,
            'calculation_details': calc_details,
            'data_source': data_source
        }

    except Exception as e:
        logger.error(f"Probability calculation failed for {risk_type} at ({latitude}, {longitude}): {e}")
        return {
            'aal': 0.0,
            'bin_probabilities': [],
            'probability_level': 'Very Low',
            'raw_data': {},
            'error': str(e)
        }


# ========== DB 저장 ==========
def save_hazard_results(results: List[Dict[str, Any]]) -> None:
    """H 결과를 DB에 배치 저장"""
    try:
        db = DatabaseConnection()
        db.save_hazard_results(results)
        logger.debug(f"Saved {len(results)} hazard results to DB")
    except Exception as e:
        logger.error(f"Failed to save hazard results: {e}")


def save_probability_results(results: List[Dict[str, Any]]) -> None:
    """P(H) 결과를 DB에 배치 저장"""
    try:
        db = DatabaseConnection()
        db.save_probability_results(results)
        logger.debug(f"Saved {len(results)} probability results to DB")
    except Exception as e:
        logger.error(f"Failed to save probability results: {e}")


# ========== 메인 배치 실행 ==========
def run_batch(
    grid_points: List[Tuple[float, float]] = None,
    scenarios: List[str] = None,
    years: List[int] = None,
    risk_types: List[str] = None,
    batch_size: int = 100
) -> None:
    """
    모든 격자점에 대해 H, P(H) 시계열 계산

    Args:
        grid_points: 계산할 격자점 리스트 (None이면 전체)
        scenarios: 계산할 시나리오 리스트 (None이면 전체)
        years: 계산할 연도 리스트 (None이면 2021-2100)
        risk_types: 계산할 리스크 타입 (None이면 전체 9개)
        batch_size: DB 저장 배치 크기
    """
    # 기본값 설정
    if grid_points is None:
        grid_points = get_all_grid_points()
    if scenarios is None:
        scenarios = SCENARIOS
    if years is None:
        years = YEARS
    if risk_types is None:
        risk_types = RISK_TYPES

    start_time = datetime.now()

    total_tasks = len(grid_points) * len(scenarios) * len(years) * len(risk_types)
    completed_tasks = 0

    logger.info("=" * 80)
    logger.info("H, P(H) Timeseries Batch Calculation Started")
    logger.info(f"Grid Points: {len(grid_points)}")
    logger.info(f"Scenarios: {scenarios}")
    logger.info(f"Years: {min(years)}-{max(years)} ({len(years)} years)")
    logger.info(f"Risk Types: {len(risk_types)}")
    logger.info(f"Total Tasks: {total_tasks:,}")
    logger.info("=" * 80)

    hazard_batch = []
    probability_batch = []

    # 시나리오 루프
    for scenario in scenarios:
        logger.info(f"\n{'='*80}")
        logger.info(f"SCENARIO: {scenario}")
        logger.info(f"{'='*80}")

        # 연도 루프
        for year in years:
            logger.info(f"\n  >> Year: {year}")

            # 격자점 루프
            for grid_idx, (lat, lon) in enumerate(grid_points):

                # 리스크 타입 루프
                for risk_type in risk_types:
                    try:
                        # Step 1: H 계산
                        h_result = calculate_hazard(lat, lon, scenario, year, risk_type)

                        hazard_batch.append({
                            'latitude': lat,
                            'longitude': lon,
                            'scenario': scenario,
                            'target_year': year,
                            'risk_type': risk_type,
                            'hazard_score': h_result['hazard_score'],
                            'hazard_score_100': h_result['hazard_score_100'],
                            'hazard_level': h_result['hazard_level']
                        })

                        # Step 2: P(H) 계산
                        p_result = calculate_probability(
                            lat, lon, scenario, year, risk_type,
                            h_result['hazard_score']
                        )

                        probability_batch.append({
                            'latitude': lat,
                            'longitude': lon,
                            'scenario': scenario,
                            'target_year': year,
                            'risk_type': risk_type,
                            'aal': p_result['aal'],
                            'bin_probabilities': p_result.get('bin_probabilities', []),
                            'probability_level': p_result['probability_level']
                        })

                        completed_tasks += 1

                        # 배치 저장
                        if len(hazard_batch) >= batch_size:
                            save_hazard_results(hazard_batch)
                            save_probability_results(probability_batch)
                            hazard_batch = []
                            probability_batch = []

                    except Exception as e:
                        logger.error(
                            f"Failed for {scenario} {year} {risk_type} "
                            f"at ({lat}, {lon}): {e}"
                        )

                # 격자점별 진행률
                if (grid_idx + 1) % 10 == 0:
                    progress = (completed_tasks / total_tasks) * 100
                    logger.info(
                        f"    Grid [{grid_idx + 1}/{len(grid_points)}] "
                        f"- Overall Progress: {progress:.1f}% "
                        f"({completed_tasks:,}/{total_tasks:,})"
                    )

    # 남은 배치 저장
    if hazard_batch:
        save_hazard_results(hazard_batch)
    if probability_batch:
        save_probability_results(probability_batch)

    # 완료 요약
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("\n" + "=" * 80)
    logger.info("BATCH CALCULATION COMPLETED")
    logger.info(f"Total Tasks: {total_tasks:,}")
    logger.info(f"Completed: {completed_tasks:,}")
    logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info(f"Avg Speed: {completed_tasks/duration:.2f} tasks/sec")
    logger.info("=" * 80)


# ========== 실행 진입점 ==========
if __name__ == "__main__":
    """
    실행 예시:

    # 전체 격자점, 전체 시나리오, 전체 연도, 전체 리스크
    python -m modelops.batch.hazard_probability_timeseries_batch

    # 특정 시나리오만 (SSP245)
    python -m modelops.batch.hazard_probability_timeseries_batch --scenario SSP245

    # 특정 연도 범위만 (2020-2050)
    python -m modelops.batch.hazard_probability_timeseries_batch --start-year 2020 --end-year 2050
    """

    try:
        # CLI 인자 파싱 (간단한 예시)
        import argparse
        parser = argparse.ArgumentParser(description='H, P(H) Timeseries Batch Calculation')
        parser.add_argument('--scenario', type=str, help='Single scenario (SSP126, SSP245, SSP370, SSP585)')
        parser.add_argument('--start-year', type=int, default=2021, help='Start year')
        parser.add_argument('--end-year', type=int, default=2100, help='End year')
        parser.add_argument('--batch-size', type=int, default=100, help='DB batch size')

        args = parser.parse_args()

        # 시나리오 설정
        scenarios = [args.scenario] if args.scenario else SCENARIOS

        # 연도 설정
        years = list(range(args.start_year, args.end_year + 1))

        # 배치 실행
        run_batch(
            scenarios=scenarios,
            years=years,
            batch_size=args.batch_size
        )

        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\nBatch calculation interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\nBatch calculation failed: {e}", exc_info=True)
        sys.exit(1)
