'''
파일명: evaal_ondemand_api.py
최종 수정일: 2025-12-13
버전: v01
파일 개요: E, V, AAL On-Demand 계산 함수 (API 호출용)
변경 이력:
    - 2025-12-13: v01 - 최초 생성
        * 사용자 요청 위경도 기반 E, V, AAL 계산
        * API에서 직접 호출 가능한 함수 형태
        * DB에서 H, P(H) 조회 후 E, V, AAL 계산
        * 통합 리스크 계산 포함 (H × E × V)
'''

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Exposure Agents
from ..agents.exposure_calculate.river_flood_exposure_agent import RiverFloodExposureAgent
from ..agents.exposure_calculate.extreme_heat_exposure_agent import ExtremeHeatExposureAgent
from ..agents.exposure_calculate.extreme_cold_exposure_agent import ExtremeColdExposureAgent
from ..agents.exposure_calculate.urban_flood_exposure_agent import UrbanFloodExposureAgent
from ..agents.exposure_calculate.drought_exposure_agent import DroughtExposureAgent
from ..agents.exposure_calculate.typhoon_exposure_agent import TyphoonExposureAgent
from ..agents.exposure_calculate.sea_level_rise_exposure_agent import SeaLevelRiseExposureAgent
from ..agents.exposure_calculate.wildfire_exposure_agent import WildfireExposureAgent
from ..agents.exposure_calculate.water_stress_exposure_agent import WaterStressExposureAgent

# Vulnerability Agents
from ..agents.vulnerability_calculate.extreme_heat_vulnerability_agent import ExtremeHeatVulnerabilityAgent
from ..agents.vulnerability_calculate.extreme_cold_vulnerability_agent import ExtremeColdVulnerabilityAgent
from ..agents.vulnerability_calculate.drought_vulnerability_agent import DroughtVulnerabilityAgent
from ..agents.vulnerability_calculate.river_flood_vulnerability_agent import RiverFloodVulnerabilityAgent
from ..agents.vulnerability_calculate.urban_flood_vulnerability_agent import UrbanFloodVulnerabilityAgent
from ..agents.vulnerability_calculate.sea_level_rise_vulnerability_agent import SeaLevelRiseVulnerabilityAgent
from ..agents.vulnerability_calculate.typhoon_vulnerability_agent import TyphoonVulnerabilityAgent
from ..agents.vulnerability_calculate.wildfire_vulnerability_agent import WildfireVulnerabilityAgent
from ..agents.vulnerability_calculate.water_stress_vulnerability_agent import WaterStressVulnerabilityAgent

# AAL Agent
from ..agents.risk_assessment.aal_scaling_agent import AALScalingAgent

# Site Assessment
from ..agents.site_assessment.relocation_recommender import RelocationRecommender

# Utils
from ..database.connection import DatabaseConnection
from ..utils.hazard_data_collector import HazardDataCollector

logger = logging.getLogger(__name__)


# ========== Agent 매핑 ==========
EXPOSURE_AGENTS = {
    'extreme_heat': ExtremeHeatExposureAgent(),
    'extreme_cold': ExtremeColdExposureAgent(),
    'drought': DroughtExposureAgent(),
    'river_flood': RiverFloodExposureAgent(),
    'urban_flood': UrbanFloodExposureAgent(),
    'sea_level_rise': SeaLevelRiseExposureAgent(),
    'typhoon': TyphoonExposureAgent(),
    'wildfire': WildfireExposureAgent(),
    'water_stress': WaterStressExposureAgent()
}

VULNERABILITY_AGENTS = {
    'extreme_heat': ExtremeHeatVulnerabilityAgent(),
    'extreme_cold': ExtremeColdVulnerabilityAgent(),
    'drought': DroughtVulnerabilityAgent(),
    'river_flood': RiverFloodVulnerabilityAgent(),
    'urban_flood': UrbanFloodVulnerabilityAgent(),
    'sea_level_rise': SeaLevelRiseVulnerabilityAgent(),
    'typhoon': TyphoonVulnerabilityAgent(),
    'wildfire': WildfireVulnerabilityAgent(),
    'water_stress': WaterStressVulnerabilityAgent()
}

