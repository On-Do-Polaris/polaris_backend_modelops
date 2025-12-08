'''
파일명: sea_level_rise_hscore_agent.py
설명: 해수면 상승(Sea Level Rise) 리스크 Hazard 점수(H) 산출 Agent
업데이트: HazardCalculator 로직 통합 (CMIP6 SSP 시나리오 기반)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class SeaLevelRiseHScoreAgent(BaseHazardHScoreAgent):
    """
    해수면 상승(Sea Level Rise) 리스크 Hazard 점수(H) 산출 Agent

    계산 방법론:
    - KMA CMIP6 SSP 시나리오 기반 해수면 상승량(cm) 예측값 사용
    - 내륙 지역(해안 10km 이상)은 0점 처리
    - Hazard Score 변환:
        - SLR ≥ 100cm: 1.0 (Extreme)
        - SLR ≥ 50cm: 0.7 (High)
        - SLR ≥ 30cm: 0.4 (Medium)
        - SLR < 30cm: 선형 비례
    """

    def __init__(self):
        super().__init__(risk_type='sea_level_rise')

    def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
        """
        해수면 상승 Hazard 점수 계산

        Args:
            collected_data: 수집된 데이터 딕셔너리
                - climate_data: slr_increase_cm 포함
                - building_data: distance_to_coast_m 포함 (BuildingDataFetcher 결과)

        Returns:
            Hazard 점수 (0.0 ~ 1.0)
        """
        climate_data = collected_data.get('climate_data', {})
        building_data = collected_data.get('building_data', {})

        try:
            # 1. 해안 노출도 판단
            # BuildingDataFetcher가 distance_to_coast_m를 제공한다고 가정
            # 값이 없으면 보수적으로 해안으로 가정하지 않고 0 반환 (내륙일 확률이 높으므로)
            distance_to_coast = building_data.get('distance_to_coast_m', 50000)
            
            # 내륙 지역 (해안선 10km 이상)
            if distance_to_coast >= 10000:
                if 'calculation_details' not in collected_data:
                    collected_data['calculation_details'] = {}
                collected_data['calculation_details']['sea_level_rise'] = {
                    'hazard_score': 0.0,
                    'note': 'Inland area (>10km from coast)'
                }
                return 0.0

            # 2. 해수면 상승량 데이터 추출
            slr_cm = climate_data.get('slr_increase_cm', 0.0)
            
            # 3. Hazard Score 변환
            if slr_cm >= 100:
                hazard_score = 1.0
            elif slr_cm >= 50:
                # 50~100cm 사이: 0.7 ~ 1.0 선형 보간
                hazard_score = 0.7 + (slr_cm - 50) / 50 * 0.3
            elif slr_cm >= 30:
                # 30~50cm 사이: 0.4 ~ 0.7 선형 보간
                hazard_score = 0.4 + (slr_cm - 30) / 20 * 0.3
            else:
                # 0~30cm 사이: 0.0 ~ 0.4 선형 보간
                hazard_score = (slr_cm / 30.0) * 0.4

            hazard_score = min(max(hazard_score, 0.0), 1.0)

            # 상세 결과 기록
            if 'calculation_details' not in collected_data:
                collected_data['calculation_details'] = {}
            
            collected_data['calculation_details']['sea_level_rise'] = {
                'hazard_score': hazard_score,
                'slr_cm': slr_cm,
                'distance_to_coast_m': distance_to_coast
            }

            return round(hazard_score, 4)

        except Exception as e:
            self.logger.error(f"Sea Level Rise 계산 중 오류 발생: {e}")
            return 0.0  # 기본적으로 안전하다고 가정