'''
파일명: coastal_flood_hscore_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: 해안 홍수 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
		* Exposure, Vulnerability 계산 제거
		* 파일명: coastal_flood_score_agent → coastal_flood_hscore_agent
		* 클래스명: CoastalFloodScoreAgent → CoastalFloodHScoreAgent
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class CoastalFloodHScoreAgent(BaseHazardHScoreAgent):
	"""
	해안 홍수 리스크 Hazard 점수(H) 산출 Agent
	기후 데이터 기반 해안홍수위험 위험도 평가
	"""

	def __init__(self):
		"""
		CoastalFloodHScoreAgent 초기화
		"""
		super().__init__(risk_type='해수면 상승')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		해안 홍수 Hazard 점수 계산
		기후 데이터 기반 해안홍수위험 위험도 평가

		Args:
			collected_data: 수집된 기후 데이터

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 해안홍수위험 관련 데이터
		risk_days = climate_data.get('coastal_flood_risk', 5)

		# Hazard 점수 계산 (임시 구현)
		hazard_score = min(risk_days / 30, 1.0)

		return round(hazard_score, 4)
