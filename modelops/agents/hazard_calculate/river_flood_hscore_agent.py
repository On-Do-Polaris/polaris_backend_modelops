'''
파일명: river_flood_hscore_agent.py
설명: 하천 홍수(River Flood) 리스크 Hazard 점수(H) 산출 Agent
업데이트: HazardCalculator 로직 통합 (TWI + 강수량 기반)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class RiverFloodHScoreAgent(BaseHazardHScoreAgent):
    """
    하천 홍수(River Flood) 리스크 Hazard 점수(H) 산출 Agent

    계산 방법론:
    - TWI (Topographic Wetness Index) + 극한 강수량 결합
    - Hazard Score = 0.4 × TWI_score + 0.6 × 강수_score
    - 근거: USGS 표준 지형 지수, 수문학 표준 (Beven & Kirkby 1979)
    """

    def __init__(self):
        super().__init__(risk_type='river_flood')

    def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
        """
        하천 홍수 Hazard 점수 계산

        Args:
            collected_data: 수집된 데이터 딕셔너리
                - spatial_data: landcover_type 포함
                - climate_data: max_1day_rainfall_mm 포함

        Returns:
            Hazard 점수 (0.0 ~ 1.0)
        """
        spatial_data = collected_data.get('spatial_data', {})
        climate_data = collected_data.get('climate_data', {})

        try:
            # 1. TWI 기반 지형 취약도 계산
            landcover_type = spatial_data.get('landcover_type', 'urban')
            twi = self._calculate_twi(landcover_type)

            # TWI 정규화 (0~1 점수)
            # TWI > 10: 매우 높은 홍수위험 (0.9)
            # TWI 7-10: 높은 홍수위험 (0.6-0.9)
            # TWI 5-7: 중간 홍수위험 (0.3-0.6)
            # TWI < 5: 낮은 홍수위험 (0-0.3)
            if twi > 10:
                twi_score = 0.9
            elif twi > 7:
                twi_score = 0.5 + (twi - 7) / 6  # 0.5 ~ 0.9
            else:
                twi_score = twi / 20  # 0 ~ 0.35

            # 2. 강수량 기반 홍수 빈도 점수
            extreme_rainfall = climate_data.get('max_1day_rainfall_mm', 250.0)
            
            # 강수량 정규화 (0~1 점수)
            # > 300mm: 0.9 (극한 강수)
            # 200-300mm: 0.6-0.9
            # 100-200mm: 0.3-0.6
            # < 100mm: 0-0.3
            if extreme_rainfall > 300:
                rainfall_score = 0.9
            elif extreme_rainfall > 200:
                rainfall_score = 0.5 + (extreme_rainfall - 200) / 200
            else:
                rainfall_score = extreme_rainfall / 300

            # 3. 결합 점수 (TWI 40% + 강수 60%)
            hazard_score = (twi_score * 0.4) + (rainfall_score * 0.6)
            
            # 상세 결과 기록
            if 'calculation_details' not in collected_data:
                collected_data['calculation_details'] = {}
            
            collected_data['calculation_details']['river_flood'] = {
                'hazard_score': hazard_score,
                'twi': twi,
                'twi_score': twi_score,
                'extreme_rainfall': extreme_rainfall,
                'rainfall_score': rainfall_score
            }

            return round(min(hazard_score, 1.0), 4)

        except Exception as e:
            self.logger.error(f"River Flood 계산 중 오류 발생: {e}")
            return 0.5

    def _calculate_twi(self, landcover_type: str) -> float:
        """
        TWI (Topographic Wetness Index) 추정
        원래는 DEM의 경사도와 상위 유역면적으로 계산해야 하나,
        여기서는 토지피복도 기반의 경험적 추정치를 사용 (HazardCalculator 로직 준용)
        """
        # 산림/초지: 높은 토양포화도 → 높은 TWI
        # 도시: 포장도로 많음 → 낮은 TWI
        # 농지: 중간 수준
        if landcover_type == 'forest':
            return 10.5  # 산림: 높은 습도
        elif landcover_type == 'grassland':
            return 9.0   # 초지: 중간~높은 습도
        elif landcover_type == 'agricultural':
            return 7.5   # 농지: 중간 습도
        elif landcover_type == 'water':
            return 14.0  # 수역: 최고 습도
        else:
            return 6.5   # 도시/포장지: 낮은 습도