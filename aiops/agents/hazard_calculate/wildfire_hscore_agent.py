'''
파일명: wildfire_hscore_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: 산불 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class WildfireHScoreAgent(BaseHazardHScoreAgent):
	"""
	산불 리스크 Hazard 점수(H) 산출 Agent
	"""

	def __init__(self):
		super().__init__(risk_type='산불')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		climate_data = collected_data.get('climate_data', {})
		risk_days = climate_data.get('wildfire_risk', 5)
		hazard_score = min(risk_days / 30, 1.0)
		return round(hazard_score, 4)