AAL_AGENT = AALScalingAgent()


# ========== DB 조회 함수 ==========
def fetch_hazard_from_db(
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    risk_type: str
) -> Dict[str, Any]:
    """
    DB에서 H 결과 조회

    Args:
        latitude: 위도
        longitude: 경도
        scenario: SSP 시나리오
        target_year: 분석 연도
        risk_type: 리스크 타입

    Returns:
        {
            'hazard_score': float,           # 0-1
            'hazard_score_100': float,       # 0-100
            'hazard_level': str              # Very High/High/Medium/Low/Very Low
        }
    """
    try:
        db = DatabaseConnection()
        h_result = db.fetch_hazard_result(
            latitude=latitude,
            longitude=longitude,
            scenario=scenario,
            target_year=target_year,
            risk_type=risk_type
        )

        if not h_result:
            logger.warning(
                f"Hazard not found for {risk_type} at ({latitude}, {longitude}), "
                f"{scenario}, {target_year} - using default"
            )
            return {
                'hazard_score': 0.0,
                'hazard_score_100': 0.0,
                'hazard_level': 'Very Low'
            }

        return h_result

    except Exception as e:
        logger.error(f"Failed to fetch hazard from DB: {e}")
        return {
            'hazard_score': 0.0,
            'hazard_score_100': 0.0,
            'hazard_level': 'Very Low'
        }


def fetch_probability_from_db(
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    risk_type: str
) -> Dict[str, Any]:
    """
    DB에서 P(H) 결과 조회

    Args:
        latitude: 위도
        longitude: 경도
        scenario: SSP 시나리오
        target_year: 분석 연도
        risk_type: 리스크 타입

    Returns:
        {
            'aal': float,                    # Annual Average Loss
            'return_period_years': float,    # 재현주기
            'probability_level': str         # Very High/High/Medium/Low/Very Low
        }
    """
    try:
        db = DatabaseConnection()
        p_result = db.fetch_probability_result(
            latitude=latitude,
            longitude=longitude,
            scenario=scenario,
            target_year=target_year,
            risk_type=risk_type
        )

        if not p_result:
            logger.warning(
                f"Probability not found for {risk_type} at ({latitude}, {longitude}), "
                f"{scenario}, {target_year} - using default"
            )
            return {
                'aal': 0.0,
                'return_period_years': 0.0,
                'probability_level': 'Very Low'
            }

        return p_result

    except Exception as e:
        logger.error(f"Failed to fetch probability from DB: {e}")
        return {
            'aal': 0.0,
            'return_period_years': 0.0,
            'probability_level': 'Very Low'
        }


def fetch_building_info(
    latitude: float,
    longitude: float
) -> Dict[str, Any]:
    """
    건물 정보 조회

    Args:
        latitude: 위도
        longitude: 경도

    Returns:
        건물 정보 딕셔너리
    """
    try:
        db = DatabaseConnection()
        building_info = db.fetch_building_info(latitude, longitude)

        if not building_info:
            logger.warning(f"Building info not found at ({latitude}, {longitude}) - using default")
            return _get_default_building_info()

        return building_info

    except Exception as e:
        logger.error(f"Failed to fetch building info: {e}")
        return _get_default_building_info()


def _get_default_building_info() -> Dict[str, Any]:
    """기본 건물 정보"""
    return {
        'building_age': 20,
        'structure': '철근콘크리트',
        'main_purpose': '주거시설',
        'floors_below': 0,
        'floors_above': 5,
        'total_area': 1000.0,
        'arch_area': 200.0,
        'has_piloti': False,
        'has_seismic_design': True,
        'elevation': 50.0
    }


