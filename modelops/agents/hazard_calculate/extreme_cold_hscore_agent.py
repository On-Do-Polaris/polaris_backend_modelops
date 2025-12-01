'''
파일명: extreme_cold_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 극심한 한파(Extreme Cold) 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (한파일수, 강도, 지속기간)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class ExtremeColdHScoreAgent(BaseHazardHScoreAgent):
	"""
	극심한 한파(Extreme Cold) 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = 0.4 × (한파일수 비율) + 0.4 × (강도 비율) + 0.2 × (최장 지속기간)
	- 근거: IPCC AR6 WG2 Chapter 16 (빈도와 강도를 동등 가중)

	데이터 출처:
	- annual_min_temp_celsius: 연최저기온 (°C)
	- coldwave_days_per_year: 한파일수 (일/년)
	- ice_days: 결빙일수 (일/년)
	- cold_wave_duration: 최장 한파 지속기간 (일)
	"""

	def __init__(self):
		super().__init__(risk_type='extreme_cold')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		한파 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- annual_min_temp_celsius: 연최저기온
					- coldwave_days_per_year: 한파일수
					- ice_days: 결빙일수
					- cold_wave_duration: 최장 지속기간
					- coldwave_intensity: 한파 강도 등급
					- baseline_coldwave_days: 기준 한파일수 (선택)
					- baseline_magnitude: 기준 강도 (선택)

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		coldwave_days = climate_data.get('coldwave_days_per_year', 0)
		cold_wave_duration = climate_data.get('cold_wave_duration', 0)
		annual_min_temp = climate_data.get('annual_min_temp_celsius', 0.0)

		# 기준값 (baseline)
		baseline_cwd = climate_data.get('baseline_coldwave_days', 10)
		baseline_magnitude = climate_data.get('baseline_magnitude', 100.0)

		# 1. 한파일수 비율 계산
		# 근거: Cohen et al. (2021) - 한파 빈도 감소 예상이지만 강도는 증가 가능
		if baseline_cwd > 0:
			cwd_ratio = coldwave_days / baseline_cwd
		else:
			cwd_ratio = coldwave_days / 10.0  # 기준값 10일

		# 2. 강도 비율 계산 (기온 기반 추정)
		# 근거: Kalkstein & Valimont (1986) - Cold Stress Index
		# 기준: -12°C를 임계값으로 가정
		threshold_temp = -12.0
		if annual_min_temp < threshold_temp:
			magnitude_estimate = abs(annual_min_temp - threshold_temp) * coldwave_days
		else:
			magnitude_estimate = 0

		if baseline_magnitude > 0:
			mag_ratio = magnitude_estimate / baseline_magnitude
		else:
			mag_ratio = magnitude_estimate / 100.0

		# 3. 지속 기간 정규화 (14일 기준)
		# 근거: Kalkstein (1991) - 7-14일 이상 한파 시 사망률 급증
		duration_norm = min(cold_wave_duration / 14.0, 1.0)

		# 4. H 통합 (한파는 빈도 감소해도 강도 증가 가능)
		cwd_norm = min(cwd_ratio, 1.0)
		mag_norm = min(mag_ratio, 1.0)

		# 5. 최종 Hazard 점수
		# 가중치: 한파일수(40%), 강도(40%), 지속기간(20%)
		H_raw = 0.4 * cwd_norm + 0.4 * mag_norm + 0.2 * duration_norm
		H_norm = min(H_raw, 1.0)

		return round(H_norm, 4)
