'''
파일명: water_stress_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 물부족(Water Stress) 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (Water Stress 지표)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class WaterStressHScoreAgent(BaseHazardHScoreAgent):
	"""
	물부족(Water Stress) 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = (총 취수량 / 재생가능 수자원량) × 100
	- 근거: UN SDG 6.4.2(2016), MSCI ESG(2023), World Bank(2015)

	Water Stress 기준:
	- 0~25%: Low stress
	- 25~50%: Medium stress
	- 50~75%: High stress
	- 75~100%: Very high stress
	- 100%+: Critical stress (물 부족)

	재생가능 수자원량:
	- 강수량(mm) × 유역면적(km²) × 유출계수(0.65) × 0.001
	- 근거: WRI Aqueduct(2019), GRACE 연구(2016)

	데이터 출처:
	- withdrawal_total: 총 취수량 (백만 m³/년)
	- precipitation_mm: 연강수량 (mm)
	- basin_area_km2: 유역 면적 (km²)
	- runoff_coef: 유출계수 (기본값 0.65)
	"""

	def __init__(self):
		super().__init__(risk_type='water_stress')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		물부족 Hazard 점수 계산

		Args:
			collected_data: 수자원 데이터
				- climate_data:
					- withdrawal_total: 총 취수량 (백만 m³/년)
					- precipitation_mm: 연강수량 (mm)
					- basin_area_km2: 유역 면적 (km²)
					- runoff_coef: 유출계수 (기본값 0.65)

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		withdrawal_total = climate_data.get('withdrawal_total', 1000.0)  # 백만 m³
		precipitation_mm = climate_data.get('precipitation_mm', 1200.0)  # mm
		basin_area_km2 = climate_data.get('basin_area_km2', 26219.0)    # km² (한강 예시)
		runoff_coef = climate_data.get('runoff_coef', 0.65)             # 무차원

		# 재생가능 수자원량 계산
		# 근거: WRI Aqueduct(2019) - 강수량 × 유역면적 × 유출계수
		water_resource = precipitation_mm * basin_area_km2 * runoff_coef * 0.001  # 백만 m³

		# Water Stress 계산
		# 근거: UN SDG 6.4.2 - 공식 물 스트레스 지표
		if water_resource > 0:
			water_stress = (withdrawal_total / water_resource) * 100
		else:
			water_stress = 100.0  # 자원 없음 → 극심한 스트레스

		# Hazard 정규화 (0~100% → 0.0~1.0)
		# 100% 이상 시 1.0 (Critical stress)
		hazard_score = min(water_stress / 100.0, 1.0)

		return round(hazard_score, 4)
