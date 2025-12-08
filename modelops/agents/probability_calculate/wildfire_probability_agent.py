'''
파일명: wildfire_probability_agent.py
최종 수정일: 2025-11-24
버전: v2.0
파일 개요: 산불 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-24: v2.0 - FWI 공식 수정 (캐나다 ISI 방식 근사)
		* 습도: 제곱근으로 영향 완화 → (1 - RHM/100)^0.5
		* 풍속: m/s → km/h 변환 후 지수적 반영 → exp(0.05039 × WS_kmh)
		* 온도: 계수 강화 (0.05 → 0.08), 기준 온도 조정 (10 → 5)
		* 강수: 감쇠 완화 (0.001 → 0.0005)
		* 스케일링: ×5 적용하여 EFFIS bin과 호환
	- 2025-11-22: v1.2 - bin 0~11.2 (Low) 추가
		* bin: [0~11.2), [11.2~21.3), [21.3~38), [38~50), [50~)
		* DR_intensity: [0.00, 0.01, 0.03, 0.10, 0.25]
	- 2025-11-22: v1.1 - flat list 데이터 형식 지원 추가
		* ta, rhm, ws, rn (flat lists) 또는 monthly_data (nested dict) 모두 처리
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: X_fire(t,m) = FWI(t,m) (Fire Weather Index, 월별)
		* FWI 계산식 적용
		* 월 기반 발생확률: P_fire[i] = (해당 bin에 속한 월 수) / (총 월 수)
		* 취약성 스케일링 제거
'''
from typing import Dict, Any
import numpy as np
from .base_probability_agent import BaseProbabilityAgent


