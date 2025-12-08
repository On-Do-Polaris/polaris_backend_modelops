'''
파일명: extreme_cold_hscore_agent.py
설명: 극한 한파(Extreme Cold) 리스크 Hazard 점수(H) 산출 Agent
업데이트: HazardCalculator 로직 통합 (CCI 지표 기반)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class ExtremeColdHScoreAgent(BaseHazardHScoreAgent):
    """
    극한 한파(Extreme Cold) 리스크 Hazard 점수(H) 산출 Agent

    계산 방법론:
    - CCI (Cold Compound Index) 기반 평가
    - 근거: IPCC AR6 + TCFD 공식 지표 (ETCCDI)
    - 공식: CCI = 0.3×(TX10p/30) + 0.3×(CSIx/20) + 0.2×(FD/50) + 0.2×(절대최저/20)
    """

    def __init__(self):
        super().__init__(risk_type='extreme_cold')

    def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
        """
        한파 Hazard 점수 계산

        Args:
            collected_data: 수집된 데이터 딕셔너리
                - climate_data: ClimateDataLoader를 통해 수집된 기후 데이터

        Returns:
            Hazard 점수 (0.0 ~ 1.0)
        """
        climate_data = collected_data.get('climate_data', {})

        # 데이터가 없는 경우 Fallback (전국 평균 수준)
        if not climate_data:
            self.logger.warning("Extreme Cold: 기후 데이터가 없습니다. 기본값(0.35)을 사용합니다.")
            return 0.35

        try:
            # Step 1: ETCCDI 지표 추출
            # tx10p: 한파일수 (≤절대최저 10백분위수)
            tx10p = climate_data.get('coldwave_days_per_year', 10)
            # csix: 한파 지속일수
            csix = climate_data.get('cold_wave_duration', 8)
            # fd: 서리일 또는 결빙일 (Ice Days)
            fd = climate_data.get('ice_days', 5)
            # tn_abs: 절대최저기온 (절대값 사용)
            tn_val = climate_data.get('annual_min_temp_celsius', -15.0)
            tn_abs = abs(tn_val)

            # Step 2: 절대값 기준 정규화 (0~1)
            # 기준값 설정 근거: 한반도 기후 특성 고려
            tx10p_norm = min(tx10p / 30.0, 1.0)  # 연간 30일 이상이면 만점
            csix_norm = min(csix / 20.0, 1.0)    # 지속 20일 이상이면 만점
            fd_norm = min(fd / 50.0, 1.0)        # 결빙 50일 이상이면 만점
            tn_norm = min(tn_abs / 20.0, 1.0)    # -20도 이하면 만점

            # Step 3: CCI 계산 (가중평균)
            # 한파일수(30%) + 지속일수(30%) + 결빙일(20%) + 최저기온(20%)
            cci = 0.3 * tx10p_norm + 0.3 * csix_norm + 0.2 * fd_norm + 0.2 * tn_norm

            # 상세 결과 기록
            if 'calculation_details' not in collected_data:
                collected_data['calculation_details'] = {}
            
            collected_data['calculation_details']['extreme_cold'] = {
                'cci': cci,
                'factors': {
                    'tx10p_norm': tx10p_norm,
                    'csix_norm': csix_norm,
                    'fd_norm': fd_norm,
                    'tn_norm': tn_norm
                }
            }

            return round(cci, 4)

        except Exception as e:
            self.logger.error(f"Extreme Cold 계산 중 오류 발생: {e}")
            return 0.35