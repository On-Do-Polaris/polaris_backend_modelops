'''
파일명: urban_flood_score_agent.py
최종 수정일: 2025-11-13
버전: v02
파일 개요: 도심 홍수 리스크 물리적 종합 점수 산출 Agent
변경 이력:
	- 2025-11-11: v01 - AAL×자산가치 방식으로 변경 (H×E×V 제거)
	- 2025-11-13: v02 - H×E×V 방식으로 복원
'''
from typing import Dict, Any
from .base_physical_risk_score_agent import BasePhysicalRiskScoreAgent


class UrbanFloodScoreAgent(BasePhysicalRiskScoreAgent):
	"""
	도심 홍수 리스크 물리적 종합 점수 산출 Agent
	H (Hazard) × E (Exposure) × V (Vulnerability) 기반 리스크 점수 계산
	"""

	def __init__(self):
		"""
		UrbanFloodScoreAgent 초기화
		"""
		super().__init__(risk_type='도시 홍수')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		도심 홍수 Hazard 점수 계산
		기후 데이터 기반 도심홍수위험 위험도 평가

		Args:
			collected_data: 수집된 기후 데이터

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 도심홍수위험 관련 데이터
		risk_days = climate_data.get('urban_flood_risk', 5)

		# Hazard 점수 계산 (임시 구현)
		hazard_score = min(risk_days / 30, 1.0)

		return round(hazard_score, 4)

	def calculate_exposure(self, asset_info: Dict[str, Any]) -> float:
		"""
		도심 홍수 Exposure 점수 계산
		자산 가치 및 노출 정도 평가

		Args:
			asset_info: 사업장 자산 정보

		Returns:
			Exposure 점수 (0.0 ~ 1.0)
		"""
		total_asset_value = asset_info.get('total_asset_value', 0)

		# 자산 가치 기반 노출도 (10억원 단위)
		exposure_score = min(total_asset_value / 100_000_000_000, 1.0)
		exposure_score = max(exposure_score, 0.1)

		return round(exposure_score, 4)

	def calculate_vulnerability(
		self,
		vulnerability_analysis: Dict[str, Any],
		asset_info: Dict[str, Any]
	) -> float:
		"""
		도심 홍수 Vulnerability 점수 계산
		건물 및 시설 취약성 평가

		Args:
			vulnerability_analysis: 취약성 분석 결과
			asset_info: 사업장 자산 정보

		Returns:
			Vulnerability 점수 (0.0 ~ 1.0)
		"""
		# 건물 연식
		building_age = vulnerability_analysis.get('building_age', 10)

		# 건물 연식 기반 취약성
		age_vulnerability = 0.2 + min(building_age / 100, 0.5)

		return round(min(age_vulnerability, 1.0), 4)