# ========== E 계산 ==========
def calculate_exposure(
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    risk_type: str
) -> Dict[str, Any]:
    """
    E (Exposure) 계산

    Args:
        latitude: 위도
        longitude: 경도
        scenario: SSP 시나리오
        target_year: 분석 연도
        risk_type: 리스크 타입

    Returns:
        {
            'exposure_score': float,  # 0-100 점수
            'raw_data': Dict          # 원본 계산 결과
        }
    """
    try:
        agent = EXPOSURE_AGENTS.get(risk_type)
        if not agent:
            logger.warning(f"Unknown risk_type for exposure: {risk_type}")
            return {
                'exposure_score': 0.0,
                'raw_data': {},
                'error': f'Unknown risk_type: {risk_type}'
            }

        # HazardDataCollector로 데이터 수집
        collector = HazardDataCollector(scenario=scenario, target_year=target_year)
        collected_data = collector.collect_data(
            lat=latitude,
            lon=longitude,
            risk_type=risk_type
        )

        # 필요한 데이터 추출
        building_data = collected_data.get('building_data', {})
        spatial_data = collected_data.get('spatial_data', {})

        # ExposureAgent 호출
        e_result = agent.calculate_exposure(
            building_data=building_data,
            spatial_data=spatial_data,
            latitude=latitude,
            longitude=longitude
        )

        exposure_score = e_result.get('score', 0.0)

        return {
            'exposure_score': exposure_score,
            'raw_data': e_result
        }

    except Exception as e:
        logger.error(f"Exposure calculation failed for {risk_type}: {e}")
        return {
            'exposure_score': 0.0,
            'raw_data': {},
            'error': str(e)
        }


