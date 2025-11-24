'''
파일명: probability_batch.py
최종 수정일: 2025-11-22
버전: v03
파일 개요: P(H) 전체 배치 계산 (9개 리스크 에이전트 연결)
'''

from typing import List, Dict, Any
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from ..agents.probability_calculate import (
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
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ProbabilityBatchProcessor:
    """P(H) 전체 배치 계산 프로세서"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
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
                        logger.info(f"Grid ({coord['latitude']}, {coord['longitude']}) processed successfully")
                    else:
                        failed_count += 1
                        logger.error(f"Grid ({coord['latitude']}, {coord['longitude']}) failed: {result.get('error')}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Grid ({coord['latitude']}, {coord['longitude']}) exception: {str(e)}")

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
        latitude = coordinate['latitude']
        longitude = coordinate['longitude']

        try:
            # 1. 기후 데이터 수집
            climate_data = self._fetch_climate_data(coordinate)

            # 2. 9개 리스크별 P(H) 계산
            probabilities = {}

            for risk_type, agent in self.agents.items():
                try:
                    result = agent.calculate_probability(climate_data)
                    probabilities[risk_type] = {
                        'probability': result.get('probability'),
                        'bin_data': result.get('bin_data')
                    }
                except Exception as e:
                    logger.error(f"Risk {risk_type} failed for grid ({latitude}, {longitude}): {str(e)}")
                    probabilities[risk_type] = None

            # 3. 결과 저장
            self._save_results(coordinate, probabilities)

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

    def _fetch_climate_data(self, coordinate: Dict[str, float]) -> Dict[str, Any]:
        """기후 데이터 조회 (실제 구현)"""
        return DatabaseConnection.fetch_climate_data(
            coordinate['latitude'],
            coordinate['longitude']
        )

    def _save_results(self, coordinate: Dict[str, float], probabilities: Dict[str, Any]) -> None:
        """결과 저장 (실제 구현)"""
        results = []
        for risk_type, data in probabilities.items():
            if data is not None:
                results.append({
                    'latitude': coordinate['latitude'],
                    'longitude': coordinate['longitude'],
                    'risk_type': risk_type,
                    'probability': data.get('probability'),
                    'bin_data': data.get('bin_data')
                })

        if results:
            DatabaseConnection.save_probability_results(results)
