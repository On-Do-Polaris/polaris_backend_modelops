'''
파일명: typhoon_probability_agent.py
최종 수정일: 2025-11-21
버전: v1
파일 개요: 열대성 태풍 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: S_tc(t,j) = Σ w_tc[bin_inst(storm,τ,j)] (누적 노출 지수)
		* bin_year(t,j): S_tc → 연도 bin 변환
		* DR_intensity: [0.00, 0.02, 0.10, 0.30]
		* 취약성 스케일링 제거
'''
from typing import Dict, Any, List
import numpy as np
import math
from .base_probability_agent import BaseProbabilityAgent


class TyphoonProbabilityAgent(BaseProbabilityAgent):
	"""
	열대성 태풍 리스크 확률 P(H) 계산 Agent

	사용 데이터: KMA 태풍 Best Track API
	강도지표: S_tc(t,j) = 연도별 누적 노출 지수
	- bin_inst(storm,τ,j): 시점별 태풍 영향 등급
	- w_tc: bin별 가중치 [0, 1, 3, 6]
	"""

	def __init__(self):
		"""
		TyphoonProbabilityAgent 초기화

		bin 구간 (연도별 누적 노출 지수 S_tc):
			- bin1: S_tc = 0 (영향 없음)
			- bin2: 0 < S_tc <= 5 (약한 노출)
			- bin3: 5 < S_tc <= 15 (중간~강한 노출)
			- bin4: S_tc > 15 (매우 강한 노출)

		기본 손상률 (DR_intensity):
			- bin1: 0%
			- bin2: 2%
			- bin3: 10%
			- bin4: 30%
		"""
		bins = [
			(0, 0),          # bin1: 영향 없음
			(0, 5),          # bin2: 약한 노출
			(5, 15),         # bin3: 중간~강한 노출
			(15, float('inf'))  # bin4: 매우 강한 노출
		]

		dr_intensity = [
			0.00,   # 0%
			0.02,   # 2%
			0.10,   # 10%
			0.30    # 30%
		]

		super().__init__(
			risk_type='태풍',
			bins=bins,
			dr_intensity=dr_intensity
		)

		# 시점별 bin 가중치
		self.w_tc = [0, 1, 3, 6]  # [bin1, bin2(TS), bin3(STS), bin4(TY)]

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		태풍 강도지표 S_tc(t,j) 계산
		S_tc(t,j) = Σ over all (storm,τ in year t) of w_tc[bin_inst(storm,τ,j)]

		Args:
			collected_data: 수집된 태풍 데이터
				- typhoon_tracks: 태풍 Best Track 데이터
					[{'year': int, 'storm_id': str, 'tracks': [track_points]}]
				- site_location: 사이트 위치 {'lon': float, 'lat': float}

		Returns:
			연도별 누적 노출 지수 배열
		"""
		typhoon_data = collected_data.get('typhoon_data', {})
		typhoon_tracks = typhoon_data.get('typhoon_tracks', [])
		site_location = typhoon_data.get('site_location', {'lon': 127.0, 'lat': 37.5})

		if not typhoon_tracks:
			self.logger.warning("태풍 Best Track 데이터가 없습니다. 기본값 0으로 설정합니다.")
			return np.array([0.0])

		site_lon = site_location.get('lon')
		site_lat = site_location.get('lat')

		# 연도별 누적 노출 지수 계산
		yearly_exposure = {}

		for storm_data in typhoon_tracks:
			year = storm_data.get('year')
			storm_id = storm_data.get('storm_id')
			tracks = storm_data.get('tracks', [])

			if year not in yearly_exposure:
				yearly_exposure[year] = 0.0

			for track_point in tracks:
				# 각 시점(τ)에서의 bin_inst 계산
				bin_inst = self._calculate_bin_inst(track_point, site_lon, site_lat)

				# 가중치 적용하여 누적
				yearly_exposure[year] += self.w_tc[bin_inst]

		# 연도별로 정렬하여 배열로 변환
		years = sorted(yearly_exposure.keys())
		exposure_values = [yearly_exposure[y] for y in years]

		exposure_array = np.array(exposure_values, dtype=float)
		self.logger.info(
			f"태풍 노출 지수: {len(exposure_array)}개 연도, "
			f"범위: {exposure_array.min():.2f} ~ {exposure_array.max():.2f}"
		)

		return exposure_array

	def _calculate_bin_inst(
		self,
		track_point: Dict[str, Any],
		site_lon: float,
		site_lat: float
	) -> int:
		"""
		시점별 태풍 영향 등급 bin_inst 계산

		Args:
			track_point: Best Track 시점 데이터
				{'lon': float, 'lat': float, 'grade': str,
				 'gale_long': float, 'gale_short': float, 'gale_dir': float,
				 'storm_long': float, 'storm_short': float, 'storm_dir': float}
			site_lon: 사이트 경도
			site_lat: 사이트 위도

		Returns:
			bin_inst (0: 영향없음, 1: TS급, 2: STS급, 3: TY급)
		"""
		typhoon_lon = track_point.get('lon', 0.0)
		typhoon_lat = track_point.get('lat', 0.0)
		grade = track_point.get('grade', 'TD')

		# 태풍 중심과 사이트 사이 거리 계산
		dx = site_lon - typhoon_lon
		dy = site_lat - typhoon_lat

		# 폭풍(STORM) 타원 체크
		storm_long = track_point.get('storm_long', 0.0)
		storm_short = track_point.get('storm_short', 0.0)
		storm_dir = track_point.get('storm_dir', 0.0)

		inside_storm = self._is_inside_ellipse(
			dx, dy, storm_long, storm_short, storm_dir
		)

		if inside_storm:
			if grade == 'TY':
				return 3  # bin4: TY급 영향
			else:
				return 2  # bin3: STS급 영향

		# 강풍(GALE) 타원 체크
		gale_long = track_point.get('gale_long', 0.0)
		gale_short = track_point.get('gale_short', 0.0)
		gale_dir = track_point.get('gale_dir', 0.0)

		inside_gale = self._is_inside_ellipse(
			dx, dy, gale_long, gale_short, gale_dir
		)

		if inside_gale:
			if grade in ['TS', 'STS', 'TY']:
				return 1  # bin2: TS급 영향
			else:
				return 0  # bin1: 영향 없음
		else:
			return 0  # bin1: 영향 없음

	def _is_inside_ellipse(
		self,
		dx: float,
		dy: float,
		semi_major: float,
		semi_minor: float,
		direction: float
	) -> bool:
		"""
		타원 내부 여부 판정

		Args:
			dx, dy: 중심으로부터의 거리
			semi_major: 장반경 (km)
			semi_minor: 단반경 (km)
			direction: 회전 각도 (도)

		Returns:
			타원 내부 여부
		"""
		if semi_major == 0 or semi_minor == 0:
			return False

		# 각도를 라디안으로 변환
		theta = math.radians(direction)

		# 회전 변환
		x_rot = dx * math.cos(theta) + dy * math.sin(theta)
		y_rot = -dx * math.sin(theta) + dy * math.cos(theta)

		# 타원 방정식
		ellipse_value = (x_rot / semi_major) ** 2 + (y_rot / semi_minor) ** 2

		return ellipse_value <= 1.0

	def _classify_into_bins(self, intensity_values: np.ndarray) -> np.ndarray:
		"""
		누적 노출 지수를 bin으로 분류 (태풍 전용)

		Args:
			intensity_values: 연도별 누적 노출 지수 배열

		Returns:
			각 연도의 bin 인덱스 배열 (0-based)
		"""
		bin_indices = np.zeros(len(intensity_values), dtype=int)

		for idx, s_tc in enumerate(intensity_values):
			if s_tc == 0:
				bin_indices[idx] = 0  # bin1: 영향 없음
			elif s_tc <= 5:
				bin_indices[idx] = 1  # bin2: 약한 노출
			elif s_tc <= 15:
				bin_indices[idx] = 2  # bin3: 중간~강한 노출
			else:
				bin_indices[idx] = 3  # bin4: 매우 강한 노출

		return bin_indices
