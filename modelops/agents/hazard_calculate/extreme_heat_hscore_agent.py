'''
파일명: extreme_heat_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 극심한 고온(Extreme Heat) 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (폭염일수, 강도, 지속기간)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class ExtremeHeatHScoreAgent(BaseHazardHScoreAgent):
	"""
	극심한 고온(Extreme Heat) 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = 0.4 × (폭염일수 증가율) + 0.4 × (강도 증가율) + 0.2 × (최장 지속기간)
	- 근거: IPCC AR6 WG2 Chapter 16 (빈도와 강도를 동등 가중)

	데이터 출처:
	- annual_max_temp_celsius: 연최고기온 (°C)
	- heatwave_days_per_year: 폭염일수 (일/년)
	- tropical_nights: 열대야일수 (일/년)
	- heat_wave_duration: 최장 폭염 지속기간 (일)
	"""

	def __init__(self):
		super().__init__(risk_type='extreme_heat')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		폭염 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- annual_max_temp_celsius: 연최고기온
					- heatwave_days_per_year: 폭염일수
					- tropical_nights: 열대야일수
					- heat_wave_duration: 최장 지속기간
					- heatwave_intensity: 폭염 강도 등급
					- baseline_heatwave_days: 기준 폭염일수 (선택)
					- baseline_magnitude: 기준 강도 (선택)

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		heatwave_days = climate_data.get('heatwave_days_per_year', 0)
		heat_wave_duration = climate_data.get('heat_wave_duration', 0)
		annual_max_temp = climate_data.get('annual_max_temp_celsius', 30.0)

		# 기준값 (baseline)
		baseline_hwd = climate_data.get('baseline_heatwave_days', 10)
		baseline_magnitude = climate_data.get('baseline_magnitude', 100.0)

		# 1. 폭염일수 증가율 계산
		if baseline_hwd > 0:
			hwd_ratio = heatwave_days / baseline_hwd
		else:
			hwd_ratio = heatwave_days / 10.0  # 기준값 10일

		# 2. 강도 증가율 계산 (기온 기반 추정)
		# 근거: Russo et al. (2015) - 강도 = 임계값 초과 온도 누적
		# 기준: 33°C를 임계값으로 가정
		threshold_temp = 33.0
		if annual_max_temp > threshold_temp:
			magnitude_estimate = (annual_max_temp - threshold_temp) * heatwave_days
		else:
			magnitude_estimate = 0

		if baseline_magnitude > 0:
			mag_ratio = magnitude_estimate / baseline_magnitude
		else:
			mag_ratio = magnitude_estimate / 100.0

		# 3. 지속 기간 정규화 (30일 기준)
		# 근거: Mora et al. (2017) Nature Climate Change
		# "30일 이상 지속 시 생태계 임계점 도달"
		duration_norm = min(heat_wave_duration / 30.0, 1.0)

		# 4. H 통합 (증가율은 3배까지 정규화)
		# 근거: Wang et al. (2021) - 2°C 온난화 시 폭염 빈도 3배 증가
		hwd_norm = min(hwd_ratio / 3.0, 1.0)
		mag_norm = min(mag_ratio / 3.0, 1.0)

		# 5. 최종 Hazard 점수
		# 가중치: 폭염일수(40%), 강도(40%), 지속기간(20%)
		H_raw = 0.4 * hwd_norm + 0.4 * mag_norm + 0.2 * duration_norm
		H_norm = min(H_raw, 1.0)

		return round(H_norm, 4)