# ========== V 계산 ==========
def calculate_vulnerability(
    latitude: float,
    longitude: float,
    risk_type: str,
    exposure_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    V (Vulnerability) 계산

    Args:
        latitude: 위도
        longitude: 경도
        risk_type: 리스크 타입
        exposure_data: Exposure 계산 결과

    Returns:
        {
            'vulnerability_score': float,  # 0-100 점수
            'vulnerability_level': str,    # very_high/high/medium/low/very_low
            'factors': Dict,               # 취약성 요인
            'raw_data': Dict               # 원본 계산 결과
        }
    """
    try:
        agent = VULNERABILITY_AGENTS.get(risk_type)
        if not agent:
            logger.warning(f"Unknown risk_type for vulnerability: {risk_type}")
            return {
                'vulnerability_score': 50.0,
                'vulnerability_level': 'medium',
                'factors': {},
                'raw_data': {},
                'error': f'Unknown risk_type: {risk_type}'
            }

        # VulnerabilityAgent 호출
        v_result = agent.calculate_vulnerability(exposure_data.get('raw_data', {}))

        return {
            'vulnerability_score': v_result.get('score', 50.0),
            'vulnerability_level': v_result.get('level', 'medium'),
            'factors': v_result.get('factors', {}),
            'raw_data': v_result
        }

    except Exception as e:
        logger.error(f"Vulnerability calculation failed for {risk_type}: {e}")
        return {
            'vulnerability_score': 50.0,
            'vulnerability_level': 'medium',
            'factors': {},
            'raw_data': {},
            'error': str(e)
        }


# ========== AAL 계산 ==========
def calculate_aal(
    base_aal: float,
    vulnerability_score: float,
    insurance_rate: float = 0.0,
    asset_value: Optional[float] = None
) -> Dict[str, Any]:
    """
    AAL (Average Annual Loss) 계산

    Args:
        base_aal: 기본 AAL (P(H)의 aal)
        vulnerability_score: V 점수 (0-100)
        insurance_rate: 보험 가입률 (0-1)
        asset_value: 자산 가치 (선택)

    Returns:
        {
            'base_aal': float,
            'vulnerability_scale': float,
            'final_aal': float,
            'insurance_rate': float,
            'expected_loss': Optional[float],
            'grade': str
        }
    """
    try:
        aal_result = AAL_AGENT.scale_aal(
            base_aal=base_aal,
            vulnerability_score=vulnerability_score,
            insurance_rate=insurance_rate,
            asset_value=asset_value
        )

        # AAL 등급 분류
        final_aal = aal_result.get('final_aal', 0.0)
        grade = AAL_AGENT.classify_aal_grade(final_aal)
        aal_result['grade'] = grade

        return aal_result

    except Exception as e:
        logger.error(f"AAL calculation failed: {e}")
        return {
            'base_aal': base_aal,
            'vulnerability_scale': 1.0,
            'final_aal': base_aal,
            'insurance_rate': insurance_rate,
            'expected_loss': None,
            'grade': '-',
            'error': str(e)
        }


# ========== 통합 리스크 계산 ==========
def calculate_integrated_risk(
    h_score: float,
    e_score: float,
    v_score: float
) -> Dict[str, Any]:
    """
    통합 리스크 계산 (H × E × V)

    Args:
        h_score: Hazard 점수 (0-100)
        e_score: Exposure 점수 (0-100)
        v_score: Vulnerability 점수 (0-100)

    Returns:
        {
            'h_score': float,
            'e_score': float,
            'v_score': float,
            'integrated_risk_score': float,  # 0-100
            'risk_level': str,               # Very High/High/Medium/Low/Very Low
            'calculation_method': str,
            'formula': str
        }
    """
    # H × E × V / 10000 (0-100 범위로 정규화)
    raw_risk = (h_score * e_score * v_score) / 10000.0

    # 위험도 등급 분류
    if raw_risk >= 80:
        risk_level = 'Very High'
    elif raw_risk >= 60:
        risk_level = 'High'
    elif raw_risk >= 40:
        risk_level = 'Medium'
    elif raw_risk >= 20:
        risk_level = 'Low'
    else:
        risk_level = 'Very Low'

    return {
        'h_score': round(h_score, 2),
        'e_score': round(e_score, 2),
        'v_score': round(v_score, 2),
        'integrated_risk_score': round(raw_risk, 2),
        'risk_level': risk_level,
        'calculation_method': 'H × E × V / 10000',
        'formula': f'{h_score:.2f} × {e_score:.2f} × {v_score:.2f} / 10000 = {raw_risk:.2f}'
    }


# ========== DB 저장 함수 ==========
def _save_results_to_db(
    latitude: float,
    longitude: float,
    risk_types: List[str],
    results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    계산 결과를 DB에 저장

    Args:
        latitude: 위도
        longitude: 경도
        risk_types: 리스크 타입 리스트
        results: 계산 결과 딕셔너리

    Returns:
        저장 결과 요약
    """
    db = DatabaseConnection()
    save_summary = {
        'exposure_saved': 0,
        'vulnerability_saved': 0,
        'aal_saved': 0,
        'errors': []
    }

    try:
        # 1. Exposure 결과 저장
        exposure_records = []
        for risk_type in risk_types:
            e_data = results['exposure'].get(risk_type, {})
            raw_data = e_data.get('raw_data', {})

            exposure_records.append({
                'latitude': latitude,
                'longitude': longitude,
                'risk_type': risk_type,
                'exposure_score': e_data.get('exposure_score', 0.0),
                'proximity_factor': raw_data.get('proximity_factor', 0.0),
                'normalized_asset_value': raw_data.get('normalized_asset_value', 0.0)
            })

        if exposure_records:
            db.save_exposure_results(exposure_records)
            save_summary['exposure_saved'] = len(exposure_records)
            logger.info(f"Saved {len(exposure_records)} exposure results")

        # 2. Vulnerability 결과 저장
        vulnerability_records = []
        for risk_type in risk_types:
            v_data = results['vulnerability'].get(risk_type, {})

            vulnerability_records.append({
                'latitude': latitude,
                'longitude': longitude,
                'risk_type': risk_type,
                'vulnerability_score': v_data.get('vulnerability_score', 50.0),
                'vulnerability_level': v_data.get('vulnerability_level', 'medium'),
                'factors': v_data.get('factors', {})
            })

        if vulnerability_records:
            db.save_vulnerability_results(vulnerability_records)
            save_summary['vulnerability_saved'] = len(vulnerability_records)
            logger.info(f"Saved {len(vulnerability_records)} vulnerability results")

        # 3. AAL Scaled 결과 저장
        aal_records = []
        for risk_type in risk_types:
            aal_data = results['aal'].get(risk_type, {})

            aal_records.append({
                'latitude': latitude,
                'longitude': longitude,
                'risk_type': risk_type,
                'base_aal': aal_data.get('base_aal', 0.0),
                'vulnerability_scale': aal_data.get('vulnerability_scale', 1.0),
                'final_aal': aal_data.get('final_aal', 0.0),
                'insurance_rate': aal_data.get('insurance_rate', 0.0),
                'expected_loss': aal_data.get('expected_loss')
            })

        if aal_records:
            db.save_aal_scaled_results(aal_records)
            save_summary['aal_saved'] = len(aal_records)
            logger.info(f"Saved {len(aal_records)} AAL scaled results")

    except Exception as e:
        error_msg = f"DB save error: {str(e)}"
        logger.error(error_msg)
        save_summary['errors'].append(error_msg)

    return save_summary


# ========== 메인 API 함수 ==========
def calculate_evaal_ondemand(
    latitude: float,
    longitude: float,
    scenario: str = 'SSP245',
    target_year: int = 2030,
    risk_types: Optional[List[str]] = None,
    insurance_rate: float = 0.0,
    asset_value: Optional[float] = None,
    save_to_db: bool = False
) -> Dict[str, Any]:
    """
    E, V, AAL On-Demand 계산 (API 호출용 메인 함수)

    Args:
        latitude: 위도
        longitude: 경도
        scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
        target_year: 분석 연도 (2021-2100)
        risk_types: 리스크 타입 리스트 (None이면 전체 9개)
        insurance_rate: 보험 가입률 (0-1)
        asset_value: 자산 가치 (선택)
        save_to_db: DB 저장 여부 (기본 False)

    Returns:
        {
            'status': 'success' | 'error',
            'latitude': float,
            'longitude': float,
            'scenario': str,
            'target_year': int,
            'results': {
                'hazard': {risk_type: {...}},
                'probability': {risk_type: {...}},
                'exposure': {risk_type: {...}},
                'vulnerability': {risk_type: {...}},
                'aal': {risk_type: {...}},
                'integrated_risk': {risk_type: {...}}
            },
            'summary': {...},
            'metadata': {...}
        }
    """
    start_time = datetime.now()

    try:
        # 기본값 설정
        if risk_types is None:
            risk_types = [
                'extreme_heat', 'extreme_cold', 'wildfire', 'drought',
                'water_stress', 'sea_level_rise', 'river_flood',
                'urban_flood', 'typhoon'
            ]

        logger.info(
            f"Starting E, V, AAL calculation: "
            f"({latitude}, {longitude}), {scenario}, {target_year}"
        )

        results = {
            'hazard': {},
            'probability': {},
            'exposure': {},
            'vulnerability': {},
            'aal': {},
            'integrated_risk': {}
        }

        # 리스크별 계산
        for risk_type in risk_types:
            logger.debug(f"Calculating {risk_type}...")

            # Step 1: DB에서 H, P(H) 조회
            h_result = fetch_hazard_from_db(latitude, longitude, scenario, target_year, risk_type)
            p_result = fetch_probability_from_db(latitude, longitude, scenario, target_year, risk_type)

            results['hazard'][risk_type] = h_result
            results['probability'][risk_type] = p_result

            # Step 2: E 계산
            e_result = calculate_exposure(latitude, longitude, scenario, target_year, risk_type)
            results['exposure'][risk_type] = e_result

            # Step 3: V 계산
            v_result = calculate_vulnerability(latitude, longitude, risk_type, e_result)
            results['vulnerability'][risk_type] = v_result

            # Step 4: AAL 계산
            base_aal = p_result.get('aal', 0.0)
            v_score = v_result.get('vulnerability_score', 50.0)
            aal_result = calculate_aal(base_aal, v_score, insurance_rate, asset_value)
            results['aal'][risk_type] = aal_result

            # Step 5: 통합 리스크 계산 (H × E × V)
            h_score = h_result.get('hazard_score_100', 0.0)
            e_score = e_result.get('exposure_score', 0.0)
            integrated_risk = calculate_integrated_risk(h_score, e_score, v_score)
            results['integrated_risk'][risk_type] = integrated_risk

        # 요약 통계 계산
        summary = _calculate_summary(results)

        # DB 저장 (옵션)
        save_summary = None
        if save_to_db:
            logger.info("Saving results to DB...")
            save_summary = _save_results_to_db(latitude, longitude, risk_types, results)
            logger.info(f"DB save completed: {save_summary}")

        # 메타데이터
        end_time = datetime.now()
        metadata = {
            'latitude': latitude,
            'longitude': longitude,
            'scenario': scenario,
            'target_year': target_year,
            'calculation_time': (end_time - start_time).total_seconds(),
            'calculated_at': end_time.isoformat(),
            'total_risks_processed': len(risk_types),
            'saved_to_db': save_to_db
        }

        logger.info(
            f"E, V, AAL calculation completed: {metadata['calculation_time']:.2f}s"
        )

        response = {
            'status': 'success',
            'latitude': latitude,
            'longitude': longitude,
            'scenario': scenario,
            'target_year': target_year,
            'results': results,
            'summary': summary,
            'metadata': metadata
        }

        # 저장 결과 포함
        if save_summary:
            response['save_summary'] = save_summary

        return response

    except Exception as e:
        logger.error(f"E, V, AAL calculation failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'latitude': latitude,
            'longitude': longitude,
            'scenario': scenario,
            'target_year': target_year
        }


# ========== 후보지 추천 (Relocation) ==========
def recommend_locations_ondemand(
    candidate_grids: List[Dict[str, float]],
    building_info: Optional[Dict[str, Any]] = None,
    asset_info: Optional[Dict[str, Any]] = None,
    scenario: str = 'SSP245',
    target_year: int = 2040,
    max_candidates: int = 3
) -> Dict[str, Any]:
    """
    사업장 이전 후보지 추천 (On-Demand)

    Args:
        candidate_grids: 후보 격자 리스트 [{'latitude': ..., 'longitude': ...}, ...]
        building_info: 건물 정보 (None이면 기본값 사용)
        asset_info: 자산 정보 (선택)
        scenario: SSP 시나리오
        target_year: 목표 연도
        max_candidates: 추천 개수

    Returns:
        추천 결과 딕셔너리
    """
    try:
        # 건물 정보가 없으면 기본값 사용
        if not building_info:
             building_info = _get_default_building_info()

        recommender = RelocationRecommender(scenario=scenario, target_year=target_year)
        
        result = recommender.recommend_locations(
            candidate_grids=candidate_grids,
            building_info=building_info,
            asset_info=asset_info,
            max_candidates=max_candidates
        )
        
        return {
            'status': 'success',
            'scenario': scenario,
            'target_year': target_year,
            'recommendation_result': result
        }
        
    except Exception as e:
        logger.error(f"Location recommendation failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'scenario': scenario,
            'target_year': target_year
        }


def compare_current_and_candidates_ondemand(
    current_site: Dict[str, float], # {'latitude': ..., 'longitude': ...}
    recommended_candidates_result: Dict[str, Any], # The 'recommendation_result' from recommend_locations_ondemand
    building_info: Optional[Dict[str, Any]] = None,
    asset_info: Optional[Dict[str, Any]] = None,
    scenario: str = 'SSP245',
    target_year: int = 2040
) -> Dict[str, Any]:
    """
    현재 사업장과 추천 후보지들 간의 리스크를 비교 (On-Demand)

    Args:
        current_site: 현재 사업장 정보 {'latitude': ..., 'longitude': ...}
        recommended_candidates_result: recommend_locations_ondemand의 'recommendation_result' 필드 값
        building_info: 건물 정보 (None이면 기본값 사용)
        asset_info: 자산 정보 (선택)
        scenario: SSP 시나리오
        target_year: 목표 연도

    Returns:
        비교 결과 딕셔너리
    """
    try:
        if not building_info:
             building_info = _get_default_building_info()

        recommender = RelocationRecommender(scenario=scenario, target_year=target_year)
        
        comparison_result = recommender.compare_current_and_candidates(
            current_site=current_site,
            candidate_result=recommended_candidates_result,
            building_info=building_info,
            asset_info=asset_info
        )
        
        return {
            'status': 'success',
            'scenario': scenario,
            'target_year': target_year,
            'comparison_result': comparison_result
        }
        
    except Exception as e:
        logger.error(f"Comparison between current site and candidates failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'scenario': scenario,
            'target_year': target_year
        }


# ========== 요약 통계 ==========
def _calculate_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """요약 통계 계산"""
    # 평균 점수
    h_scores = [h.get('hazard_score_100', 0.0) for h in results['hazard'].values()]
    e_scores = [e.get('exposure_score', 0.0) for e in results['exposure'].values()]
    v_scores = [v.get('vulnerability_score', 0.0) for v in results['vulnerability'].values()]
    risk_scores = [r.get('integrated_risk_score', 0.0) for r in results['integrated_risk'].values()]

    avg_hazard = sum(h_scores) / len(h_scores) if h_scores else 0.0
    avg_exposure = sum(e_scores) / len(e_scores) if e_scores else 0.0
    avg_vulnerability = sum(v_scores) / len(v_scores) if v_scores else 0.0
    avg_integrated_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

    # 최고 통합 리스크
    highest_integrated_risk = max(
        results['integrated_risk'].items(),
        key=lambda x: x[1].get('integrated_risk_score', 0.0),
        default=(None, {})
    )

    # 최고 AAL 리스크
    highest_aal_risk = max(
        results['aal'].items(),
        key=lambda x: x[1].get('final_aal', 0.0),
        default=(None, {})
    )

    # Top 3 리스크
    top_3_risks = sorted(
        results['integrated_risk'].items(),
        key=lambda x: x[1].get('integrated_risk_score', 0.0),
        reverse=True
    )[:3]

    return {
        'average_hazard': round(avg_hazard, 2),
        'average_exposure': round(avg_exposure, 2),
        'average_vulnerability': round(avg_vulnerability, 2),
        'average_integrated_risk': round(avg_integrated_risk, 2),
        'highest_integrated_risk': {
            'risk_type': highest_integrated_risk[0],
            'score': highest_integrated_risk[1].get('integrated_risk_score', 0.0),
            'level': highest_integrated_risk[1].get('risk_level', 'Very Low')
        } if highest_integrated_risk[0] else None,
        'highest_aal_risk': {
            'risk_type': highest_aal_risk[0],
            'final_aal': highest_aal_risk[1].get('final_aal', 0.0),
            'grade': highest_aal_risk[1].get('grade', '-')
        } if highest_aal_risk[0] else None,
        'top_3_risks': [
            {
                'rank': i + 1,
                'risk_type': risk_type,
                'score': risk_data.get('integrated_risk_score', 0.0),
                'level': risk_data.get('risk_level', 'Very Low')
            }
            for i, (risk_type, risk_data) in enumerate(top_3_risks)
        ]
    }