class WildfireProbabilityAgent(BaseProbabilityAgent):
	"""
	산불 리스크 확률 P(H) 계산 Agent

	사용 데이터: 월별 기상 데이터 (TA, RHM, WS, RN)
	강도지표: X_fire(t,m) = FWI(t,m) (월별)

	FWI 계산식 (캐나다 ISI 방식 근사, v2.0):
		FWI(t,m) = (1 - RHM/100)^0.5 × exp(0.05039 × WS_kmh)
		           × exp(0.08 × (TA - 5)) × exp(-0.0005 × RN) × 5

		- 습도: 제곱근으로 영향 완화
		- 풍속: m/s → km/h 변환 후 지수적 반영 (캐나다 ISI 방식)
		- 온도: 계수 강화 및 기준온도 하향
		- 강수: 감쇠 완화
		- 스케일링: ×5 (EFFIS bin 호환)

	월 기반 발생확률: P_fire[i] = (해당 bin에 속한 월 수) / (총 월 수)
	"""

	def __init__(self):
		"""
		WildfireProbabilityAgent 초기화

		bin 구간 (EFFIS FWI 기준):
			- bin1: 0 <= FWI < 11.2 (Low)
			- bin2: 11.2 <= FWI < 21.3 (Moderate)
			- bin3: 21.3 <= FWI < 38 (High)
			- bin4: 38 <= FWI < 50 (Very High)
			- bin5: FWI >= 50 (Extreme)

		기본 손상률 (DR_intensity):
			- bin1: 0%
			- bin2: 1%
			- bin3: 3%
			- bin4: 10%
			- bin5: 25%

		참고:
			- 월 기반 발생확률 사용
			- P_fire[i] = (해당 bin에 속한 월 수) / (총 월 수)
		"""
		bins = [
			(0, 11.2),
			(11.2, 21.3),
			(21.3, 38),
			(38, 50),
			(50, float('inf'))
		]

		dr_intensity = [
			0.00,   # 0% (Low)
			0.01,   # 1% (Moderate)
			0.03,   # 3% (High)
			0.10,   # 10% (Very High)
			0.25    # 25% (Extreme)
		]

		super().__init__(
			risk_type='wildfire',
			bins=bins,
			dr_intensity=dr_intensity,
			time_unit='monthly'
		)

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		산불 강도지표 X_fire(t,m) 계산
		X_fire(t,m) = FWI(t,m) (월별)

		FWI(t,m) = (1 - RHM(t,m)/100) × 0.5 × (WS(t,m) + 1)
		           × exp(0.05 × (TA(t,m) - 10)) × exp(-0.001 × RN(t,m))

		Args:
			collected_data: 수집된 기후 데이터
				- ta, rhm, ws, rn: 월별 데이터 flat lists (권장)
				- monthly_data: 연도별 월별 데이터 리스트 (레거시)
					각 원소는 {'year': int, 'months': [{'ta': float, 'rhm': float, 'ws': float, 'rn': float}, ...]}

		Returns:
			월별 FWI 값 배열 (전체 월을 평탄화하여 반환)
		"""
		climate_data = collected_data.get('climate_data', {})

		# 1. flat list 형식 (우선)
		ta_list = climate_data.get('ta', [])
		rhm_list = climate_data.get('rhm', [])
		ws_list = climate_data.get('ws', [])
		rn_list = climate_data.get('rn', [])

		if ta_list and rhm_list and ws_list and rn_list:
			n_months = min(len(ta_list), len(rhm_list), len(ws_list), len(rn_list))
			all_monthly_fwi = []

			for i in range(n_months):
				fwi = self._calculate_fwi(
					ta_list[i],
					rhm_list[i],
					ws_list[i],
					rn_list[i]
				)
				all_monthly_fwi.append(fwi)

			fwi_array = np.array(all_monthly_fwi, dtype=float)
			self.logger.info(f"FWI 데이터 (flat): {len(fwi_array)}개 월, 범위: {fwi_array.min():.2f} ~ {fwi_array.max():.2f}")
			return fwi_array

		# 2. nested dict 형식 (레거시)
		monthly_data = climate_data.get('monthly_data', [])
		if monthly_data:
			all_monthly_fwi = []
			for year_data in monthly_data:
				months = year_data.get('months', [])
				for month in months:
					ta = month.get('ta', 10.0)
					rhm = month.get('rhm', 50.0)
					ws = month.get('ws', 2.0)
					rn = month.get('rn', 0.0)
					fwi = self._calculate_fwi(ta, rhm, ws, rn)
					all_monthly_fwi.append(fwi)

			if all_monthly_fwi:
				fwi_array = np.array(all_monthly_fwi, dtype=float)
				self.logger.info(f"FWI 데이터 (nested): {len(fwi_array)}개 월, 범위: {fwi_array.min():.2f} ~ {fwi_array.max():.2f}")
				return fwi_array

		self.logger.warning("월별 기상 데이터가 없습니다. 기본값 0으로 설정합니다.")
		return np.array([0.0])

	def _calculate_fwi(self, ta: float, rhm: float, ws: float, rn: float) -> float:
		"""
		Fire Weather Index (FWI) 계산 (캐나다 ISI 방식 근사, v2.0)

		FWI = (1 - RHM/100)^0.5 × exp(0.05039 × WS_kmh)
		      × exp(0.08 × (TA - 5)) × exp(-0.0005 × RN) × 5

		Args:
			ta: 평균 기온 (°C)
			rhm: 상대습도 (%)
			ws: 평균 풍속 (m/s)
			rn: 강수량 (mm)

		Returns:
			FWI 값 (EFFIS bin 호환 스케일)
		"""
		# 습도 영향 (제곱근으로 완화)
		humidity_factor = (1 - (rhm / 100.0)) ** 0.5

		# 풍속 영향 (m/s → km/h 변환 후 지수적 반영, 캐나다 ISI 방식)
		ws_kmh = ws * 3.6
		wind_factor = np.exp(0.05039 * ws_kmh)

		# 온도 영향 (계수 강화, 기준온도 하향)
		temp_factor = np.exp(0.08 * (ta - 5))

		# 강수 영향 (감쇠 완화)
		rain_factor = np.exp(-0.0005 * rn)

		# 스케일링 적용 (EFFIS bin 호환)
		fwi = humidity_factor * wind_factor * temp_factor * rain_factor * 5

		return max(fwi, 0.0)  # 음수 방지
