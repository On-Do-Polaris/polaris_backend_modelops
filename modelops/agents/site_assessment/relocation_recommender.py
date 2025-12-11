"""
사업장 이전 후보지 추천기
~1000개 후보 격자를 평가하여 최적 후보지 추천
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

from .site_risk_calculator import SiteRiskCalculator

logger = logging.getLogger(__name__)


class RelocationRecommender:
    """
    사업장 이전 후보지 추천기

    역할:
    - ~1000개 후보 격자를 순회하면서 각 위치의 AAL 계산
    - SiteRiskCalculator를 사용하여 E, V, AAL 계산
    - total_aal 기준으로 정렬하여 top 3 추천
    - 각 리스크별 상세 정보 포함
    """

    def __init__(self, scenario='SSP245', target_year=2030):
        """
        RelocationRecommender 초기화

        Args:
            scenario: SSP 시나리오
            target_year: 목표 연도
        """
        self.scenario = scenario
        self.target_year = target_year

        # SiteRiskCalculator 초기화
        self.risk_calculator = SiteRiskCalculator(
            scenario=scenario,
            target_year=target_year
        )

    def recommend_locations(
        self,
        candidate_grids: List[Dict[str, float]],
        building_info: Dict[str, Any],
        asset_info: Optional[Dict[str, Any]] = None,
        max_candidates: int = 3
    ) -> Dict[str, Any]:
        """
        후보 격자들을 평가하여 최적 후보지 추천

        Process:
        1. candidate_grids 순회 (~1000개)
        2. 각 격자마다 SiteRiskCalculator로 리스크 계산
        3. total_aal 기준으로 정렬
        4. top N개 선택
        5. 각 후보지의 리스크 상세 정보 구성

        Args:
            candidate_grids: 후보 격자 리스트 [{'latitude': ..., 'longitude': ...}, ...]
            building_info: 건물 정보 dict
            asset_info: 자산 정보 dict (선택)
            max_candidates: 최대 추천 후보지 개수 (기본 3)

        Returns:
            {
                'candidates': [
                    {
                        'rank': 1,
                        'latitude': float,
                        'longitude': float,
                        'total_aal': float,
                        'average_integrated_risk': float,
                        'risk_details': {risk_type: {...}, ...}
                    },
                    ...
                ],
                'total_grids_evaluated': int,
                'search_criteria': {...},
                'calculated_at': datetime
            }
        """
        start_time = datetime.now()
        total_grids = len(candidate_grids)
        logger.info(f"이전 후보지 추천 시작: {total_grids}개 격자 평가")
        logger.info(f"  max_candidates: {max_candidates}")

        try:
            # Step 1: 모든 후보 격자 평가
            evaluated_grids = []

            for idx, grid in enumerate(candidate_grids, 1):
                latitude = grid['latitude']
                longitude = grid['longitude']

                if idx % 100 == 0:
                    logger.info(f"  진행률: {idx}/{total_grids} ({idx/total_grids*100:.1f}%)")

                try:
                    # SiteRiskCalculator로 리스크 계산
                    risk_result = self.risk_calculator.calculate_site_risks(
                        latitude=latitude,
                        longitude=longitude,
                        building_info=building_info,
                        asset_info=asset_info,
                        site_id=None  # 후보지는 site_id 없음
                    )

                    # AAL 합계 계산
                    total_aal = risk_result['summary']['total_final_aal']
                    avg_integrated_risk = risk_result['summary']['average_integrated_risk']

                    # 평가 결과 저장
                    evaluated_grids.append({
                        'latitude': latitude,
                        'longitude': longitude,
                        'total_aal': total_aal,
                        'average_integrated_risk': avg_integrated_risk,
                        'risk_result': risk_result
                    })

                except Exception as e:
                    logger.error(f"격자 ({latitude}, {longitude}) 평가 실패: {e}")
                    # 실패한 격자는 건너뜀
                    continue

            # Step 2: total_aal 기준 오름차순 정렬 (낮을수록 좋음)
            evaluated_grids.sort(key=lambda x: x['total_aal'])

            # Step 3: top N개 선택
            top_candidates = evaluated_grids[:max_candidates]

            # Step 4: 결과 구성
            candidates = []
            for rank, candidate in enumerate(top_candidates, 1):
                risk_result = candidate['risk_result']

                # 리스크별 상세 정보 구성
                risk_details = {}
                for risk_type in self.risk_calculator.RISK_TYPES:
                    h_data = risk_result['hazard'].get(risk_type, {})
                    e_data = risk_result['exposure'].get(risk_type, {})
                    v_data = risk_result['vulnerability'].get(risk_type, {})
                    ir_data = risk_result['integrated_risk'].get(risk_type, {})
                    aal_data = risk_result['aal_scaled'].get(risk_type, {})

                    risk_details[risk_type] = {
                        'h_score': h_data.get('hazard_score_100', 0.0),
                        'e_score': e_data.get('exposure_score', 0.0),
                        'v_score': v_data.get('vulnerability_score', 0.0),
                        'integrated_risk_score': ir_data.get('integrated_risk_score', 0.0),
                        'base_aal': aal_data.get('base_aal', 0.0),
                        'f_vuln': aal_data.get('vulnerability_scale', 1.0),
                        'final_aal': aal_data.get('final_aal', 0.0)
                    }

                candidates.append({
                    'rank': rank,
                    'latitude': candidate['latitude'],
                    'longitude': candidate['longitude'],
                    'total_aal': round(candidate['total_aal'], 6),
                    'average_integrated_risk': round(candidate['average_integrated_risk'], 2),
                    'risk_details': risk_details
                })

            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            logger.info(f"이전 후보지 추천 완료: {elapsed_time:.2f}초")
            logger.info(f"  평가 성공: {len(evaluated_grids)}/{total_grids}개")

            return {
                'candidates': candidates,
                'total_grids_evaluated': len(evaluated_grids),
                'search_criteria': {
                    'max_candidates': max_candidates,
                    'ssp_scenario': self.scenario,
                    'target_year': self.target_year
                },
                'calculated_at': end_time
            }

        except Exception as e:
            logger.error(f"이전 후보지 추천 실패: {e}", exc_info=True)
            raise

    def compare_two_locations(
        self,
        location_a: Tuple[float, float],
        location_b: Tuple[float, float],
        building_info: Dict[str, Any],
        asset_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        두 위치를 직접 비교

        Args:
            location_a: (latitude, longitude) 튜플
            location_b: (latitude, longitude) 튜플
            building_info: 건물 정보 dict
            asset_info: 자산 정보 dict (선택)

        Returns:
            {
                'location_a': {...},
                'location_b': {...},
                'comparison': {
                    'better_location': 'A' or 'B',
                    'aal_difference': float,
                    'aal_reduction_percent': float
                }
            }
        """
        logger.info(f"두 위치 비교: A{location_a} vs B{location_b}")

        try:
            # Location A 계산
            result_a = self.risk_calculator.calculate_site_risks(
                latitude=location_a[0],
                longitude=location_a[1],
                building_info=building_info,
                asset_info=asset_info,
                site_id='location_a'
            )

            # Location B 계산
            result_b = self.risk_calculator.calculate_site_risks(
                latitude=location_b[0],
                longitude=location_b[1],
                building_info=building_info,
                asset_info=asset_info,
                site_id='location_b'
            )

            # AAL 비교
            aal_a = result_a['summary']['total_final_aal']
            aal_b = result_b['summary']['total_final_aal']
            aal_diff = abs(aal_a - aal_b)

            if aal_a < aal_b:
                better_location = 'A'
                reduction_percent = ((aal_b - aal_a) / aal_b * 100) if aal_b > 0 else 0
            else:
                better_location = 'B'
                reduction_percent = ((aal_a - aal_b) / aal_a * 100) if aal_a > 0 else 0

            return {
                'location_a': {
                    'latitude': location_a[0],
                    'longitude': location_a[1],
                    'total_aal': round(aal_a, 6),
                    'average_integrated_risk': result_a['summary']['average_integrated_risk'],
                    'highest_risk': result_a['summary']['highest_integrated_risk']
                },
                'location_b': {
                    'latitude': location_b[0],
                    'longitude': location_b[1],
                    'total_aal': round(aal_b, 6),
                    'average_integrated_risk': result_b['summary']['average_integrated_risk'],
                    'highest_risk': result_b['summary']['highest_integrated_risk']
                },
                'comparison': {
                    'better_location': better_location,
                    'aal_difference': round(aal_diff, 6),
                    'aal_reduction_percent': round(reduction_percent, 2)
                }
            }

        except Exception as e:
            logger.error(f"두 위치 비교 실패: {e}", exc_info=True)
            raise
