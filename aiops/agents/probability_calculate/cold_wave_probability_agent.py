'''
파일명: cold_wave_probability_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: 극심한 한파 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: X_cold(t) = CSDI(t) (Cold Spell Duration Index)
		* bin: [0~3), [3~7), [7~15), [15~)
		* DR_intensity: [0.0005, 0.0020, 0.0060, 0.0150]
		* 취약성 스케일링 제거
'''
from typing import Dict, Any
import numpy as np
from .base_probability_agent import BaseProbabilityAgent


class ColdWaveProbabilityAgent(BaseProbabilityAgent):
	"""
	극심한 한파 리스크 확률 P(H) 계산 Agent

	사용 데이터: KMA 연간 극값 지수 CSDI (Cold Spell Duration Index)
	강도지표: X_cold(t) = CSDI(t)
	의미: 평년 기준 하위 분위수 이하 저온이 연속적으로 지속된 기간의 연간 합
	"""

	def __init__(self):
		"""
		ColdWaveProbabilityAgent 초기화

		bin 구간:
			- bin1: 0 <= CSDI < 3 (낮음)
			- bin2: 3 <= CSDI < 7 (중간)
			- bin3: 7 <= CSDI < 15 (높음)
			- bin4: CSDI >= 15 (매우 높음)

		기본 손상률 (DR_intensity):
			- bin1: 0.05%
			- bin2: 0.20%
			- bin3: 0.60%
			- bin4: 1.50%
		"""
		bins = [
			(0, 3),
			(3, 7),
			(7, 15),
			(15, float('inf'))
		]

		dr_intensity = [
			0.0005,  # 0.05%
			0.0020,  # 0.20%
			0.0060,  # 0.60%
			0.0150   # 1.50%
		]

		super().__init__(
			risk_type='극심한 한파',
			bins=bins,
			dr_intensity=dr_intensity
		)

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		극심한 한파 강도지표 X_cold(t) 계산
		X_cold(t) = CSDI(t)

		Args:
			collected_data: 수집된 기후 데이터
				- csdi: 연도별 CSDI 값 리스트 또는 배열

		Returns:
			연도별 CSDI 값 배열
		"""
		climate_data = collected_data.get('climate_data', {})
		csdi_data = climate_data.get('csdi', [])

		if not csdi_data:
			self.logger.warning("CSDI 데이터가 없습니다. 기본값 0으로 설정합니다.")
			csdi_data = [0]

		# numpy 배열로 변환
		csdi_array = np.array(csdi_data, dtype=float)

		self.logger.info(f"CSDI 데이터: {len(csdi_array)}개 연도, 범위: {csdi_array.min():.2f} ~ {csdi_array.max():.2f}")

		return csdi_array
