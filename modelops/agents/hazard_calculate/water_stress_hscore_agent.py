'''
파일명: water_stress_hscore_agent.py
설명: 물 부족(Water Stress) 리스크 Hazard 점수(H) 산출 Agent
업데이트: HazardCalculator 로직 통합 (WAMIS 용수이용량 + 기후 강수량 기반)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class WaterStressHScoreAgent(BaseHazardHScoreAgent):
    """
    물 부족(Water Stress) 리스크 Hazard 점수(H) 산출 Agent

    계산 방법론:
    - 물부족지수(Water Stress Index) = 용수수요량 / 용수공급량
    - 용수수요량: WAMIS 권역별 생활/공업/농업 용수 이용량 합계
    - 용수공급량: 연강수량 × 유역면적 × 유출계수
    
    Hazard Score 변환:
    - Index < 1.0 (No Stress) → 0.2
    - 1.0 ≤ Index < 1.5 (Mild) → 0.4
    - 1.5 ≤ Index < 2.0 (Moderate) → 0.7
    - Index ≥ 2.0 (Severe) → 1.0
    """

    def __init__(self):
        super().__init__(risk_type='water_stress')

    def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
        """
        물 부족 Hazard 점수 계산

        Args:
            collected_data: 수집된 데이터 딕셔너리
                - wamis_data: watershed_info, water_usage 포함
                - climate_data: annual_rainfall_mm 포함

        Returns:
            Hazard 점수 (0.0 ~ 1.0)
        """
        wamis_data = collected_data.get('wamis_data', {})
        climate_data = collected_data.get('climate_data', {})

        try:
            # 1. 데이터 추출
            watershed_info = wamis_data.get('watershed_info', {})
            water_usage = wamis_data.get('water_usage', {})
            
            watershed_area_km2 = watershed_info.get('watershed_area_km2', 15000)
            runoff_coef = watershed_info.get('runoff_coef', 0.6)
            
            # 2. 용수 수요량 계산 (m³/day)
            # 1년 = 365일, 1천 m³ = 1000 m³
            # water_usage 단위가 '천 m³/년'이라고 가정 (WAMIS Fetcher 로직)
            total_usage_k_m3_yr = water_usage.get('total', 500000) # 기본값: 5억톤/년
            water_demand_m3_per_day = (total_usage_k_m3_yr * 1000) / 365.0

            # 3. 용수 공급량 계산 (m³/day)
            annual_rainfall_mm = climate_data.get('annual_rainfall_mm', 1200.0)
            
            # 물수급량 = 강수량(mm) × 유역면적(km²) × 유출계수 × 1000 (단위 변환)
            # 1mm * 1km² = 1000 m³
            rainfall_runoff_m3_annually = (
                annual_rainfall_mm *
                watershed_area_km2 *
                runoff_coef * 1000
            )
            water_supply_m3_per_day = rainfall_runoff_m3_annually / 365.0

            # 4. 물부족지수 계산
            if water_supply_m3_per_day > 0:
                stress_index = water_demand_m3_per_day / water_supply_m3_per_day
            else:
                stress_index = 10.0 # 공급 불가능 (극심한 부족)

            # 5. Hazard Score 변환
            if stress_index < 1.0:
                hazard_score = 0.2 # No stress
                stress_level = 'low'
            elif stress_index < 1.5:
                hazard_score = 0.4 # Mild
                stress_level = 'mild'
            elif stress_index < 2.0:
                hazard_score = 0.7 # Moderate
                stress_level = 'medium'
            else:
                hazard_score = 1.0 # Severe
                stress_level = 'high'

            # 상세 결과 기록
            if 'calculation_details' not in collected_data:
                collected_data['calculation_details'] = {}
            
            collected_data['calculation_details']['water_stress'] = {
                'hazard_score': hazard_score,
                'stress_index': stress_index,
                'stress_level': stress_level,
                'water_demand_m3_day': water_demand_m3_per_day,
                'water_supply_m3_day': water_supply_m3_per_day
            }

            return round(hazard_score, 4)

        except Exception as e:
            self.logger.error(f"Water Stress 계산 중 오류 발생: {e}")
            return 0.5