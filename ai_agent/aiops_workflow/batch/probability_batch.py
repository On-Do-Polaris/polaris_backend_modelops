'''
파일명: probability_batch.py
최종 수정일: 2025-11-22
버전: v02
파일 개요: P(H) 전체 배치 계산 (9개 리스크 에이전트 연결)
'''

from typing import List, Dict, Any
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from ...agents.aiops.probability_calculate import (
	CoastalFloodProbabilityAgent,
	ColdWaveProbabilityAgent,
	DroughtProbabilityAgent,
	HighTemperatureProbabilityAgent,
	InlandFloodProbabilityAgent,
	TyphoonProbabilityAgent,
	UrbanFloodProbabilityAgent,
	WaterScarcityProbabilityAgent,
	WildfireProbabilityAgent
)

logger = logging.getLogger(__name__)


class ProbabilityBatchProcessor:
	"""P(H) 전체 배치 계산 프로세서"""

	def __init__(self, config: Dict[str, Any]):
		self.config = config
		self.db_config = config.get('db_config', {})
		self.storage_config = config.get('storage_config', {})
		self.parallel_workers = config.get('parallel_workers', 4)

		# 9개 리스크 에이전트 초기화
		self.agents = {
			'coastal_flood': CoastalFloodProbabilityAgent(),
			'cold_wave': ColdWaveProbabilityAgent(),
			'drought': DroughtProbabilityAgent(),
			'high_temperature': HighTemperatureProbabilityAgent(),
			'inland_flood': InlandFloodProbabilityAgent(),
			'typhoon': TyphoonProbabilityAgent(),
			'urban_flood': UrbanFloodProbabilityAgent(),
			'water_scarcity': WaterScarcityProbabilityAgent(),
			'wildfire': WildfireProbabilityAgent()
		}

		logger.info(f"ProbabilityBatchProcessor initialized with {self.parallel_workers} workers")

	def process_all_grids(self, grid_coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
		"""전체 격자 P(H) 계산"""
		start_time = datetime.now()
		logger.info(f"Starting P(H) batch for {len(grid_coordinates)} grids")

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

		logger.info(f"P(H) batch completed: {summary['processed']}/{summary['total_grids']} grids in {duration:.2f}s")

		return summary

	def _process_single_grid(self, coordinate: Dict[str, float]) -> Dict[str, Any]:
		"""단일 격자 P(H) 계산"""
		lat = coordinate['lat']
		lon = coordinate['lon']

		try:
			# 1. 기후 데이터 수집
			collected_data = self._fetch_climate_data(lat, lon)

			# 2. 9개 리스크별 P(H) 계산
			probabilities = {}

			for risk_type, agent in self.agents.items():
				try:
					result = agent.calculate_probability(collected_data)
					probabilities[risk_type] = {
						'bin_probabilities': result['bin_probabilities'],
						'bin_base_damage_rates': result['bin_base_damage_rates']
					}
				except Exception as e:
					logger.error(f"Risk {risk_type} failed for grid ({lat}, {lon}): {str(e)}")
					probabilities[risk_type] = None

			# 3. 결과 저장
			self._save_results(lat, lon, probabilities)

			return {
				'status': 'success',
				'coordinate': coordinate,
				'timestamp': datetime.now().isoformat(),
				'risks_calculated': len([v for v in probabilities.values() if v is not None])
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
			}
		}

	def _save_results(self, lat: float, lon: float, probabilities: Dict[str, Any]) -> None:
		"""결과 저장 (DB)"""
		logger.debug(f"Saving P(H) results for grid ({lat}, {lon})")

		# TODO: 데이터베이스 저장 구현
		# 예: INSERT INTO probability_results (lat, lon, risk_type, bin_probabilities, bin_base_damage_rates, updated_at)
		pass
