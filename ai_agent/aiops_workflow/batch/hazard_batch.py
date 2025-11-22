'''
파일명: hazard_batch.py
최종 수정일: 2025-11-22
버전: v02
파일 개요: Hazard Score 전체 배치 계산 (9개 리스크 에이전트 연결)
'''

from typing import List, Dict, Any
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from ...agents.aiops.hazard_calculate import (
	CoastalFloodHScoreAgent,
	ColdWaveHScoreAgent,
	DroughtHScoreAgent,
	HighTemperatureHScoreAgent,
	InlandFloodHScoreAgent,
	TyphoonHScoreAgent,
	UrbanFloodHScoreAgent,
	WaterScarcityHScoreAgent,
	WildfireHScoreAgent
)

logger = logging.getLogger(__name__)


class HazardBatchProcessor:
	"""Hazard Score 전체 배치 계산 프로세서"""

	def __init__(self, config: Dict[str, Any]):
		self.config = config
		self.db_config = config.get('db_config', {})
		self.storage_config = config.get('storage_config', {})
		self.parallel_workers = config.get('parallel_workers', 4)

		# 9개 리스크 에이전트 초기화
		self.agents = {
			'coastal_flood': CoastalFloodHScoreAgent(),
			'cold_wave': ColdWaveHScoreAgent(),
			'drought': DroughtHScoreAgent(),
			'high_temperature': HighTemperatureHScoreAgent(),
			'inland_flood': InlandFloodHScoreAgent(),
			'typhoon': TyphoonHScoreAgent(),
			'urban_flood': UrbanFloodHScoreAgent(),
			'water_scarcity': WaterScarcityHScoreAgent(),
			'wildfire': WildfireHScoreAgent()
		}

		logger.info(f"HazardBatchProcessor initialized with {self.parallel_workers} workers")

	def process_all_grids(self, grid_coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
		"""전체 격자 Hazard Score 계산"""
		start_time = datetime.now()
		logger.info(f"Starting Hazard Score batch for {len(grid_coordinates)} grids")

		results = []
		failed_count = 0

		with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
			futures = {executor.submit(self._process_single_grid, coord): coord for coord in grid_coordinates}

			for future in as_completed(futures):
				coord = futures[future]
				try:
					result = future.result()
					results.append(result)

					if result['status'] == 'success':
						logger.info(f"Grid ({coord['lat']}, {coord['lon']}) processed successfully")
					else:
						failed_count += 1
						logger.error(f"Grid ({coord['lat']}, {coord['lon']}) failed: {result.get('error')}")

				except Exception as e:
					failed_count += 1
					logger.error(f"Grid ({coord['lat']}, {coord['lon']}) exception: {str(e)}")

		duration = (datetime.now() - start_time).total_seconds()

		summary = {
			'total_grids': len(grid_coordinates),
			'processed': len(results) - failed_count,
			'failed': failed_count,
			'success_rate': round((len(results) - failed_count) / len(grid_coordinates) * 100, 2) if grid_coordinates else 0,
			'duration_seconds': duration,
			'duration_hours': round(duration / 3600, 2),
			'start_time': start_time.isoformat(),
			'end_time': datetime.now().isoformat()
		}

		logger.info(f"Hazard Score batch completed: {summary['processed']}/{summary['total_grids']} grids in {duration:.2f}s")

		return summary

	def _process_single_grid(self, coordinate: Dict[str, float]) -> Dict[str, Any]:
		"""단일 격자 Hazard Score 계산"""
		lat = coordinate['lat']
		lon = coordinate['lon']

		try:
			# 1. 기후 데이터 수집
			collected_data = self._fetch_climate_data(lat, lon)

			# 2. 9개 리스크별 Hazard Score 계산
			hazard_scores = {}

			for risk_type, agent in self.agents.items():
				try:
					result = agent.calculate_hazard_score(collected_data)

					if result.get('status') == 'completed':
						hazard_scores[risk_type] = {
							'hazard_score': result['hazard_score'],
							'hazard_score_100': result['hazard_score_100'],
							'hazard_level': result['hazard_level']
						}
					else:
						logger.error(f"Risk {risk_type} failed for grid ({lat}, {lon}): {result.get('error')}")
						hazard_scores[risk_type] = None

				except Exception as e:
					logger.error(f"Risk {risk_type} exception for grid ({lat}, {lon}): {str(e)}")
					hazard_scores[risk_type] = None

			# 3. 결과 저장
			self._save_results(lat, lon, hazard_scores)

			return {
				'status': 'success',
				'coordinate': coordinate,
				'timestamp': datetime.now().isoformat(),
				'risks_calculated': len([v for v in hazard_scores.values() if v is not None])
			}

		except Exception as e:
			return {
				'status': 'failed',
				'coordinate': coordinate,
				'error': str(e),
				'timestamp': datetime.now().isoformat()
			}

	def _fetch_climate_data(self, lat: float, lon: float) -> Dict[str, Any]:
		"""기후 데이터 수집 (DB 또는 API)"""
		logger.debug(f"Fetching climate data for ({lat}, {lon})")

		# TODO: 실제 데이터베이스 또는 API 연동
		return {
			'location': {'lat': lat, 'lon': lon},
			'climate_data': {
				'wsdi': [],
				'csdi': [],
				'temperature': [],
				'precipitation': [],
				'wind_speed': [],
				'sea_level': [],
				'drought_index': [],
			}
		}

	def _save_results(self, lat: float, lon: float, hazard_scores: Dict[str, Any]) -> None:
		"""결과 저장 (DB)"""
		logger.debug(f"Saving Hazard Score results for grid ({lat}, {lon})")

		# TODO: 데이터베이스 저장 구현
		# 예: INSERT INTO hazard_scores (lat, lon, risk_type, hazard_score, hazard_level, updated_at)
		pass
