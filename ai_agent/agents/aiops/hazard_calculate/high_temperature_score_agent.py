'''
파일명: high_temperature_score_agent.py
최종 수정일: 2025-11-13
버전: v02
파일 개요: 극심한 고온 리스크 물리적 종합 점수 산출 Agent
변경 이력:
	- 2025-11-11: v01 - AAL×자산가치 방식으로 변경 (H×E×V 제거)
	- 2025-11-13: v02 - H×E×V 방식으로 복원
'''
from typing import Dict, Any
from .base_physical_risk_score_agent import BasePhysicalRiskScoreAgent


class HighTemperatureScoreAgent(BasePhysicalRiskScoreAgent):
	"""
	극심한 고온 리스크 물리적 종합 점수 산출 Agent
	H (Hazard) × E (Exposure) × V (Vulnerability) 기반 리스크 점수 계산
	"""

	def __init__(self):
		"""
		HighTemperatureScoreAgent 초기화
		"""
		super().__init__(risk_type='극심한 고온')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		극심한 고온 Hazard 점수 계산
		기후 데이터 기반 폭염 위험도 평가

		Args:
			collected_data: 수집된 기후 데이터

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 폭염 일수 (연간)
		heatwave_days = climate_data.get('heatwave_days', 5)

		# 최고 기온
		max_temperature = climate_data.get('max_temperature', 30)

		# Hazard 점수 계산
		# 폭염 일수 기반 (0-30일 → 0.0-0.5)
		days_score = min(heatwave_days / 60, 0.5)

		# 최고 기온 기반 (30-40도 → 0.0-0.5)
		temp_score = min(max((max_temperature - 30) / 20, 0), 0.5)

		hazard_score = days_score + temp_score

		return round(min(hazard_score, 1.0), 4)

	def calculate_exposure(self, asset_info: Dict[str, Any]) -> float:
		"""
		극심한 고온 Exposure 점수 계산
		자산 가치 및 노출 정도 평가

		Args:
			asset_info: 사업장 자산 정보

		Returns:
			Exposure 점수 (0.0 ~ 1.0)
		"""
		total_asset_value = asset_info.get('total_asset_value', 0)

		# 자산 가치 기반 노출도 (10억원 단위)
		# 10억원 = 0.1, 100억원 = 1.0
		exposure_score = min(total_asset_value / 100_000_000_000, 1.0)

		# 최소 노출도 0.1 보장
		exposure_score = max(exposure_score, 0.1)

		return round(exposure_score, 4)

	def calculate_vulnerability(
		self,
		vulnerability_analysis: Dict[str, Any],
		asset_info: Dict[str, Any]
	) -> float:
		"""
		극심한 고온 Vulnerability 점수 계산
		건물 및 시설 취약성 평가

		Args:
			vulnerability_analysis: 취약성 분석 결과
			asset_info: 사업장 자산 정보

		Returns:
			Vulnerability 점수 (0.0 ~ 1.0)
		"""
		# 건물 연식
		building_age = vulnerability_analysis.get('building_age', 10)

		# 냉방 시스템 유무 (가정)
		has_cooling_system = asset_info.get('has_cooling_system', True)

		# 건물 연식 기반 취약성 (0-50년 → 0.2-0.7)
		age_vulnerability = 0.2 + min(building_age / 100, 0.5)

		# 냉방 시스템 보정
		if has_cooling_system:
			age_vulnerability *= 0.7  # 30% 감소

		return round(min(age_vulnerability, 1.0), 4)
