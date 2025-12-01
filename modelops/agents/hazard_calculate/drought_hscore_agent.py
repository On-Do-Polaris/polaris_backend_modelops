'''
파일명: drought_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 가뭄 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (SPEI 기반 가뭄 평가)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class DroughtHScoreAgent(BaseHazardHScoreAgent):
	"""
	가뭄 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- SPEI (Standardized Precipitation Evapotranspiration Index) 기반
	- H = min(100, |SPEI| / 2.5 × 100)
	- 근거: Vicente-Serrano et al. (2010), S&P Global Physical Risk (2025)

	SPEI 기준:
	- SPEI ≤ -2.5: 극심한 가뭄 (100점)
	- SPEI ≤ -2.0: 심한 가뭄 (80점)
	- SPEI ≤ -1.5: 중간 가뭄 (60점)
	- SPEI ≤ -1.0: 약한 가뭄 (40점)
	- SPEI ≥ 0: 정상 (0점)

	데이터 출처:
	- annual_rainfall_mm: 연강수량 (mm)
	- consecutive_dry_days: 연속 무강수일수 (일)
	- soil_moisture: 토양수분 (0~1)
	- spi_index: SPI/SPEI 지수
	"""

	def __init__(self):
		super().__init__(risk_type='drought')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		가뭄 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- annual_rainfall_mm: 연강수량
					- consecutive_dry_days: 연속 무강수일수
					- rainfall_intensity: 강우 강도
					- soil_moisture: 토양수분 (0~1)
					- drought_indicator: 가뭄 지표
					- drought_frequency: 가뭄 빈도
					- drought_duration_months: 가뭄 지속기간 (월)
					- spi_index: SPI/SPEI 지수

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		consecutive_dry_days = climate_data.get('consecutive_dry_days', 0)
		spi_index = climate_data.get('spi_index', 0.0)
		soil_moisture = climate_data.get('soil_moisture', 0.3)
		drought_duration = climate_data.get('drought_duration_months', 0)

		# 1. SPEI/SPI 기반 위해성 계산
		# 근거: Vicente-Serrano et al. (2010) - SPEI가 SPI보다 정확
		if spi_index != 0:
			# SPEI 값이 있는 경우
			spei_score = min(abs(spi_index) / 2.5, 1.0)
		else:
			# SPEI 없으면 연속 무강수일수로 추정
			# 근거: 30일 이상 무강수 시 극심한 가뭄
			if consecutive_dry_days > 30:
				spei_score = 1.0  # 극심한 가뭄
			elif consecutive_dry_days > 20:
				spei_score = 0.8  # 심한 가뭄
			elif consecutive_dry_days > 15:
				spei_score = 0.6  # 보통 가뭄
			elif consecutive_dry_days > 10:
				spei_score = 0.4  # 경미한 가뭄
			else:
				spei_score = consecutive_dry_days / 30.0

		# 2. 토양수분 부족도
		# 근거: NASA SMAP (2018) - 토양수분 < 20% 시 극심한 가뭄
		if soil_moisture < 0.1:
			soil_score = 1.0
		elif soil_moisture < 0.2:
			soil_score = 0.8
		elif soil_moisture < 0.3:
			soil_score = 0.5
		else:
			soil_score = max(0, (0.3 - soil_moisture) / 0.2)

		# 3. 가뭄 지속기간
		# 근거: 3개월 이상 지속 시 심각한 가뭄
		duration_score = min(drought_duration / 6.0, 1.0)  # 6개월 기준

		# 4. H 통합
		# 가중치: SPEI(60%), 토양수분(30%), 지속기간(10%)
		H_raw = 0.6 * spei_score + 0.3 * soil_score + 0.1 * duration_score
		H_norm = min(H_raw, 1.0)

		return round(H_norm, 4)
