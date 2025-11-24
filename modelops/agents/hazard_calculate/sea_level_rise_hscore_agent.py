'''
파일명: sea_level_rise_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 해수면 상승(Sea Level Rise) 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (해수면 상승량)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class SeaLevelRiseHScoreAgent(BaseHazardHScoreAgent):
	"""
	해수면 상승(Sea Level Rise) 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = (해수면 상승량 cm / 100) × 100 정규화
	- 근거: IPCC AR6(2021), S&P Global, World Bank(2024)

	해수면 상승 기준:
	- 0cm → 0점
	- 50cm → 50점
	- 100cm 이상 → 100점

	IPCC AR6 한국 해수면 상승 전망:
	- SSP1-2.6: 2050년 0.30m, 2100년 0.53m
	- SSP2-4.5: 2050년 0.35m, 2100년 0.62m
	- SSP5-8.5: 2050년 0.48m, 2100년 0.99m

	데이터 출처:
	- slr_m: 해수면 상승량 (m)
	- slr_cm: 해수면 상승량 (cm)
	"""

	def __init__(self):
		super().__init__(risk_type='sea_level_rise')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		해수면 상승 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- slr_m: 해수면 상승량 (m)
					- slr_cm: 해수면 상승량 (cm, 선택)

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		slr_m = climate_data.get('slr_m', 0.0)
		slr_cm = climate_data.get('slr_cm', slr_m * 100)

		# Hazard 점수 계산
		# 근거: IPCC AR6 - 해수면 상승이 해안 홍수의 직접 원인
		# 100cm 기준으로 정규화
		hazard_score = min(slr_cm / 100.0, 1.0)

		return round(hazard_score, 4)
