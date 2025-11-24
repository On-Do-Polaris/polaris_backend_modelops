'''
파일명: hazard_batch.py
최종 수정일: 2025-11-22
버전: v03
파일 개요: Hazard Score 전체 배치 계산 (9개 리스크 에이전트 연결)
'''

from typing import List, Dict, Any
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from ..agents.hazard_calculate import (
    SeaLevelRiseHScoreAgent,
    ExtremeColdHScoreAgent,
    DroughtHScoreAgent,
    ExtremeHeatHScoreAgent,
    RiverFloodHScoreAgent,
    TyphoonHScoreAgent,
    UrbanFloodHScoreAgent,
    WaterStressHScoreAgent,
    WildfireHScoreAgent
)
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class HazardBatchProcessor:
    """Hazard Score 전체 배치 계산 프로세서"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.parallel_workers = config.get('parallel_workers', 4)

        # 9개 리스크 에이전트 초기화
        self.agents = {
            "sea_level_rise": SeaLevelRiseHScoreAgent(),
            "extreme_cold": ExtremeColdHScoreAgent(),
            'drought': DroughtHScoreAgent(),
            'high_temperature': ExtremeHeatHScoreAgent(),
            "river_flood": RiverFloodHScoreAgent(),
            'typhoon': TyphoonHScoreAgent(),
            'urban_flood': UrbanFloodHScoreAgent(),
            "water_stress": WaterStressHScoreAgent(),
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

        logger.info(f"Hazard Score batch completed: {summary['processed']}/{summary['total_grids']} grids in {duration:.2f}s")

        return summary

    def _process_single_grid(self, coordinate: Dict[str, float]) -> Dict[str, Any]:
        """단일 격자 Hazard Score 계산"""
        latitude = coordinate['latitude']
        longitude = coordinate['longitude']

        try:
            # 1. 기후 데이터 수집
            climate_data = self._fetch_climate_data(coordinate)

            # 2. 9개 리스크별 Hazard Score 계산
            hazard_scores = {}

            for risk_type, agent in self.agents.items():
                try:
                    result = agent.calculate_hazard_score(climate_data)

                    if result.get('status') == 'completed':
                        hazard_scores[risk_type] = {
                            'hazard_score': result['hazard_score'],
                            'hazard_score_100': result['hazard_score_100'],
                            'hazard_level': result['hazard_level']
                        }
                    else:
                        logger.error(f"Risk {risk_type} failed for grid ({latitude}, {longitude}): {result.get('error')}")
                        hazard_scores[risk_type] = None

                except Exception as e:
                    logger.error(f"Risk {risk_type} exception for grid ({latitude}, {longitude}): {str(e)}")
                    hazard_scores[risk_type] = None

            # 3. 결과 저장
            self._save_results(coordinate, hazard_scores)

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

    def _fetch_climate_data(self, coordinate: Dict[str, float]) -> Dict[str, Any]:
        """기후 데이터 조회 (실제 구현)"""
        return DatabaseConnection.fetch_climate_data(
            coordinate['latitude'],
            coordinate['longitude']
        )

    def _save_results(self, coordinate: Dict[str, float], hazard_scores: Dict[str, Any]) -> None:
        """결과 저장 (실제 구현)"""
        results = []
        for risk_type, data in hazard_scores.items():
            if data is not None:
                results.append({
                    'latitude': coordinate['latitude'],
                    'longitude': coordinate['longitude'],
                    'risk_type': risk_type,
                    'hazard_score': data.get('hazard_score'),
                    'hazard_score_100': data.get('hazard_score_100'),
                    'hazard_level': data.get('hazard_level')
                })

        if results:
            DatabaseConnection.save_hazard_results(results)
