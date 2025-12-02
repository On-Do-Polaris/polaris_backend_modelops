'''
파일명: probability_batch.py
최종 수정일: 2025-12-02
버전: v04
파일 개요: P(H) 전체 배치 계산 (9개 리스크 에이전트 연결) - ProcessPoolExecutor 호환
변경 이력:
    - 2025-12-02: v04 - ProcessPoolExecutor 호환성 수정
        * 독립 함수(_process_single_grid_worker) 추출
        * 워커별 에이전트 자체 생성
        * tqdm 진행률 표시 추가
        * 에러 처리 강화
'''

from typing import List, Dict, Any
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from ..agents.probability_calculate import (
    SeaLevelRiseProbabilityAgent,
    ExtremeColdProbabilityAgent,
    DroughtProbabilityAgent,
    ExtremeHeatProbabilityAgent,
    RiverFloodProbabilityAgent,
    TyphoonProbabilityAgent,
    UrbanFloodProbabilityAgent,
    WaterStressProbabilityAgent,
    WildfireProbabilityAgent
)
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


def _process_single_grid_worker(coordinate: Dict[str, float]) -> Dict[str, Any]:
    """
    워커 프로세스에서 실행되는 독립 함수 (pickle 가능)

    Args:
        coordinate: 격자 좌표 {'latitude': float, 'longitude': float}

    Returns:
        처리 결과 딕셔너리
    """
    latitude = coordinate['latitude']
    longitude = coordinate['longitude']

    try:
        # 1. 에이전트 생성 (각 워커마다 독립적)
        agents = {
            "sea_level_rise": SeaLevelRiseProbabilityAgent(),
            "extreme_cold": ExtremeColdProbabilityAgent(),
            'drought': DroughtProbabilityAgent(),
            'high_temperature': ExtremeHeatProbabilityAgent(),
            "river_flood": RiverFloodProbabilityAgent(),
            'typhoon': TyphoonProbabilityAgent(),
            'urban_flood': UrbanFloodProbabilityAgent(),
            "water_stress": WaterStressProbabilityAgent(),
            'wildfire': WildfireProbabilityAgent()
        }

        # 2. 기후 데이터 조회 (독립 DB 연결)
        climate_data = DatabaseConnection.fetch_climate_data(latitude, longitude)

        # 3. 9개 리스크별 P(H) 계산
        probabilities = {}
        for risk_type, agent in agents.items():
            try:
                result = agent.calculate_probability(climate_data)
                if result.get('status') == 'completed':
                    probabilities[risk_type] = {
                        'aal': result.get('aal'),
                        'bin_data': result.get('calculation_details', {}).get('bins')
                    }
                else:
                    logger.error(
                        f"Risk {risk_type} failed for grid ({latitude}, {longitude}): "
                        f"{result.get('error')}"
                    )
                    probabilities[risk_type] = None
            except Exception as e:
                logger.error(
                    f"Risk {risk_type} exception for grid ({latitude}, {longitude}): "
                    f"{str(e)}"
                )
                probabilities[risk_type] = None

        # 4. 결과 저장 (에러 처리 포함)
        try:
            results = []
            for risk_type, data in probabilities.items():
                if data is not None:
                    results.append({
                        'latitude': latitude,
                        'longitude': longitude,
                        'risk_type': risk_type,
                        'aal': data.get('aal'),
                        'bin_data': data.get('bin_data')
                    })

            if results:
                DatabaseConnection.save_probability_results(results)
        except Exception as e:
            logger.error(f"DB save failed for ({latitude}, {longitude}): {str(e)}")
            raise  # 저장 실패는 전체 실패로 처리

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


class ProbabilityBatchProcessor:
    """P(H) 전체 배치 계산 프로세서"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.parallel_workers = config.get('parallel_workers', 2)
        logger.info(f"ProbabilityBatchProcessor initialized with {self.parallel_workers} workers")

    def process_all_grids(self, grid_coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
        """전체 격자 P(H) 계산"""
        start_time = datetime.now()
        logger.info(f"Starting P(H) batch for {len(grid_coordinates)} grids")

        results = []
        failed_count = 0

        with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
            futures = {
                executor.submit(_process_single_grid_worker, coord): coord
                for coord in grid_coordinates
            }

            # tqdm으로 진행률 표시
            with tqdm(total=len(futures), desc="Processing P(H)", unit="grid") as pbar:
                for future in as_completed(futures):
                    coord = futures[future]
                    try:
                        result = future.result()
                        results.append(result)

                        if result['status'] == 'success':
                            pbar.set_postfix({
                                'success': len(results) - failed_count,
                                'failed': failed_count,
                                'risks': f"{result['risks_calculated']}/9"
                            })
                        else:
                            failed_count += 1
                            logger.error(
                                f"Grid ({coord['latitude']}, {coord['longitude']}) "
                                f"failed: {result.get('error')}"
                            )
                            pbar.set_postfix({
                                'success': len(results) - failed_count,
                                'failed': failed_count
                            })

                    except Exception as e:
                        failed_count += 1
                        logger.error(
                            f"Grid ({coord['latitude']}, {coord['longitude']}) "
                            f"exception: {str(e)}"
                        )

                    pbar.update(1)  # 진행률 업데이트

        duration = (datetime.now() - start_time).total_seconds()

        summary = {
            'total_grids': len(grid_coordinates),
            'processed': len(results) - failed_count,
            'failed': failed_count,
            'success_rate': round(
                (len(results) - failed_count) / len(grid_coordinates) * 100, 2
            ) if grid_coordinates else 0,
            'duration_seconds': duration,
            'duration_hours': round(duration / 3600, 2),
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat()
        }

        logger.info(
            f"P(H) batch completed: {summary['processed']}/{summary['total_grids']} "
            f"grids in {duration:.2f}s (Success rate: {summary['success_rate']}%)"
        )

        return summary
