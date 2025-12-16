"""
Site Assessment API
사업장 리스크 계산 및 이전 후보지 추천 API
"""

from fastapi import APIRouter, HTTPException
from ..schemas.site_models import (
    SiteRiskRequest,
    SiteRiskResponse,
    SiteRelocationRequest,
    SiteRelocationResponse
)
from ...batch.evaal_ondemand_api import calculate_evaal_ondemand
from ...config.settings import settings
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/site-assessment", tags=["site-assessment"])

# ========== 상수 정의 ==========
# 계산할 시나리오와 연도 목록
SCENARIOS = ["SSP126", "SSP245", "SSP370", "SSP585"]
TARGET_YEARS = list(range(2021, 2101))  # 2021-2100 (80년)
# 병렬 처리 워커 수
MAX_WORKERS = 8
# 9개 리스크 타입
RISK_TYPES = [
    'extreme_heat', 'extreme_cold', 'drought',
    'river_flood', 'urban_flood', 'sea_level_rise',
    'typhoon', 'wildfire', 'water_stress'
]


async def _notify_recommendation_completed(batch_id: str):
    """
    FastAPI 서버에 후보지 추천 완료 알림

    Args:
        batch_id: 배치 작업 ID
    """
    if not batch_id:
        logger.warning("batch_id가 없어 콜백을 건너뜁니다.")
        return

    callback_url = f"{settings.fastapi_url}/api/analysis/modelops/recommendation-completed"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {}
            if settings.fastapi_api_key:
                headers['X-API-Key'] = settings.fastapi_api_key

            response = await client.post(
                callback_url,
                params={'batchId': batch_id},
                headers=headers
            )

            if response.status_code == 200:
                logger.info(f"콜백 성공: batch_id={batch_id}")
            else:
                logger.warning(f"콜백 실패 (HTTP {response.status_code}): {response.text}")

    except Exception as e:
        logger.error(f"콜백 호출 중 오류 (batch_id={batch_id}): {e}", exc_info=True)


def _calculate_single_site_scenario_year(
    site_id: str,
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    insurance_rate: float,
    asset_value: Optional[float]
) -> Dict[str, Any]:
    """
    단일 사업장의 단일 시나리오/연도 조합 계산 (병렬 처리용 헬퍼 함수)

    Returns:
        Dict: {
            'site_id': str,
            'scenario': str,
            'year': int,
            'status': 'success'|'failed',
            'error_message': Optional[str]
        }
    """
    try:
        result = calculate_evaal_ondemand(
            latitude=latitude,
            longitude=longitude,
            scenario=scenario,
            target_year=target_year,
            risk_types=RISK_TYPES,
            insurance_rate=insurance_rate,
            asset_value=asset_value,
            save_to_db=True  # DB에 결과 저장
        )

        if result.get('status') == 'error':
            error_msg = result.get('error', 'E, V, AAL 계산 중 알 수 없는 오류 발생')
            return {
                'site_id': site_id,
                'scenario': scenario,
                'year': target_year,
                'status': 'failed',
                'error_message': error_msg
            }

        return {
            'site_id': site_id,
            'scenario': scenario,
            'year': target_year,
            'status': 'success',
            'error_message': None
        }

    except Exception as e:
        return {
            'site_id': site_id,
            'scenario': scenario,
            'year': target_year,
            'status': 'failed',
            'error_message': str(e)
        }


