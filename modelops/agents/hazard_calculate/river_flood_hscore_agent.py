'''
파일명: river_flood_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 하천 홍수(River Flood) 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (RX5DAY, 유역면적, 하천차수)
'''
from typing import Dict, Any
import numpy as np
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class RiverFloodHScoreAgent(BaseHazardHScoreAgent):
	"""
	하천 홍수(River Flood) 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = 0.50 × (RX5DAY 증가율) + 0.30 × (유역 면적) + 0.20 × (하천 차수)
	- 근거: IPCC AR6 WG2(2022), Nature Water(2024), 한국 한강연구(2012)

	RX5DAY 기준:
	- 연속 5일 최대강수량이 하천 유입량의 주요 인자
	- SSP5-8.5에서 최대 50% 증가 예상

	유역 면적 기준:
	- 소하천: < 100km²
	- 중하천: 100~1000km²
	- 대하천: > 1000km² (한강급)

	하천 차수 기준:
	- 1차(소하천) ~ 4차(본류)
	- Strahler 차수가 높을수록 유량 증가

	데이터 출처:
	- rx5day_baseline_mm: 기준 RX5DAY (mm)
	- rx5day_future_mm: 미래 RX5DAY (mm)
	- watershed_area_km2: 유역 면적 (km²)
	- stream_order: 하천 차수 (1~4)
	"""

	def __init__(self):
		super().__init__(risk_type='river_flood')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		하천 홍수 Hazard 점수 계산

		Args:
			collected_data: 기후 및 유역 데이터
				- climate_data:
					- rx5day_baseline_mm: 기준 RX5DAY (mm)
					- rx5day_future_mm: 미래 RX5DAY (mm)
					- watershed_area_km2: 유역 면적 (km²)
					- stream_order: 하천 차수 (1~4)

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		rx5day_baseline = climate_data.get('rx5day_baseline_mm', 200.0)
		rx5day_future = climate_data.get('rx5day_future_mm', 250.0)
		watershed_area = climate_data.get('watershed_area_km2', 500.0)
		stream_order = climate_data.get('stream_order', 2)

		# 1. RX5DAY 증가율 점수
		# 근거: IPCC AR6 - SSP5-8.5에서 최대 50% 증가 예상
		rx5day_increase_pct = ((rx5day_future - rx5day_baseline) / rx5day_baseline) * 100

		if rx5day_increase_pct >= 50:
			rx5day_score = 100.0
		elif rx5day_increase_pct <= 0:
			rx5day_score = 0.0
		else:
			rx5day_score = (rx5day_increase_pct / 50.0) * 100

		# 2. 유역 면적 점수
		# 근거: Nature Water(2024) - 유역 면적이 클수록 범람 시 피해 규모 증가
		# 한국 하천: 소하천 < 100km², 중하천 100~1000km², 대하천 > 1000km²
		if watershed_area >= 10000:
			area_score = 100.0  # 대하천 (한강급)
		elif watershed_area <= 100:
			area_score = 10.0   # 소하천
		else:
			# 로그 스케일 (면적 증가 시 비선형 증가)
			area_score = 10.0 + (
				(np.log10(watershed_area) - np.log10(100)) /
				(np.log10(10000) - np.log10(100))
			) * 90.0

		# 3. 하천 차수 점수
		# 근거: Nature Water(2024) - Strahler 차수가 높을수록 유량 증가
		# 한국 하천: 1차(소하천) ~ 4차(본류)
		if stream_order >= 4:
			order_score = 100.0
		elif stream_order <= 1:
			order_score = 25.0
		else:
			order_score = 25.0 + ((stream_order - 1) / 3.0) * 75.0

		# 4. H 통합
		# 근거: 한국 한강연구(2012) - RX5DAY 50%, 유역 30%, 차수 20%
		H_raw = (rx5day_score * 0.50) + (area_score * 0.30) + (order_score * 0.20)
		H_norm = min(H_raw / 100.0, 1.0)

		return round(H_norm, 4)
