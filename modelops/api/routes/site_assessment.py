"""
Site Assessment API
사업장 리스크 계산 및 이전 후보지 추천 API
"""

from fastapi import APIRouter, HTTPException
from ..schemas.site_models import (
    SiteRiskRequest,
    SiteRiskResponse,
    SiteRelocationRequest,
    SiteRelocationResponse,
    CalculationResult
)
from ...batch.evaal_ondemand_api import (
    calculate_evaal_ondemand,
    recommend_locations_ondemand
)
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/site-assessment", tags=["site-assessment"])

# ========== 상수 정의 ==========
# 계산할 시나리오와 연도 목록
SCENARIOS = ["SSP126", "SSP245", "SSP370", "SSP585"]
TARGET_YEARS = list(range(2021, 2101))  # 2021-2100 (80년)
# 병렬 처리 워커 수
MAX_WORKERS = 8


def _calculate_single_scenario_year(
    latitude: float,
    longitude: float,
    scenario: str,
    target_year: int,
    insurance_rate: float,
    asset_value: Optional[float]
) -> CalculationResult:
    """
    단일 시나리오/연도 조합 계산 (병렬 처리용 헬퍼 함수)

    Returns:
        CalculationResult: 계산 결과 (success/failed)
    """
    try:
        result = calculate_evaal_ondemand(
            latitude=latitude,
            longitude=longitude,
            scenario=scenario,
            target_year=target_year,
            risk_types=None,  # None이면 전체 리스크
            insurance_rate=insurance_rate,
            asset_value=asset_value,
            save_to_db=True  # DB에 결과 저장
        )

        if result.get('status') == 'error':
            error_msg = result.get('error', 'E, V, AAL 계산 중 알 수 없는 오류 발생')
            return CalculationResult(
                scenario=scenario,
                year=target_year,
                status='failed',
                error_message=error_msg
            )

        return CalculationResult(
            scenario=scenario,
            year=target_year,
            status='success',
            error_message=None
        )

    except Exception as e:
        return CalculationResult(
            scenario=scenario,
            year=target_year,
            status='failed',
            error_message=str(e)
        )


