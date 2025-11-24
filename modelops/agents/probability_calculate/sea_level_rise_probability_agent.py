'''
파일명: sea_level_rise_probability_agent.py
최종 수정일: 2025-11-24
버전: v2
파일 개요: 해수면 상승 리스크 확률 P(H) 계산 Agent
변경 이력:
	- 2025-11-24: v2 - DEM 데이터 기반 ground_level 사용
		* ground_level 기본값 5m → DEM 최저 고도 사용
		* DEM 경로에서 모든 .txt 파일 읽어 최저 고도 추출
	- 2025-11-21: v1 - AAL에서 확률 계산으로 분리
		* 강도지표: X_slr(t,j) = max inundation_depth(t,τ,j)
		* inundation_depth = max(zos/100 - ground_level, 0)
		* bin: [0), [0~0.3m), [0.3~1.0m), [≥1.0m)
		* DR_intensity: [0.00, 0.02, 0.15, 0.35] (국제 Damage Curve 중간값)
		* 취약성 스케일링 제거
'''
from typing import Dict, Any
import numpy as np
from pathlib import Path
from .base_probability_agent import BaseProbabilityAgent


class SeaLevelRiseProbabilityAgent(BaseProbabilityAgent):
	"""
	해수면 상승 리스크 확률 P(H) 계산 Agent

	사용 데이터: CMIP6 zos (해수면 높이, m)
	강도지표: X_slr(t,j) = max over τ in year t [ inundation_depth(t,τ,j) ]
	inundation_depth(t,τ,j) = max(zos(t,τ) - ground_level(j), 0)
	"""

	def __init__(self):
		"""
		SeaLevelRiseProbabilityAgent 초기화

		bin 구간 (침수 깊이):
			- bin1: 0 m (침수 없음)
			- bin2: 0 ~ 0.3 m (경미 피해)
			- bin3: 0.3 ~ 1.0 m (중간 피해)
			- bin4: >= 1.0 m (심각 피해)

		기본 손상률 (DR_intensity - 국제 Damage Curve 중간값):
			- bin1: 0%
			- bin2: 2%
			- bin3: 15%
			- bin4: 35%
		"""
		bins = [
			(0, 0),          # bin1: 침수 없음
			(0, 0.3),        # bin2: 0 ~ 0.3m
			(0.3, 1.0),      # bin3: 0.3 ~ 1.0m
			(1.0, float('inf'))  # bin4: >= 1.0m
		]

		dr_intensity = [
			0.00,   # 0%
			0.02,   # 2%
			0.15,   # 15%
			0.35    # 35%
		]

		super().__init__(
			risk_type='sea_level_rise',
			bins=bins,
			dr_intensity=dr_intensity
		)

	def _load_dem_min_elevation(self, dem_path: str) -> float:
		"""
		DEM 데이터에서 최저 고도 추출

		Args:
			dem_path: DEM 파일 또는 디렉토리 경로

		Returns:
			최저 고도 (meters)
		"""
		dem_path_obj = Path(dem_path)

		if dem_path_obj.is_file():
			dem_files = [dem_path_obj]
		elif dem_path_obj.is_dir():
			dem_files = list(dem_path_obj.glob('*.txt'))
		else:
			self.logger.warning(f"DEM 경로를 찾을 수 없습니다: {dem_path}, 기본값 0m 사용")
			return 0.0

		if not dem_files:
			self.logger.warning(f"DEM 파일이 없습니다: {dem_path}, 기본값 0m 사용")
			return 0.0

		min_elevation = float('inf')

		for dem_file in dem_files:
			try:
				with open(dem_file, 'r', encoding='utf-8') as f:
					for line in f:
						parts = line.strip().split()
						if len(parts) >= 3:
							try:
								elevation = float(parts[2])  # Z 값
								if elevation < min_elevation:
									min_elevation = elevation
							except ValueError:
								continue
			except Exception as e:
				self.logger.warning(f"DEM 파일 읽기 실패 ({dem_file}): {e}")
				continue

		if min_elevation == float('inf'):
			self.logger.warning("유효한 DEM 데이터를 찾을 수 없습니다. 기본값 0m 사용")
			return 0.0

		self.logger.info(f"DEM 최저 고도: {min_elevation:.2f}m")
		return min_elevation

	def calculate_intensity_indicator(self, collected_data: Dict[str, Any]) -> np.ndarray:
		"""
		해수면 상승 강도지표 X_slr(t,j) 계산

		Args:
			collected_data: 수집된 해양 및 지형 데이터
				- zos_data: 연도별 시점별 zos 데이터
					각 원소는 {'year': int, 'zos_values': [m values]}
				- ground_level: 사이트 지반고도 (m) - DEM 데이터로부터 계산
				- dem_path: DEM 파일 경로 (ground_level 없을 경우)

		Returns:
			연도별 최대 침수 깊이 값 배열 (m)
		"""
		ocean_data = collected_data.get('ocean_data', {})
		zos_data = ocean_data.get('zos_data', [])

		# ground_level을 DEM 데이터로부터 가져오기
		ground_level = ocean_data.get('ground_level')
		if ground_level is None:
			dem_path = ocean_data.get('dem_path', 'scratch/dem')
			ground_level = self._load_dem_min_elevation(dem_path)

		if not zos_data:
			self.logger.warning("ZOS 데이터가 없습니다. 기본값 0으로 설정합니다.")
			return np.array([0.0])

		yearly_max_inundation = []

		for year_data in zos_data:
			year = year_data.get('year')
			zos_values = year_data.get('zos_values', [])  # m 단위

			if not zos_values:
				yearly_max_inundation.append(0.0)
				continue

			# 시점별 침수 깊이 계산
			inundation_depths = []
			for zos_m in zos_values:
				inundation_depth = max(zos_m - ground_level, 0.0)
				inundation_depths.append(inundation_depth)

			# 연도별 최대 침수 깊이
			max_inundation = max(inundation_depths) if inundation_depths else 0.0
			yearly_max_inundation.append(max_inundation)

		depth_array = np.array(yearly_max_inundation, dtype=float)
		self.logger.info(
			f"침수 깊이 데이터: {len(depth_array)}개 연도, "
			f"범위: {depth_array.min():.3f}m ~ {depth_array.max():.3f}m"
		)

		return depth_array

	def _classify_into_bins(self, intensity_values: np.ndarray) -> np.ndarray:
		"""
		침수 깊이를 bin으로 분류 (해수면 상승 전용)

		Args:
			intensity_values: 연도별 침수 깊이 배열 (m)

		Returns:
			각 연도의 bin 인덱스 배열 (0-based)
		"""
		bin_indices = np.zeros(len(intensity_values), dtype=int)

		for idx, depth in enumerate(intensity_values):
			if depth == 0:
				bin_indices[idx] = 0  # bin1: 침수 없음
			elif depth < 0.3:
				bin_indices[idx] = 1  # bin2: 0 ~ 0.3m
			elif depth < 1.0:
				bin_indices[idx] = 2  # bin3: 0.3 ~ 1.0m
			else:
				bin_indices[idx] = 3  # bin4: >= 1.0m

		return bin_indices