@router.post("/calculate", response_model=SiteRiskResponse)
async def calculate_site_risk(request: SiteRiskRequest):
    """
    사업장 리스크 계산 API (다중 사업장 병렬 처리)
    (모든 시나리오 × 모든 연도 조합에 대해 E, V, AAL 계산 및 DB 저장)
    """
    total_sites = len(request.sites)
    logger.info(f"사업장 리스크 계산 요청: {total_sites}개 사업장")

    # asset_info 처리
    insurance_rate = request.asset_info.insurance_coverage_rate if request.asset_info else 0.0
    asset_value = request.asset_info.total_value if request.asset_info else None

    calculation_start_time = datetime.now()

    # 전체 계산 개수 (사업장 수 × 시나리오 수 × 연도 수)
    total_calculations = total_sites * len(SCENARIOS) * len(TARGET_YEARS)
    logger.info(f"총 {total_calculations}개 조합 계산 시작 "
                f"({total_sites} sites × {len(SCENARIOS)} scenarios × {len(TARGET_YEARS)} years)")

    successful_sites = 0
    failed_sites = 0
    site_errors = {}

    try:
        # 병렬 처리로 모든 사업장의 모든 시나리오/연도 조합 계산
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 모든 작업 제출
            futures = []
            for site_id, site_location in request.sites.items():
                for scenario in SCENARIOS:
                    for year in TARGET_YEARS:
                        future = executor.submit(
                            _calculate_single_site_scenario_year,
                            site_id,
                            site_location.latitude,
                            site_location.longitude,
                            scenario,
                            year,
                            insurance_rate,
                            asset_value
                        )
                        futures.append(future)

            # 결과 수집 및 사업장별 성공/실패 추적
            completed_count = 0
            site_results = {site_id: {'success': 0, 'failed': 0} for site_id in request.sites.keys()}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    site_id = result['site_id']

                    if result['status'] == 'success':
                        site_results[site_id]['success'] += 1
                    else:
                        site_results[site_id]['failed'] += 1
                        # 첫 번째 에러만 기록
                        if site_id not in site_errors:
                            site_errors[site_id] = result['error_message']

                    completed_count += 1

                    # 진행 상황 로그 (10% 단위)
                    if completed_count % max(1, total_calculations // 10) == 0:
                        progress = (completed_count / total_calculations) * 100
                        logger.info(f"진행률: {completed_count}/{total_calculations} ({progress:.1f}%)")

                except Exception as e:
                    logger.error(f"결과 수집 중 오류: {e}")
                    completed_count += 1

            # 사업장별 성공/실패 집계
            for site_id, counts in site_results.items():
                if counts['failed'] == 0:
                    successful_sites += 1
                else:
                    failed_sites += 1

        calculation_end_time = datetime.now()
        elapsed_time = (calculation_end_time - calculation_start_time).total_seconds()

        logger.info(f"사업장 리스크 계산 완료 (총 {elapsed_time:.1f}초 소요)")
        logger.info(f"성공: {successful_sites}/{total_sites} 사업장")
        logger.info(f"실패: {failed_sites}/{total_sites} 사업장")

        # 실패한 사업장 로그
        if site_errors:
            logger.warning(f"실패한 사업장 목록:")
            for site_id, error_msg in list(site_errors.items())[:5]:
                logger.warning(f"  - {site_id}: {error_msg}")
            if len(site_errors) > 5:
                logger.warning(f"  ... 외 {len(site_errors) - 5}개 사업장 실패")

        # 상태 결정
        if failed_sites == 0:
            status = "success"
            message = f"모든 사업장 ({total_sites}개) 계산 성공"
        elif successful_sites == 0:
            status = "failed"
            message = f"모든 사업장 ({total_sites}개) 계산 실패"
        else:
            status = "partial"
            message = f"{successful_sites}/{total_sites} 사업장 계산 성공, {failed_sites}개 실패"

        # Response 반환
        return SiteRiskResponse(
            status=status,
            total_sites=total_sites,
            successful_sites=successful_sites,
            failed_sites=failed_sites,
            message=message,
            calculated_at=calculation_end_time
        )

    except Exception as e:
        logger.error(f"사업장 리스크 계산 중 내부 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _calculate_single_site_candidates(
    site_id: str,
    candidate_grids: List[Dict[str, float]],
    building_info: Dict[str, Any],
    asset_info: Optional[Dict[str, Any]],
    scenario: str,
    target_year: int
) -> Dict[str, Any]:
    """
    단일 사업장의 후보지 계산 (병렬 처리용 헬퍼 함수)

    Returns:
        Dict: {
            'site_id': str,
            'status': 'success'|'failed',
            'candidates_saved': int,
            'error_message': Optional[str]
        }
    """
    try:
        from ..database.connection import DatabaseConnection

        # 보험 가입률 추출
        insurance_rate = asset_info.get('insurance_coverage_rate', 0.0) if asset_info else 0.0
        asset_value = asset_info.get('total_value') if asset_info else None

        saved_count = 0

        # 각 후보지에 대해 계산
        for grid in candidate_grids:
            lat, lon = grid['latitude'], grid['longitude']

            # 이미 평가된 위치는 건너뛰기
            if DatabaseConnection.check_candidate_exists(lat, lon, scenario, target_year):
                logger.debug(f"[{site_id}] 이미 존재하는 후보지 건너뜀: ({lat}, {lon})")
                continue

            # calculate_evaal_ondemand 호출 (save_to_db=False)
            result = calculate_evaal_ondemand(
                latitude=lat,
                longitude=lon,
                scenario=scenario,
                target_year=target_year,
                risk_types=RISK_TYPES,
                insurance_rate=insurance_rate,
                asset_value=asset_value,
                save_to_db=False  # 후보지는 별도 테이블에 저장
            )

            if result.get('status') == 'error':
                logger.warning(f"[{site_id}] 후보지 ({lat}, {lon}) 계산 실패: {result.get('error')}")
                continue

            # candidate_sites 테이블에 저장
            results_data = result.get('results', {})

            # AAL 합산 및 risk_details 구성
            aal_by_risk = {}
            total_aal = 0.0
            risk_scores = []

            for risk_type in RISK_TYPES:
                aal_data = results_data.get('aal', {}).get(risk_type, {})
                final_aal = aal_data.get('final_aal', 0.0)
                aal_by_risk[risk_type] = final_aal
                total_aal += final_aal

                integrated_risk_data = results_data.get('integrated_risk', {}).get(risk_type, {})
                risk_scores.append(integrated_risk_data.get('integrated_risk_score', 0.0))

            average_integrated_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
            risk_score = int(round(average_integrated_risk))  # 0-100 정수

            # candidate_sites 테이블에 저장
            DatabaseConnection.save_candidate_site(
                latitude=lat,
                longitude=lon,
                aal=total_aal,
                aal_by_risk=aal_by_risk,
                risk_score=risk_score,
                risks=None,  # 또는 results_data 전체
                reference_site_id=site_id
            )

            saved_count += 1

        return {
            'site_id': site_id,
            'status': 'success',
            'candidates_saved': saved_count,
            'error_message': None
        }

    except Exception as e:
        logger.error(f"[{site_id}] 후보지 계산 실패: {e}", exc_info=True)
        return {
            'site_id': site_id,
            'status': 'failed',
            'candidates_saved': 0,
            'error_message': str(e)
        }


@router.post("/recommend-locations", response_model=SiteRelocationResponse)
async def recommend_relocation_locations(request: SiteRelocationRequest):
    """
    사업장 이전 후보지 추천 API (다중 사업장 병렬 처리)
    (On-Demand 계산 + candidate_sites DB 저장)
    """
    total_sites = len(request.sites)
    logger.info(f"이전 후보지 추천 요청: {total_sites}개 사업장, batch_id={request.batch_id}")

    # 1. candidate_grids 처리: 없으면 고정 위치 사용
    if request.candidate_grids is None or len(request.candidate_grids) == 0:
        from ..utils.candidate_location import LOCATION_MAP

        # LOCATION_MAP: set of {"lat": ..., "lng": ...}
        # Convert to list of {"latitude": ..., "longitude": ...}
        candidate_grids = [
            {'latitude': loc['lat'], 'longitude': loc['lng']}
            for loc in LOCATION_MAP
        ]
        logger.info(f"고정 위치 사용: {len(candidate_grids)}개")
    else:
        candidate_grids = [
            {'latitude': grid.latitude, 'longitude': grid.longitude}
            for grid in request.candidate_grids
        ]
        logger.info(f"사용자 제공 위치: {len(candidate_grids)}개")

    total_grids = len(candidate_grids)

    if total_grids > 2000:
        logger.warning(f"candidate_grids가 {total_grids}개로 많습니다. 처리 시간이 오래 걸릴 수 있습니다.")

    # 검색 기준 처리
    search_criteria = request.search_criteria or {}
    scenario = search_criteria.get('ssp_scenario', 'SSP245')
    target_year = search_criteria.get('target_year', 2040)

    # building_info, asset_info 변환
    building_info = request.building_info.model_dump() if request.building_info else None
    asset_info = request.asset_info.model_dump() if request.asset_info else None

    calculation_start_time = datetime.now()

    successful_sites = 0
    failed_sites = 0
    total_candidates_saved = 0
    site_errors = {}

    try:
        # 병렬 처리로 모든 사업장의 후보지 계산
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []

            for site_id in request.sites.keys():
                future = executor.submit(
                    _calculate_single_site_candidates,
                    site_id,
                    candidate_grids,
                    building_info,
                    asset_info,
                    scenario,
                    target_year
                )
                futures.append(future)

            # 결과 수집
            for future in as_completed(futures):
                try:
                    result = future.result()
                    site_id = result['site_id']

                    if result['status'] == 'success':
                        successful_sites += 1
                        total_candidates_saved += result['candidates_saved']
                        logger.info(f"[{site_id}] 후보지 {result['candidates_saved']}개 저장 완료")
                    else:
                        failed_sites += 1
                        site_errors[site_id] = result['error_message']
                        logger.error(f"[{site_id}] 후보지 계산 실패: {result['error_message']}")

                except Exception as e:
                    logger.error(f"결과 수집 중 오류: {e}")
                    failed_sites += 1

        calculation_end_time = datetime.now()
        elapsed_time = (calculation_end_time - calculation_start_time).total_seconds()

        logger.info(f"후보지 추천 완료 (총 {elapsed_time:.1f}초 소요)")
        logger.info(f"성공: {successful_sites}/{total_sites} 사업장")
        logger.info(f"실패: {failed_sites}/{total_sites} 사업장")
        logger.info(f"총 저장 후보지: {total_candidates_saved}개")

        # 실패한 사업장 로그
        if site_errors:
            logger.warning(f"실패한 사업장 목록:")
            for site_id, error_msg in list(site_errors.items())[:5]:
                logger.warning(f"  - {site_id}: {error_msg}")
            if len(site_errors) > 5:
                logger.warning(f"  ... 외 {len(site_errors) - 5}개 사업장 실패")

        # 상태 결정
        if failed_sites == 0:
            status = "success"
            message = f"모든 사업장 ({total_sites}개) 후보지 계산 성공, 총 {total_candidates_saved}개 후보지 저장"
        elif successful_sites == 0:
            status = "failed"
            message = f"모든 사업장 ({total_sites}개) 후보지 계산 실패"
        else:
            status = "partial"
            message = f"{successful_sites}/{total_sites} 사업장 성공, {total_candidates_saved}개 후보지 저장"

        # 콜백 호출 (완료 알림)
        if request.batch_id:
            try:
                await _notify_recommendation_completed(request.batch_id)
            except Exception as callback_error:
                logger.error(f"콜백 호출 실패 (무시하고 계속): {callback_error}")

        # Response 반환
        return SiteRelocationResponse(
            status=status,
            total_sites=total_sites,
            successful_sites=successful_sites,
            failed_sites=failed_sites,
            total_candidates_saved=total_candidates_saved,
            message=message,
            batch_id=request.batch_id,
            calculated_at=calculation_end_time
        )

    except Exception as e:
        logger.error(f"이전 후보지 추천 중 내부 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