@router.post("/calculate", response_model=SiteRiskResponse)
async def calculate_site_risk(request: SiteRiskRequest):
    """
    사업장 리스크 계산 API
    (모든 시나리오 × 모든 연도 조합에 대해 E, V, AAL 계산 및 DB 저장)
    """
    logger.info(f"사업장 리스크 계산 요청: ({request.latitude}, {request.longitude})")
    if request.site_id:
        logger.info(f"  site_id: {request.site_id}")

    # 총 계산 개수
    total_calculations = len(SCENARIOS) * len(TARGET_YEARS)
    logger.info(f"  총 {total_calculations}개 시나리오/연도 조합 계산 시작 "
                f"({len(SCENARIOS)} scenarios × {len(TARGET_YEARS)} years)")

    try:
        # asset_info 처리
        insurance_rate = request.asset_info.insurance_coverage_rate if request.asset_info else 0.0
        asset_value = request.asset_info.total_value if request.asset_info else None

        calculation_start_time = datetime.now()
        results: List[CalculationResult] = []

        # 병렬 처리로 모든 시나리오/연도 조합 계산
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 모든 작업 제출
            future_to_params = {}
            for scenario in SCENARIOS:
                for year in TARGET_YEARS:
                    future = executor.submit(
                        _calculate_single_scenario_year,
                        request.latitude,
                        request.longitude,
                        scenario,
                        year,
                        insurance_rate,
                        asset_value
                    )
                    future_to_params[future] = (scenario, year)

            # 결과 수집
            completed_count = 0
            for future in as_completed(future_to_params):
                scenario, year = future_to_params[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed_count += 1

                    # 진행 상황 로그 (10% 단위)
                    if completed_count % max(1, total_calculations // 10) == 0:
                        progress = (completed_count / total_calculations) * 100
                        logger.info(f"  진행률: {completed_count}/{total_calculations} ({progress:.1f}%)")

                except Exception as e:
                    logger.error(f"  {scenario}/{year} 계산 실패: {e}")
                    results.append(CalculationResult(
                        scenario=scenario,
                        year=year,
                        status='failed',
                        error_message=str(e)
                    ))

        # 성공/실패 통계
        successful_count = sum(1 for r in results if r.status == 'success')
        failed_count = sum(1 for r in results if r.status == 'failed')

        calculation_end_time = datetime.now()
        elapsed_time = (calculation_end_time - calculation_start_time).total_seconds()

        logger.info(f"사업장 리스크 계산 완료 (총 {elapsed_time:.1f}초 소요)")
        logger.info(f"  성공: {successful_count}/{total_calculations}")
        logger.info(f"  실패: {failed_count}/{total_calculations}")

        # 실패한 항목 상세 로그
        if failed_count > 0:
            failed_items = [r for r in results if r.status == 'failed']
            logger.warning(f"  실패 상세:")
            for item in failed_items[:5]:  # 처음 5개만 로그
                logger.warning(f"    - {item.scenario}/{item.year}: {item.error_message}")
            if failed_count > 5:
                logger.warning(f"    ... 외 {failed_count - 5}개 실패")

        # Response 반환
        return SiteRiskResponse(
            site_id=request.site_id,
            latitude=request.latitude,
            longitude=request.longitude,
            total_calculations=total_calculations,
            successful_calculations=successful_count,
            failed_calculations=failed_count,
            results=results,
            calculated_at=calculation_end_time
        )

    except Exception as e:
        logger.error(f"사업장 리스크 계산 중 내부 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/recommend-locations", response_model=SiteRelocationResponse)
async def recommend_relocation_locations(request: SiteRelocationRequest):
    """
    사업장 이전 후보지 추천 API
    (On-Demand 계산 + DB 저장)
    """
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
    max_candidates = search_criteria.get('max_candidates', 3)

    try:
        # 2. 중복 체크: 이미 평가된 위치 필터링
        from ..database.connection import DatabaseConnection

        new_candidates = []
        skipped_count = 0

        for grid in candidate_grids:
            lat, lon = grid['latitude'], grid['longitude']

            if DatabaseConnection.check_candidate_exists(lat, lon, scenario, target_year):
                logger.info(f"이미 존재하는 후보지 건너뜀: ({lat}, {lon})")
                skipped_count += 1
            else:
                new_candidates.append(grid)

        logger.info(f"신규 평가 대상: {len(new_candidates)}개, 건너뜀: {skipped_count}개")

        # 3. 신규 후보지만 평가
        if not new_candidates:
            logger.info("모든 후보지가 이미 평가됨. 계산 건너뜀.")
            return SiteRelocationResponse(
                candidates=[],
                total_grids_evaluated=0,
                total_saved_to_db=0,
                search_criteria=search_criteria,
                calculated_at=datetime.now()
            )

        # building_info, asset_info 변환
        building_info = request.building_info.model_dump() if request.building_info else None
        asset_info = request.asset_info.model_dump() if request.asset_info else None

        logger.info(f"  max_candidates: {max_candidates}")
        logger.info(f"  scenario: {scenario}, target_year: {target_year}")

        # 4. 리스크 계산
        result = recommend_locations_ondemand(
            candidate_grids=new_candidates,
            building_info=building_info,
            asset_info=asset_info,
            scenario=scenario,
            target_year=target_year,
            max_candidates=len(new_candidates)  # 모두 평가
        )

        if result.get('status') == 'error':
            error_msg = result.get('error', '후보지 추천 중 알 수 없는 오류 발생')
            logger.error(f"이전 후보지 추천 실패: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        recommendation_result = result.get('recommendation_result', {})
        evaluated_candidates = recommendation_result.get('candidates', [])

        # 5. DB 저장 (전체 평가된 후보지)
        saved_count = save_all_candidates_to_db(
            candidates=evaluated_candidates,
            scenario=scenario,
            target_year=target_year,
            reference_site_id=request.site_id
        )

        # 6. 응답 생성 (상위 N개만 반환)
        top_candidates = sorted(
            evaluated_candidates,
            key=lambda x: x.get('average_aal', float('inf'))
        )[:max_candidates]

        logger.info(f"후보지 추천 완료: {len(evaluated_candidates)}개 평가, {saved_count}개 저장")

        if top_candidates:
            top1_aal = top_candidates[0].get('average_aal', 0.0)
            logger.info(f"  Top 1 AAL: {top1_aal:.6f}")

        # Response 모델에 맞게 결과 매핑
        return SiteRelocationResponse(
            candidates=top_candidates,
            total_grids_evaluated=len(evaluated_candidates),
            total_saved_to_db=saved_count,
            search_criteria=search_criteria,
            calculated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"이전 후보지 추천 중 내부 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


def save_all_candidates_to_db(
    candidates: List[Dict[str, Any]],
    scenario: str,
    target_year: int,
    reference_site_id: str = None
) -> int:
    """
    모든 평가된 후보지를 DB에 저장

    Args:
        candidates: RelocationRecommender에서 반환된 후보지 리스트
        scenario: SSP 시나리오
        target_year: 목표 연도
        reference_site_id: 참조 사업장 ID

    Returns:
        저장된 후보지 개수
    """
    from ..database.connection import DatabaseConnection

    saved_count = 0

    for candidate in candidates:
        try:
            lat = candidate['latitude']
            lon = candidate['longitude']
            risk_details = candidate['risk_details']

            # 1. E, V, AAL 데이터 추출 (9개 리스크 타입)
            exposure_records = []
            vulnerability_records = []
            aal_records = []
            aal_by_risk = {}

            for risk_type, risk_data in risk_details.items():
                exposure_records.append({
                    'latitude': lat,
                    'longitude': lon,
                    'risk_type': risk_type,
                    'target_year': target_year,
                    'exposure_score': risk_data['e_score']
                })

                vulnerability_records.append({
                    'latitude': lat,
                    'longitude': lon,
                    'risk_type': risk_type,
                    'target_year': target_year,
                    'vulnerability_score': risk_data['v_score']
                })

                aal_records.append({
                    'latitude': lat,
                    'longitude': lon,
                    'risk_type': risk_type,
                    'target_year': target_year,
                    'scenario': scenario,
                    'final_aal': risk_data['final_aal']
                })

                # aal_by_risk JSONB용
                aal_by_risk[risk_type] = risk_data['final_aal']

            # 2. DB 저장
            DatabaseConnection.save_exposure_results(exposure_records)
            DatabaseConnection.save_vulnerability_results(vulnerability_records)
            DatabaseConnection.save_aal_scaled_results(aal_records)

            # 3. candidate_sites 요약 저장
            average_aal = candidate['average_aal']
            average_integrated_risk = candidate['average_integrated_risk']
            risk_score = int(round(average_integrated_risk))  # 0-100 정수

            DatabaseConnection.save_candidate_site(
                latitude=lat,
                longitude=lon,
                aal=average_aal,
                aal_by_risk=aal_by_risk,
                risk_score=risk_score,
                risks=None,  # 또는 risk_details 전체를 저장
                reference_site_id=reference_site_id
            )

            saved_count += 1
            logger.info(f"후보지 저장 완료: ({lat}, {lon})")

        except Exception as e:
            logger.error(f"후보지 저장 실패 ({candidate.get('latitude')}, {candidate.get('longitude')}): {e}")
            continue  # 부분 성공 허용

    return saved_count
