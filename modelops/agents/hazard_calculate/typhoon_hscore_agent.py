'''
파일명: typhoon_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 태풍 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (극값 풍속 95p 증가율)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class TyphoonHScoreAgent(BaseHazardHScoreAgent):
	"""
	태풍 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = V_95p_future / V_95p_baseline (극값 백분위수 비율법)
	- 근거: IPCC AR6, WMO Guidelines, S&P Global

	극값 풍속 기준:
	- 일평균 풍속의 95th percentile 사용
	- 일평균 → 일최대 변환계수 k = 1.7
	- 근거: WMO Guidelines 표준

	Hazard 해석:
	- H = 1.00: 변화 없음
	- H = 1.10: 10% 증가 (경미한 위험)
	- H = 1.29: 29% 증가 (중간 위험)
	- H = 1.50+: 50% 이상 증가 (극심한 위험)

	데이터 출처:
	- wind_95p_baseline: 기준 95th percentile 풍속 (m/s)
	- wind_95p_future: 미래 95th percentile 풍속 (m/s)
	"""

	def __init__(self):
		super().__init__(risk_type='typhoon')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		태풍 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- wind_95p_baseline: 기준 95p 풍속 (m/s)
					- wind_95p_future: 미래 95p 풍속 (m/s)

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		wind_95p_baseline = climate_data.get('wind_95p_baseline', 12.0)
		wind_95p_future = climate_data.get('wind_95p_future', 15.5)

		# Hazard 비율 계산
		# 근거: TCFD Framework - 시나리오 간 상대적 변화 비율로 리스크 증가 정량화
		if wind_95p_baseline > 0:
			H_ratio = wind_95p_future / wind_95p_baseline
		else:
			H_ratio = 1.0

		# 정규화 (1.0 기준, 최대 2.0까지)
		# H = 1.0: 변화 없음 → 0.0
		# H = 2.0: 100% 증가 → 1.0
		hazard_score = min((H_ratio - 1.0), 1.0)

		return round(hazard_score, 4)
