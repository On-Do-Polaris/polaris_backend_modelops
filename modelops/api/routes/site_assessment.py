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
from ...batch.evaal_ondemand_api import (
    calculate_evaal_ondemand,
    recommend_locations_ondemand
)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/site-assessment", tags=["site-assessment"])


@router.post("/calculate", response_model=SiteRiskResponse)
async def calculate_site_risk(request: SiteRiskRequest):
    """
    사업장 리스크 계산 API
    (E, V, AAL On-Demand 계산 및 DB 저장)
    """
    logger.info(f"사업장 리스크 계산 요청: ({request.latitude}, {request.longitude})")
    if request.site_id:
        logger.info(f"  site_id: {request.site_id}")

    try:
        # evaal_ondemand_api.py의 함수를 직접 호출
        # 시나리오와 연도는 API 요청 스펙에 추가하거나, 현재처럼 기본값 사용
        scenario = 'SSP245'
        target_year = 2040
        
        # asset_info 처리
        insurance_rate = request.asset_info.insurance_coverage_rate if request.asset_info else 0.0
        asset_value = request.asset_info.total_value if request.asset_info else None

        # calculate_evaal_ondemand 호출
        result = calculate_evaal_ondemand(
            latitude=request.latitude,
            longitude=request.longitude,
            scenario=scenario,
            target_year=target_year,
            risk_types=None,  # None이면 전체 리스크
            insurance_rate=insurance_rate,
            asset_value=asset_value,
            save_to_db=True  # DB에 결과 저장
        )

        if result.get('status') == 'error':
            error_msg = result.get('error', 'E, V, AAL 계산 중 알 수 없는 오류 발생')
            logger.error(f"사업장 리스크 계산 실패: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"사업장 리스크 계산 완료 (E, V, AAL On-Demand)")
        if result.get('summary'):
             logger.info(f"  Total AAL: {result['summary'].get('highest_aal_risk', {}).get('final_aal', 0.0):.6f}")

        # Response 모델에 맞게 결과 매핑
        return SiteRiskResponse(
            site_id=request.site_id, # 요청에서 받은 site_id 그대로 반환
            latitude=result['latitude'],
            longitude=result['longitude'],
            hazard=result['results']['hazard'],
            exposure=result['results']['exposure'],
            vulnerability=result['results']['vulnerability'],
            integrated_risk=result['results']['integrated_risk'],
            aal_scaled=result['results']['aal'],
            summary=result['summary'],
            calculated_at=result['metadata']['calculated_at']
        )

    except ValueError as e:
        logger.error(f"사업장 리스크 계산 실패 (Value Error): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"사업장 리스크 계산 중 내부 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/recommend-locations", response_model=SiteRelocationResponse)
async def recommend_relocation_locations(request: SiteRelocationRequest):
    """
    사업장 이전 후보지 추천 API
    (On-Demand 계산)
    """
    total_grids = len(request.candidate_grids)
    logger.info(f"이전 후보지 추천 요청: {total_grids}개 격자")

    # 입력 검증
    if total_grids == 0:
        raise HTTPException(
            status_code=400,
            detail="candidate_grids는 최소 1개 이상이어야 합니다."
        )
    if total_grids > 2000:
        logger.warning(f"candidate_grids가 {total_grids}개로 많습니다. 처리 시간이 오래 걸릴 수 있습니다.")

    try:
        # 검색 기준 처리
        search_criteria = request.search_criteria or {}
        scenario = search_criteria.get('ssp_scenario', 'SSP245')
        target_year = search_criteria.get('target_year', 2040)
        max_candidates = search_criteria.get('max_candidates', 3)

        # building_info를 dict로 변환
        building_info = request.building_info.model_dump() if request.building_info else None

        # asset_info를 dict로 변환 (있으면)
        asset_info = request.asset_info.model_dump() if request.asset_info else None

        # candidate_grids를 dict 리스트로 변환
        candidate_grids = [
            {'latitude': grid.latitude, 'longitude': grid.longitude}
            for grid in request.candidate_grids
        ]
        
        logger.info(f"  max_candidates: {max_candidates}")
        logger.info(f"  scenario: {scenario}, target_year: {target_year}")

        # recommend_locations_ondemand 호출
        result = recommend_locations_ondemand(
            candidate_grids=candidate_grids,
            building_info=building_info,
            asset_info=asset_info,
            scenario=scenario,
            target_year=target_year,
            max_candidates=max_candidates
        )
        
        if result.get('status') == 'error':
            error_msg = result.get('error', '후보지 추천 중 알 수 없는 오류 발생')
            logger.error(f"이전 후보지 추천 실패: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        recommendation_result = result.get('recommendation_result', {})
        logger.info(f"이전 후보지 추천 완료: {recommendation_result.get('total_grids_evaluated', 0)}/{total_grids}개 평가")
        
        if recommendation_result.get('candidates'):
            top1_aal = recommendation_result['candidates'][0].get('total_aal', 0.0)
            logger.info(f"  Top 1 AAL: {top1_aal:.6f}")

        # Response 모델에 맞게 결과 매핑
        return SiteRelocationResponse(
            candidates=recommendation_result.get('candidates', []),
            total_grids_evaluated=recommendation_result.get('total_grids_evaluated', 0),
            search_criteria=recommendation_result.get('search_criteria', {}),
            calculated_at=recommendation_result.get('calculated_at', datetime.now().isoformat())
        )

    except Exception as e:
        logger.error(f"이전 후보지 추천 중 내부 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
