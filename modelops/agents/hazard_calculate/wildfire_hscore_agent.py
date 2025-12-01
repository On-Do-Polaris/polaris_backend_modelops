'''
파일명: wildfire_hscore_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 산불 리스크 Hazard 점수(H) 산출 Agent
변경 이력:
	- 2025-11-21: v1 - H×E×V에서 H만 계산하도록 분리
	- 2025-11-24: v2 - Physical_RISK_calculate 로직 반영 (FWI, 건조일수)
'''
from typing import Dict, Any
from .base_hazard_hscore_agent import BaseHazardHScoreAgent


class WildfireHScoreAgent(BaseHazardHScoreAgent):
	"""
	산불 리스크 Hazard 점수(H) 산출 Agent

	계산 방법론:
	- H = 0.60 × (FWI 증가율) + 0.40 × (건조일수 증가율)
	- 근거: IPCC AR6(2022), 캐나다 FWI System(1987), 한국 산림청(2023)

	FWI 기준 (Fire Weather Index):
	- 캐나다 산림청 표준 산불 위험 지수
	- FWI > 30: 고위험
	- FWI > 45: 극위험
	- SSP5-8.5에서 최대 40% 증가 예상

	건조일수 기준:
	- 연속 무강수 일수 (< 1mm)
	- 7일 이상: 산불 위험 급증 (80%)
	- 14일 이상: 산불 확률 95%
	- 50% 증가 시 산불 위험 배가

	데이터 출처:
	- fwi_baseline_max: 기준 FWI 최대값
	- fwi_future_max: 미래 FWI 최대값
	- dry_days_baseline: 기준 최대 연속 건조일수
	- dry_days_future: 미래 최대 연속 건조일수
	"""

	def __init__(self):
		super().__init__(risk_type='wildfire')

	def calculate_hazard(self, collected_data: Dict[str, Any]) -> float:
		"""
		산불 Hazard 점수 계산

		Args:
			collected_data: 기후 데이터
				- climate_data:
					- fwi_baseline_max: 기준 FWI 최대값
					- fwi_future_max: 미래 FWI 최대값
					- dry_days_baseline: 기준 건조일수
					- dry_days_future: 미래 건조일수

		Returns:
			Hazard 점수 (0.0 ~ 1.0)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 데이터 추출
		fwi_baseline = climate_data.get('fwi_baseline_max', 30.0)
		fwi_future = climate_data.get('fwi_future_max', 40.0)
		dry_days_baseline = climate_data.get('dry_days_baseline', 10)
		dry_days_future = climate_data.get('dry_days_future', 14)

		# 1. FWI 증가율 점수
		# 근거: IPCC AR6 - SSP5-8.5에서 FWI 최대 40% 증가 예상
		fwi_increase_pct = ((fwi_future - fwi_baseline) / fwi_baseline) * 100

		if fwi_increase_pct >= 40:
			fwi_score = 100.0
		elif fwi_increase_pct <= 0:
			fwi_score = 0.0
		else:
			fwi_score = (fwi_increase_pct / 40.0) * 100

		# 2. 건조일수 증가율 점수
		# 근거: 한국 산림청(2023) - 건조일수 50% 증가 시 산불 위험 배가
		if dry_days_baseline > 0:
			dry_days_increase_pct = ((dry_days_future - dry_days_baseline) / dry_days_baseline) * 100
		else:
			dry_days_increase_pct = 0.0

		if dry_days_increase_pct >= 50:
			dry_days_score = 100.0
		elif dry_days_increase_pct <= 0:
			dry_days_score = 0.0
		else:
			dry_days_score = (dry_days_increase_pct / 50.0) * 100

		# 3. H 통합
		# 근거: IPCC AR6(2022) - FWI 60%, 건조일수 40%
		H_raw = (fwi_score * 0.60) + (dry_days_score * 0.40)
		H_norm = min(H_raw / 100.0, 1.0)

		return round(H_norm, 4)
