'''
파일명: drought_probability_agent.py
최종 수정일: 2025-11-22
버전: v1.1
파일 개요: 가뭄 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-22: v1.1 - flat list 데이터 형식 지원 추가
		* spei12 (flat list) 또는 spei12_monthly (nested dict) 모두 처리
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: X_drought(t,m) = SPEI12(t,m) (월별)
		* bin: (>-1), [-1~-1.5), [-1.5~-2.0), (≤-2.0)
		* DR_intensity: [0.00, 0.02, 0.07, 0.20]
		* 월 기반 발생확률: P_drought[i] = (해당 bin에 속한 월 수) / (총 월 수)
		* 취약성 스케일링 제거
'''
from typing import Dict, Any
import numpy as np
from .base_probability_agent import BaseProbabilityAgent


class DroughtProbabilityAgent(BaseProbabilityAgent):
	"""
	가뭄 리스크 확률 P(H) 계산 Agent

	사용 데이터: KMA SPEI12 (Standardized Precipitation-Evapotranspiration Index 12개월)
	강도지표: X_drought(t,m) = SPEI12(t,m) (월별)
	월 기반 발생확률: P_drought[i] = (해당 bin에 속한 월 수) / (총 월 수)
	"""

	def __init__(self):
		"""
		DroughtProbabilityAgent 초기화

		bin 구간:
			- bin1: SPEI12 > -1 (정상~약한 가뭄)
			- bin2: -1 >= SPEI12 > -1.5 (중간 가뭄)
			- bin3: -1.5 >= SPEI12 > -2.0 (심각 가뭄)
			- bin4: SPEI12 <= -2.0 (극심 가뭄)

		기본 손상률 (DR_intensity):
			- bin1: 0%
			- bin2: 2%
			- bin3: 7%
			- bin4: 20%

		참고:
			- 월 기반 발생확률 사용
			- P_drought[i] = (해당 bin에 속한 월 수) / (총 월 수)
		"""
		bins = [
			(-1, float('inf')),   # SPEI12 > -1
			(-1.5, -1),           # -1.5 < SPEI12 <= -1
			(-2.0, -1.5),         # -2.0 < SPEI12 <= -1.5
			(float('-inf'), -2.0) # SPEI12 <= -2.0
		]

		dr_intensity = [
			0.00,   # 0%
			0.02,   # 2%
			0.07,   # 7%
			0.20    # 20%
		]

		super().__init__(
			risk_type='가뭄',
			bins=bins,
			dr_intensity=dr_intensity,
			time_unit='monthly'
		)

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		가뭄 강도지표 X_drought(t,m) 계산
		X_drought(t,m) = SPEI12(t,m) (월별)

		Args:
			collected_data: 수집된 기후 데이터
				- spei12: 월별 SPEI12 flat list [v1, v2, ...] (권장)
				- spei12_monthly: 연도별 월별 SPEI12 데이터 리스트 (레거시)
					각 원소는 {'year': int, 'months': [spei12_values]}

		Returns:
			월별 SPEI12 값 배열 (전체 월을 평탄화하여 반환)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 1. flat list 형식 (우선)
		spei12_flat = climate_data.get('spei12', [])
		if spei12_flat:
			spei12_array = np.array(spei12_flat, dtype=float)
			self.logger.info(f"SPEI12 데이터 (flat): {len(spei12_array)}개 월, 범위: {spei12_array.min():.2f} ~ {spei12_array.max():.2f}")
			return spei12_array

		# 2. nested dict 형식 (레거시)
		spei12_monthly = climate_data.get('spei12_monthly', [])
		if spei12_monthly:
			all_monthly_spei12 = []
			for year_data in spei12_monthly:
				monthly_values = year_data.get('months', [])
				if monthly_values:
					all_monthly_spei12.extend(monthly_values)

			if all_monthly_spei12:
				spei12_array = np.array(all_monthly_spei12, dtype=float)
				self.logger.info(f"SPEI12 데이터 (nested): {len(spei12_array)}개 월, 범위: {spei12_array.min():.2f} ~ {spei12_array.max():.2f}")
				return spei12_array

		self.logger.warning("SPEI12 데이터가 없습니다. 기본값 0으로 설정합니다.")
		return np.array([0.0])

	def _classify_into_bins(self, intensity_values: np.ndarray) -> np.ndarray:
		"""
		SPEI12 값을 bin으로 분류 (가뭄 전용 - 음수 값 처리)

		Args:
			intensity_values: 연도별 SPEI12 값 배열

		Returns:
			각 연도의 bin 인덱스 배열 (0-based)
		"""
		bin_indices = np.zeros(len(intensity_values), dtype=int)

		for idx, value in enumerate(intensity_values):
			if value > -1:
				bin_indices[idx] = 0  # bin1: SPEI12 > -1
			elif value > -1.5:
				bin_indices[idx] = 1  # bin2: -1.5 < SPEI12 <= -1
			elif value > -2.0:
				bin_indices[idx] = 2  # bin3: -2.0 < SPEI12 <= -1.5
			else:
				bin_indices[idx] = 3  # bin4: SPEI12 <= -2.0

		return bin_indices
