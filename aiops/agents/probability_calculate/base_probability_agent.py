'''
파일명: base_probability_agent.py
최종 수정일: 2025-11-22
버전: v1.1
파일 개요: 위험 발생확률 P(H) 계산 Base Agent
변경 이력:
	- 2025-11-22: v1.1 - 연별/월별 데이터 모두 처리 가능하도록 개선
		* time_unit 파라미터 추가 ('yearly' | 'monthly')
		* 월별 데이터의 경우 P_r[i] = (해당 bin 월 수) / (전체 월 수)
		* calculation_details에 time_unit 정보 추가
	- 2025-11-21: v1 - P(H) 계산만 수행하도록 AAL 로직에서 분리
		* bin별 발생확률 P[i] 계산
		* bin별 기본 손상률 DR_intensity[i] 계산
		* 취약성 스케일링 제거 (F_vuln 관련 로직 삭제)
		* 최종 손상률 및 AAL 계산 제거
'''
from typing import Dict, Any, List, Tuple
from abc import ABC, abstractmethod
import logging
import numpy as np


logger = logging.getLogger(__name__)


class BaseProbabilityAgent(ABC):
	"""
	위험 발생확률 P(H) 계산 Base Agent

	공통 프레임워크:
	- 강도지표 X_r(t) 계산
	- bin 분류
	- bin별 발생확률 P_r[i] = (해당 bin 샘플 수) / (전체 샘플 수)
	  * yearly: 연도 기반 (폭염, 한파, 홍수 등)
	  * monthly: 월 기반 (가뭄, 산불 등)
	- bin별 기본 손상률 DR_intensity_r[i] (취약성 스케일링 적용 전)
	"""

	def __init__(
		self,
		risk_type: str,
		bins: List[Tuple[float, float]],
		dr_intensity: List[float],
		time_unit: str = 'yearly'
	):
		"""
		BaseProbabilityAgent 초기화

		Args:
			risk_type: 리스크 타입 (예: heat, cold, fire, drought, etc.)
			bins: 강도 구간 리스트 [(min1, max1), (min2, max2), ...]
			dr_intensity: bin별 기본 손상률 리스트 [DR1, DR2, DR3, ...]
			time_unit: 시간 단위 ('yearly' | 'monthly')
		"""
		self.risk_type = risk_type
		self.bins = bins
		self.dr_intensity = dr_intensity
		self.time_unit = time_unit
		self.logger = logger
		self.logger.info(f"{risk_type} 확률 계산 Agent 초기화 (v1.1, {time_unit})")

	def calculate_probability(
		self,
		collected_data: Dict[str, Any]
	) -> Dict[str, Any]:
		"""
		위험 발생확률 P(H) 계산

		Args:
			collected_data: 수집된 기후 데이터 (시계열 데이터 포함)

		Returns:
			확률 계산 결과 딕셔너리
				- bin_probabilities: bin별 발생확률 P_r[i]
				- bin_base_damage_rates: bin별 기본 손상률 DR_intensity_r[i]
				- calculation_details: 계산 상세 내역
				- status: 분석 상태
		"""
		self.logger.info(f"{self.risk_type} 확률 계산 시작 (v1)")

		try:
			# 1. 강도지표 X_r(t) 계산 (추상 메서드)
			intensity_values = self.calculate_intensity_indicator(collected_data)

			# 2. bin 분류 및 발생확률 P_r[i] 계산
			bin_probabilities = self._calculate_bin_probabilities(intensity_values)

			result = {
				'risk_type': self.risk_type,
				'bin_probabilities': [round(p, 4) for p in bin_probabilities],
				'bin_base_damage_rates': [round(dr, 4) for dr in self.dr_intensity],
				'calculation_details': self._get_calculation_details(
					bin_probabilities,
					intensity_values
				),
				'status': 'completed'
			}

			self.logger.info(
				f"{self.risk_type} 확률 계산 완료: "
				f"P_r[i]={bin_probabilities}"
			)

			return result

		except Exception as e:
			self.logger.error(f"{self.risk_type} 확률 계산 중 오류: {str(e)}", exc_info=True)
			return {
				'risk_type': self.risk_type,
				'status': 'failed',
				'error': str(e)
			}

	@abstractmethod
	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		강도지표 X_r(t) 계산
		각 연도별 리스크 강도 값 산출

		Args:
			collected_data: 수집된 기후 데이터 (시계열)

		Returns:
			연도별 강도지표 배열 (numpy array)
		"""
		pass

	def _classify_into_bins(self, intensity_values: np.ndarray) -> np.ndarray:
		"""
		강도지표를 bin으로 분류

		Args:
			intensity_values: 연도별 강도지표 배열

		Returns:
			각 연도의 bin 인덱스 배열 (0-based)
		"""
		bin_indices = np.zeros(len(intensity_values), dtype=int)

		for idx, value in enumerate(intensity_values):
			for i, (bin_min, bin_max) in enumerate(self.bins):
				if bin_min <= value < bin_max:
					bin_indices[idx] = i
					break
			else:
				# 마지막 bin (upper bound 없음)
				bin_indices[idx] = len(self.bins) - 1

		return bin_indices

	def _calculate_bin_probabilities(self, intensity_values: np.ndarray) -> List[float]:
		"""
		bin별 발생확률 P_r[i] 계산
		P_r[i] = (해당 bin에 속한 샘플 수) / (전체 샘플 수)
		- yearly: 연도 기반
		- monthly: 월 기반

		Args:
			intensity_values: 강도지표 배열 (연별 또는 월별)

		Returns:
			bin별 발생확률 리스트
		"""
		bin_indices = self._classify_into_bins(intensity_values)
		total_samples = len(intensity_values)

		probabilities = []
		for i in range(len(self.bins)):
			count = np.sum(bin_indices == i)
			prob = count / total_samples if total_samples > 0 else 0.0
			probabilities.append(prob)

		return probabilities

	def _get_calculation_details(
		self,
		bin_probabilities: List[float],
		intensity_values: np.ndarray
	) -> Dict[str, Any]:
		"""
		계산 상세 내역 생성

		Args:
			bin_probabilities: bin별 발생확률
			intensity_values: 강도지표 배열 (연별 또는 월별)

		Returns:
			계산 상세 내역 딕셔너리
		"""
		bin_details = []
		for i in range(len(self.bins)):
			bin_details.append({
				'bin': i + 1,
				'range': f"{self.bins[i][0]} ~ {self.bins[i][1]}",
				'probability': round(bin_probabilities[i], 4),
				'base_damage_rate': round(self.dr_intensity[i], 4)
			})

		total_samples = len(intensity_values)

		if self.time_unit == 'monthly':
			return {
				'formula': 'P_r[i] = (해당 bin 월 수) / (전체 월 수)',
				'time_unit': 'monthly',
				'total_months': total_samples,
				'total_years': total_samples // 12,
				'bins': bin_details
			}
		else:
			return {
				'formula': 'P_r[i] = (해당 bin 연도 수) / (전체 연도 수)',
				'time_unit': 'yearly',
				'total_years': total_samples,
				'bins': bin_details
			}
