'''
파일명: water_scarcity_probability_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: 물부족 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: X_wst(t) = WSI(t) = Withdrawal(t) / ARWR(t)
		* bin: [<0.2), [0.2~0.4), [0.4~0.8), [≥0.8)
		* DR_intensity: [0.01, 0.03, 0.07, 0.15]
		* 취약성 스케일링 제거
'''
from typing import Dict, Any
import numpy as np
from .base_probability_agent import BaseProbabilityAgent


class WaterScarcityProbabilityAgent(BaseProbabilityAgent):
	"""
	물부족 리스크 확률 P(H) 계산 Agent

	사용 데이터: WAMIS 용수이용량 및 재생가능수자원
	강도지표: X_wst(t) = WSI(t) = Withdrawal(t) / ARWR(t)
	- WSI: Water Stress Index
	- ARWR = TRWR × 0.63 (환경유지유량 차감)
	"""

	def __init__(self):
		"""
		WaterScarcityProbabilityAgent 초기화

		bin 구간 (WRI 기준):
			- bin1: WSI < 0.2 (낮은 물 스트레스)
			- bin2: 0.2 <= WSI < 0.4 (중간 물 스트레스)
			- bin3: 0.4 <= WSI < 0.8 (높은 물 스트레스)
			- bin4: WSI >= 0.8 (극심한 물 스트레스)

		기본 손상률 (DR_intensity):
			- bin1: 1%
			- bin2: 3%
			- bin3: 7%
			- bin4: 15%
		"""
		bins = [
			(0, 0.2),
			(0.2, 0.4),
			(0.4, 0.8),
			(0.8, float('inf'))
		]

		dr_intensity = [
			0.01,   # 1%
			0.03,   # 3%
			0.07,   # 7%
			0.15    # 15%
		]

		super().__init__(
			risk_type='물부족',
			bins=bins,
			dr_intensity=dr_intensity
		)

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		물부족 강도지표 X_wst(t) 계산
		X_wst(t) = WSI(t) = Withdrawal(t) / ARWR_future(t)

		Args:
			collected_data: 수집된 수자원 데이터
				- water_data: 연도별 용수이용량 데이터 리스트
					각 원소는 {'year': int, 'withdrawal': float}
				- flow_data: 유량 관측소 일유량 데이터 (TRWR 계산용)
					각 원소는 {'year': int, 'daily_flows': [m³/s values]}
				- climate_data: 기후 데이터 (ET0 계산 및 스케일링용)
					{'monthly_data': [{'year': int, 'months': [{ta, rhm, ws, si, rn}, ...]}]}
				- baseline_years: 기준기간 연도 리스트 (예: [1991, ..., 2020])

		Returns:
			연도별 WSI 값 배열
		"""
		water_data = collected_data.get('water_data', [])
		flow_data = collected_data.get('flow_data', [])
		climate_data_dict = collected_data.get('climate_data', {})
		baseline_years = collected_data.get('baseline_years', [])

		if not water_data:
			self.logger.warning("수자원 데이터가 없습니다. 기본값 0으로 설정합니다.")
			return np.array([0.0])

		# 1. TRWR 계산 (기준기간 평균)
		trwr_baseline = self._calculate_trwr_baseline(flow_data, baseline_years)
		self.logger.info(f"TRWR baseline: {trwr_baseline:.2e} m³/year")

		# 2. 유효강수량 기준 스케일링 계산
		scaling_factors = self._calculate_scaling_factors(
			climate_data_dict, baseline_years
		)

		# 3. WSI 계산
		yearly_wsi = []

		for year_data in water_data:
			year = year_data.get('year')
			withdrawal = year_data.get('withdrawal', 0.0)  # 용수이용량 (m³/year)

			# 미래 TRWR 스케일링
			scale_factor = scaling_factors.get(year, 1.0)
			trwr_future = trwr_baseline * scale_factor

			# ARWR 계산 (환경유지유량 차감)
			arwr_future = trwr_future * 0.63  # αEFR = 0.37

			# WSI 계산
			if arwr_future > 0:
				wsi = withdrawal / arwr_future
			else:
				wsi = 0.0

			yearly_wsi.append(wsi)

		wsi_array = np.array(yearly_wsi, dtype=float)
		self.logger.info(f"WSI 데이터: {len(wsi_array)}개 연도, 범위: {wsi_array.min():.2f} ~ {wsi_array.max():.2f}")

		return wsi_array

	def _calculate_trwr_baseline(
		self,
		flow_data: list,
		baseline_years: list
	) -> float:
		"""
		재생 가능 수자원 (TRWR) 기준값 계산

		Args:
			flow_data: 유량 관측소 일유량 데이터
				각 원소는 {'year': int, 'daily_flows': [m³/s values]}
			baseline_years: 기준기간 연도 리스트

		Returns:
			TRWR 기준값 (m³/year)
		"""
		if not flow_data or not baseline_years:
			self.logger.warning("유량 데이터 또는 기준기간이 없습니다. 기본값 사용.")
			return 1.0e10  # 기본값

		baseline_volumes = []

		for year_data in flow_data:
			year = year_data.get('year')
			if year not in baseline_years:
				continue

			daily_flows = year_data.get('daily_flows', [])  # m³/s

			if not daily_flows:
				continue

			# 결측값 처리
			valid_flows = [f for f in daily_flows if f is not None and f >= 0]
			missing_ratio = 1 - len(valid_flows) / len(daily_flows)

			# 결측 비율이 20~30% 이상이면 해당 연도 제외
			if missing_ratio > 0.25:
				self.logger.warning(f"{year}년 결측 비율 {missing_ratio:.1%} - 제외")
				continue

			# Volume_y 계산: 일유량 × 86400초 누적
			# 결측값은 평균으로 보정 (결측 < 10% 조건 만족)
			if missing_ratio > 0:
				mean_flow = np.mean(valid_flows)
				daily_flows_filled = [
					f if f is not None and f >= 0 else mean_flow
					for f in daily_flows
				]
			else:
				daily_flows_filled = daily_flows

			# 연간 총 유량 (m³/year)
			volume_y = sum(daily_flows_filled) * 86400

			baseline_volumes.append(volume_y)

		if not baseline_volumes:
			self.logger.warning("유효한 기준기간 유량 데이터가 없습니다.")
			return 1.0e10

		# TRWR = 기준기간 평균
		trwr = np.mean(baseline_volumes)

		return trwr

	def _calculate_scaling_factors(
		self,
		climate_data: Dict[str, Any],
		baseline_years: list
	) -> Dict[int, float]:
		"""
		유효강수량(P - ET0) 기반 TRWR 스케일링 계수 계산

		Args:
			climate_data: 기후 데이터
				{'monthly_data': [{'year': int, 'months': [{ta, rhm, ws, si, rn}, ...]}]}
			baseline_years: 기준기간 연도 리스트

		Returns:
			연도별 스케일링 계수 딕셔너리 {year: scale_factor}
		"""
		monthly_data = climate_data.get('monthly_data', [])

		if not monthly_data or not baseline_years:
			self.logger.warning("기후 데이터 또는 기준기간이 없습니다. 스케일링 계수 1.0 사용.")
			return {}

		# 1. 연도별 유효강수량 계산
		p_eff_yearly = {}

		for year_data in monthly_data:
			year = year_data.get('year')
			months = year_data.get('months', [])

			if not months:
				continue

			annual_p_eff = 0.0

			for month_data in months:
				ta = month_data.get('ta', 15.0)    # 기온 (°C)
				rhm = month_data.get('rhm', 60.0)  # 상대습도 (%)
				ws = month_data.get('ws', 2.0)     # 풍속 (m/s, 10m 기준)
				si = month_data.get('si', 150.0)   # 일사량 (W/m²)
				rn = month_data.get('rn', 50.0)    # 강수량 (mm)

				# ET0 계산 (Penman-Monteith 식)
				et0 = self._calculate_et0(ta, rhm, ws, si)

				# 월별 유효강수량
				p_eff_month = rn - et0
				annual_p_eff += p_eff_month

			p_eff_yearly[year] = annual_p_eff

		# 2. 기준기간 평균 계산
		baseline_p_eff = [
			p_eff_yearly[y] for y in baseline_years if y in p_eff_yearly
		]

		if not baseline_p_eff:
			self.logger.warning("기준기간 유효강수량 데이터가 없습니다.")
			return {}

		p_eff_baseline_mean = np.mean(baseline_p_eff)
		self.logger.info(f"기준기간 평균 유효강수량: {p_eff_baseline_mean:.2f} mm/year")

		# 3. 연도별 스케일링 계수 계산
		scaling_factors = {}

		for year, p_eff in p_eff_yearly.items():
			if p_eff_baseline_mean > 0:
				scale_factor = p_eff / p_eff_baseline_mean
			else:
				scale_factor = 1.0

			scaling_factors[year] = scale_factor

		return scaling_factors

	def _calculate_et0(
		self,
		ta: float,
		rhm: float,
		ws: float,
		si: float
	) -> float:
		"""
		Penman-Monteith 식을 사용한 ET0 계산

		ET0 = [0.408 * Δ * (Rn - G) + γ * (900 / (T + 273)) * u2 * (es - ea)]
		      / [Δ + γ * (1 + 0.34 * u2)]

		Args:
			ta: 월평균 기온 (°C)
			rhm: 상대습도 (%)
			ws: 풍속 (m/s, 10m 기준)
			si: 일사량 (W/m²)

		Returns:
			ET0 (mm/month, 대략값)
		"""
		# 1. 포화수증기압 (kPa)
		es = 0.6108 * np.exp(17.27 * ta / (ta + 237.3))

		# 2. 실제수증기압 (kPa)
		ea = es * rhm / 100.0

		# 3. 기울기 Δ (kPa/°C)
		delta = 4098 * es / ((ta + 237.3) ** 2)

		# 4. 풍속 보정 (10m → 2m)
		u2 = ws * 4.87 / np.log(67.8 * 10 - 5.42)

		# 5. 순복사량 Rn (MJ/m²/day)
		# SI (W/m²) → Rs (MJ/m²/day): Rs ≈ SI * 0.0864
		rs = si * 0.0864

		# 순단파복사량
		rns = (1 - 0.23) * rs

		# 순장파복사량
		t_k = ta + 273.16
		# Rso 근사 (맑은 날 일사량, 간단 근사)
		rso = rs * 1.3  # 간단 근사

		rnl = (
			4.903e-9 * (t_k ** 4)
			* (0.34 - 0.14 * np.sqrt(ea))
			* (1.35 * (rs / rso if rso > 0 else 0) - 0.35)
		)

		# 순복사량
		rn = rns - rnl

		# 지면열 G = 0 (월 기준)
		g = 0

		# 6. 심리계수 γ (kPa/°C)
		gamma = 0.665e-3 * 101.3  # 표준 대기압 가정

		# 7. ET0 계산 (mm/day)
		numerator = (
			0.408 * delta * (rn - g)
			+ gamma * (900 / (ta + 273)) * u2 * (es - ea)
		)
		denominator = delta + gamma * (1 + 0.34 * u2)

		if denominator > 0:
			et0_daily = numerator / denominator
		else:
			et0_daily = 0.0

		# mm/day → mm/month (30일 가정)
		et0_monthly = et0_daily * 30

		return max(et0_monthly, 0.0)  # 음수 방지
