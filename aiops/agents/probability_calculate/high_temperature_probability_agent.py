'''
파일명: high_temperature_probability_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: 극심한 고온 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: X_heat(t) = WSDI(t) (Warm Spell Duration Index)
		* bin: [0~3), [3~8), [8~20), [20~)
		* DR_intensity: [0.001, 0.003, 0.010, 0.020]
		* 취약성 스케일링 제거
'''
from typing import Dict, Any
import numpy as np
from .base_probability_agent import BaseProbabilityAgent


class HighTemperatureProbabilityAgent(BaseProbabilityAgent):
	"""
	극심한 고온 리스크 확률 P(H) 계산 Agent

	사용 데이터: KMA 연간 극값 지수 WSDI (Warm Spell Duration Index)
	강도지표: X_heat(t) = WSDI(t)
	의미: 평년 기준 상위 분위수 이상 고온이 연속적으로 지속된 기간의 연간 합
	"""

	def __init__(self):
		"""
		HighTemperatureProbabilityAgent 초기화

		bin 구간:
			- bin1: 0 <= WSDI < 3 (낮음)
			- bin2: 3 <= WSDI < 8 (중간)
			- bin3: 8 <= WSDI < 20 (높음)
			- bin4: WSDI >= 20 (매우 높음)

		기본 손상률 (DR_intensity):
			- bin1: 0.1%
			- bin2: 0.3%
			- bin3: 1.0%
			- bin4: 2.0%
		"""
		bins = [
			(0, 3),
			(3, 8),
			(8, 20),
			(20, float('inf'))
		]

		dr_intensity = [
			0.001,  # 0.1%
			0.003,  # 0.3%
			0.010,  # 1.0%
			0.020   # 2.0%
		]

		super().__init__(
			risk_type='극심한 고온',
			bins=bins,
			dr_intensity=dr_intensity
		)

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		극심한 고온 강도지표 X_heat(t) 계산
		X_heat(t) = WSDI(t)

		Args:
			collected_data: 수집된 기후 데이터
				- wsdi: 연도별 WSDI 값 리스트 또는 배열

		Returns:
			연도별 WSDI 값 배열
		"""
		climate_data = collected_data.get('climate_data', {})
		wsdi_data = climate_data.get('wsdi', [])

		if not wsdi_data:
			self.logger.warning("WSDI 데이터가 없습니다. 기본값 0으로 설정합니다.")
			wsdi_data = [0]

		# numpy 배열로 변환
		wsdi_array = np.array(wsdi_data, dtype=float)

		self.logger.info(f"WSDI 데이터: {len(wsdi_array)}개 연도, 범위: {wsdi_array.min():.2f} ~ {wsdi_array.max():.2f}")

		return wsdi_array
