'''
파일명: urban_flood_probability_agent.py
최종 수정일: 2025-11-22
버전: v3
파일 개요: 도시 집중 홍수 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-22: v3 - 순수 RAIN80 기반 (취약성 분리)
		* 강도지표: X_pflood = RAIN80 (호우일수)
		* bin: 호우일수 기준 [0~1), [1~3), [3~5), [≥5)
		* DR_intensity: [0.00, 0.05, 0.15, 0.35]
		* vulnerability_factor 제거 (취약성 에이전트에서 별도 처리)
	- 2025-11-22: v2 - RAIN80 + vulnerability_factor 방식 (deprecated)
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
'''
from typing import Dict, Any
import numpy as np
from .base_probability_agent import BaseProbabilityAgent


class UrbanFloodProbabilityAgent(BaseProbabilityAgent):
	"""
	도시 집중 홍수 리스크 확률 P(H) 계산 Agent

	사용 데이터: KMA RAIN80 (연간 80mm 이상 호우일수)
	강도지표: X_pflood(t) = RAIN80(t)
	취약성은 별도 취약성 에이전트에서 처리
	"""

	def __init__(self):
		"""
		UrbanFloodProbabilityAgent 초기화

		bin 구간 (호우일수):
			- bin1: < 1일 (호우 거의 없음)
			- bin2: 1 ~ 3일 (낮은 빈도)
			- bin3: 3 ~ 5일 (중간 빈도)
			- bin4: >= 5일 (높은 빈도)

		기본 손상률 (DR_intensity):
			- bin1: 0%
			- bin2: 5%
			- bin3: 15%
			- bin4: 35%
		"""
		bins = [
			(0, 1),          # bin1: 호우 거의 없음
			(1, 3),          # bin2: 낮은 빈도
			(3, 5),          # bin3: 중간 빈도
			(5, float('inf'))  # bin4: 높은 빈도
		]

		dr_intensity = [
			0.00,   # 0%
			0.05,   # 5%
			0.15,   # 15%
			0.35    # 35%
		]

		super().__init__(
			risk_type='도시 홍수',
			bins=bins,
			dr_intensity=dr_intensity
		)

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		도시 집중 홍수 강도지표 X_pflood(t) 계산

		X_pflood = RAIN80
		- RAIN80: 연간 80mm 이상 호우일수 (일)
		- 취약성은 별도 취약성 에이전트에서 처리

		Args:
			collected_data: 수집된 기후 데이터
				- climate_data.rain80: 연도별 RAIN80 값 리스트 (호우일수)

		Returns:
			연도별 호우일수 배열
		"""
		climate_data = collected_data.get('climate_data', {})
		rain80_data = climate_data.get('rain80', [])

		if not rain80_data:
			self.logger.warning("RAIN80 데이터가 없습니다. 기본값 0으로 설정합니다.")
			return np.array([0.0])

		rain80_array = np.array(rain80_data, dtype=float)

		self.logger.info(
			f"도시홍수 강도지표: {len(rain80_array)}개 연도, "
			f"RAIN80 범위: {rain80_array.min():.1f} ~ {rain80_array.max():.1f}일"
		)

		return rain80_array
