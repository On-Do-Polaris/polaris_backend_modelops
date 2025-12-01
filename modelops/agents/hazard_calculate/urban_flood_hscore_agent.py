'''
파일명: urban_flood_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 도시 홍수 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (RX1DAY, SDII, RAIN80)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class UrbanFloodHScoreAgent(BaseHazardHScoreAgent):
	"""
	도시 홍수 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = 0.50 × (RX1DAY 증가율) + 0.30 × (SDII 증가률) + 0.20 × (RAIN80 증가율)
	- 근거: Nature Cities(2025), IPCC AR6 WG1(2021), WMO 기준

	RX1DAY 기준:
	- 일 최대 강수량이 도시 배수 능력 초과의 주요 원인
	- SSP5-8.5에서 최대 30% 증가 예상

	SDII 기준 (Simple Daily Intensity Index):
	- 집중호우 강도가 배수 한계 초과 결정
	- 20% 증가 시 침수 위험 배가

	RAIN80 기준:
	- 80mm/일 이상이 도시 배수망 설계 한계
	- 빈도 50% 증가 시 도시 침수 증가

	데이터 출처:
	- rx1day_baseline_mm: 기준 RX1DAY (mm)
	- rx1day_future_mm: 미래 RX1DAY (mm)
	- sdii_baseline: 기준 SDII (mm/일)
	- sdii_future: 미래 SDII (mm/일)
	- rain80_baseline_days: 기준 RAIN80 일수
	- rain80_future_days: 미래 RAIN80 일수
	"""

	def __init__(self):
		super().__init__(risk_type='urban_flood')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		도시 홍수 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- rx1day_baseline_mm: 기준 RX1DAY
					- rx1day_future_mm: 미래 RX1DAY
					- sdii_baseline: 기준 SDII
					- sdii_future: 미래 SDII
					- rain80_baseline_days: 기준 RAIN80 일수
					- rain80_future_days: 미래 RAIN80 일수

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		rx1day_baseline = climate_data.get('rx1day_baseline_mm', 100.0)
		rx1day_future = climate_data.get('rx1day_future_mm', 120.0)
		sdii_baseline = climate_data.get('sdii_baseline', 10.0)
		sdii_future = climate_data.get('sdii_future', 11.5)
		rain80_baseline_days = climate_data.get('rain80_baseline_days', 2)
		rain80_future_days = climate_data.get('rain80_future_days', 3)

		# 1. RX1DAY 증가율 점수
		# 근거: IPCC AR6 - SSP5-8.5에서 최대 30% 증가 예상
		rx1day_increase_pct = ((rx1day_future - rx1day_baseline) / rx1day_baseline) * 100

		if rx1day_increase_pct >= 30:
			rx1day_score = 100.0
		elif rx1day_increase_pct <= 0:
			rx1day_score = 0.0
		else:
			rx1day_score = (rx1day_increase_pct / 30.0) * 100

		# 2. SDII 증가율 점수
		# 근거: WMO - SDII 20% 증가 시 침수 위험 배가
		sdii_increase_pct = ((sdii_future - sdii_baseline) / sdii_baseline) * 100

		if sdii_increase_pct >= 20:
			sdii_score = 100.0
		elif sdii_increase_pct <= 0:
			sdii_score = 0.0
		else:
			sdii_score = (sdii_increase_pct / 20.0) * 100

		# 3. RAIN80 증가율 점수
		# 근거: 한국 기상청 - RAIN80 빈도 50% 증가 시 도시 침수 증가
		if rain80_baseline_days > 0:
			rain80_increase_pct = ((rain80_future_days - rain80_baseline_days) / rain80_baseline_days) * 100
		else:
			rain80_increase_pct = 0.0

		if rain80_increase_pct >= 50:
			rain80_score = 100.0
		elif rain80_increase_pct <= 0:
			rain80_score = 0.0
		else:
			rain80_score = (rain80_increase_pct / 50.0) * 100

		# 4. H 통합
		# 근거: Nature Cities(2025) - RX1DAY 50%, SDII 30%, RAIN80 20%
		H_raw = (rx1day_score * 0.50) + (sdii_score * 0.30) + (rain80_score * 0.20)
		H_norm = min(H_raw / 100.0, 1.0)

		return round(H_norm, 4)
