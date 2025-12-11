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
from ...agents.site_assessment import (
    SiteRiskCalculator,
    RelocationRecommender
)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/site-assessment", tags=["site-assessment"])


@router.post("/calculate", response_model=SiteRiskResponse)
async def calculate_site_risk(request: SiteRiskRequest):
    """
    사업장 리스크 계산 API

    Request:
        {
            "latitude": 37.5665,
            "longitude": 126.9780,
            "site_id": "SITE-2025-001",  (optional)
            "building_info": {
                "building_type": "office",
                "structure": "철근콘크리트",
                "building_age": 15,
                "total_area_m2": 2500,
                "ground_floors": 5,
                "basement_floors": 1,
                "has_piloti": false,
                "elevation_m": 10
            },
            "asset_info": {  (optional)
                "total_value": 50000000000,
                "insurance_coverage_rate": 0.3
            }
        }

    Response:
        {
            "site_id": "SITE-2025-001",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "hazard": {risk_type: {...}, ...},
            "exposure": {risk_type: {...}, ...},
            "vulnerability": {risk_type: {...}, ...},
            "integrated_risk": {risk_type: {...}, ...},
            "aal_scaled": {risk_type: {...}, ...},
            "summary": {...},
            "calculated_at": "2025-12-11T..."
        }

    Process:
        1. H, base_aal은 DB 조회 (스케줄러가 미리 계산)
        2. E, V는 building_info 기반 계산
        3. 통합 리스크 Score = H × E × V / 10000
        4. 최종 AAL = base_aal × F_vuln × (1 - insurance_rate)
        5. DB 저장 및 반환
    """
    logger.info(f"사업장 리스크 계산 요청: ({request.latitude}, {request.longitude})")
    if request.site_id:
        logger.info(f"  site_id: {request.site_id}")

    try:
        # SiteRiskCalculator 초기화
        calculator = SiteRiskCalculator(
            scenario='SSP245',  # 기본 시나리오
            target_year=2040    # 기본 연도 (2021-2040 baseline period)
        )

        # building_info를 dict로 변환
        building_info = request.building_info.model_dump()

        # asset_info를 dict로 변환 (있으면)
        asset_info = request.asset_info.model_dump() if request.asset_info else None

        # 리스크 계산
        result = calculator.calculate_site_risks(
            latitude=request.latitude,
            longitude=request.longitude,
            building_info=building_info,
            asset_info=asset_info,
            site_id=request.site_id
        )

        logger.info(f"사업장 리스크 계산 완료: total_aal={result['summary']['total_final_aal']:.6f}")

        # Response 반환
        return SiteRiskResponse(
            site_id=result['site_id'],
            latitude=result['latitude'],
            longitude=result['longitude'],
            hazard=result['hazard'],
            exposure=result['exposure'],
            vulnerability=result['vulnerability'],
            integrated_risk=result['integrated_risk'],
            aal_scaled=result['aal_scaled'],
            summary=result['summary'],
            calculated_at=result['calculated_at']
        )

    except ValueError as e:
        # DB에 H, base_aal 없는 경우
        logger.error(f"사업장 리스크 계산 실패: {e}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"사업장 리스크 계산 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/recommend-locations", response_model=SiteRelocationResponse)
async def recommend_relocation_locations(request: SiteRelocationRequest):
    """
    사업장 이전 후보지 추천 API

    Request:
        {
            "candidate_grids": [
                {"latitude": 37.5665, "longitude": 126.9780},
                {"latitude": 37.5666, "longitude": 126.9781},
                ...  (~1000개)
            ],
            "building_info": {
                "building_type": "office",
                "structure": "철근콘크리트",
                "building_age": 15,
                "total_area_m2": 2500,
                "ground_floors": 5,
                "basement_floors": 1,
                "has_piloti": false,
                "elevation_m": 10
            },
            "asset_info": {  (optional)
                "total_value": 50000000000,
                "insurance_coverage_rate": 0.3
            },
            "search_criteria": {  (optional)
                "max_candidates": 3,
                "ssp_scenario": "ssp2",
                "target_year": 2040
            }
        }

    Response:
        {
            "candidates": [
                {
                    "rank": 1,
                    "latitude": 37.5665,
                    "longitude": 126.9780,
                    "total_aal": 0.123456,
                    "average_integrated_risk": 45.67,
                    "risk_details": {
                        "extreme_heat": {
                            "h_score": 75.0,
                            "e_score": 60.0,
                            "v_score": 55.0,
                            "integrated_risk_score": 24.75,
                            "base_aal": 0.025,
                            "f_vuln": 1.01,
                            "final_aal": 0.025
                        },
                        ...
                    }
                },
                ...
            ],
            "total_grids_evaluated": 1000,
            "search_criteria": {...},
            "calculated_at": "2025-12-11T..."
        }

    Process:
        1. ~1000개 candidate_grids 순회
        2. 각 격자마다 사업장 리스크 계산
        3. total_aal 기준 오름차순 정렬
        4. top 3 (또는 max_candidates) 선택
        5. 각 후보지의 리스크 상세 정보 반환
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
        # RelocationRecommender 초기화
        search_criteria = request.search_criteria or {}
        scenario = search_criteria.get('ssp_scenario', 'ssp2')
        target_year = search_criteria.get('target_year', 2040)
        max_candidates = search_criteria.get('max_candidates', 3)

        recommender = RelocationRecommender(
            scenario=scenario.upper().replace('SSP', 'SSP2') if 'ssp' in scenario.lower() else 'SSP245',
            target_year=target_year
        )

        # building_info를 dict로 변환
        building_info = request.building_info.model_dump()

        # asset_info를 dict로 변환 (있으면)
        asset_info = request.asset_info.model_dump() if request.asset_info else None

        # candidate_grids를 dict 리스트로 변환
        candidate_grids = [
            {'latitude': grid.latitude, 'longitude': grid.longitude}
            for grid in request.candidate_grids
        ]

        logger.info(f"  max_candidates: {max_candidates}")
        logger.info(f"  scenario: {scenario}, target_year: {target_year}")

        # 후보지 추천
        result = recommender.recommend_locations(
            candidate_grids=candidate_grids,
            building_info=building_info,
            asset_info=asset_info,
            max_candidates=max_candidates
        )

        logger.info(f"이전 후보지 추천 완료: {result['total_grids_evaluated']}/{total_grids}개 평가")
        if result['candidates']:
            top1_aal = result['candidates'][0]['total_aal']
            logger.info(f"  Top 1 AAL: {top1_aal:.6f}")

        # Response 반환
        return SiteRelocationResponse(
            candidates=result['candidates'],
            total_grids_evaluated=result['total_grids_evaluated'],
            search_criteria=result['search_criteria'],
            calculated_at=result['calculated_at']
        )

    except Exception as e:
        logger.error(f"이전 후보지 추천 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
