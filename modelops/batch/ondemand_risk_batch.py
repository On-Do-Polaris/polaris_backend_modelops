'''
파일명: ondemand_risk_batch.py
최종 수정일: 2025-12-03
버전: v01
파일 개요: On-Demand E × V × AAL 계산 배치 프로세서 (진행률 추적)
변경 이력:
    - 2025-12-03: v01 - 최초 생성
        * E, V, AAL 순차 계산
        * batch_jobs 테이블 진행률 실시간 업데이트
        * 통합 리스크 계산
'''

from typing import List, Dict, Any, Optional
import logging
import traceback
from datetime import datetime

from ..agents.risk_assessment.aal_scaling_agent import AALScalingAgent
from ..agents.risk_assessment.integrated_risk_agent import IntegratedRiskAgent
from ..database.connection import DatabaseConnection
from ..data_loaders.building_data_fetcher import BuildingDataFetcher
from ..api_clients import BuildingClient
from ..utils import GridMapper

logger = logging.getLogger(__name__)


class OnDemandRiskBatch:
    """
    On-Demand 리스크 계산 배치 프로세서

    사용자 요청 시 E → V → AAL을 순차적으로 계산하고
    진행률을 batch_jobs 테이블에 실시간 업데이트
    """

    # 기본 리스크 타입 (9개)
    DEFAULT_RISK_TYPES = [
        'extreme_heat',      # 극한 고온
        'extreme_cold',      # 극한 한파
        'wildfire',          # 산불
        'drought',           # 가뭄
        'water_stress',      # 물 부족
        'sea_level_rise',    # 해수면 상승
        'river_flood',       # 하천 홍수
        'urban_flood',       # 도시 홍수
        'typhoon'            # 태풍
    ]

    def __init__(self, batch_id: str):
        """
        Args:
            batch_id: 배치 작업 ID
        """
        self.batch_id = batch_id
        self.exposure_agent = ExposureAgent()
        self.vulnerability_agent = VulnerabilityAgent()
        self.aal_agent = AALScalingAgent()
        self.integrated_agent = IntegratedRiskAgent()

        logger.info(f"OnDemandRiskBatch initialized: batch_id={batch_id}")

    def run(self, latitude: float, longitude: float,
            risk_types: List[str] = None) -> Dict[str, Any]:
        """
        전체 리스크 계산 실행

        Args:
            latitude, longitude: 사업장 좌표
            risk_types: 계산할 리스크 목록 (None이면 전체 9개)

        Returns:
            최종 통합 리스크 결과

        Raises:
            Exception: 계산 중 오류 발생 시
        """
        start_time = datetime.now()

        try:
            # 리스크 타입 설정
            if risk_types is None:
                risk_types = self.DEFAULT_RISK_TYPES

            logger.info(
                f"Starting ondemand risk calculation: "
                f"batch_id={self.batch_id}, lat={latitude}, lon={longitude}, "
                f"risks={len(risk_types)}"
            )

            # Step 1: H, P(H) 조회 (0% → 10%)
            DatabaseConnection.update_batch_progress(
                self.batch_id, 0, "Fetching H and P(H) from DB"
            )
            hazards_and_probs = self._fetch_hazard_and_probability(
                latitude, longitude, risk_types
            )
            DatabaseConnection.update_batch_progress(
                self.batch_id, 10, "H and P(H) fetched"
            )

            # Step 2: E 계산 (10% → 50%)
            exposures = self._calculate_exposures(
                latitude, longitude, risk_types
            )

            # Step 3: V 계산 (50% → 80%)
            vulnerabilities = self._calculate_vulnerabilities(
                latitude, longitude, risk_types
            )

            # Step 4: AAL 계산 (80% → 95%)
            aal_results = self._calculate_aal_scaled(
                latitude, longitude, risk_types,
                hazards_and_probs['probabilities'], vulnerabilities
            )

            # Step 5: 통합 리스크 계산 (95% → 100%)
            DatabaseConnection.update_batch_progress(
                self.batch_id, 95, "Calculating integrated risk"
            )
            integrated_result = self._calculate_integrated_risk(
                hazards_and_probs['hazards'], exposures,
                vulnerabilities, aal_results
            )
            DatabaseConnection.update_batch_progress(
                self.batch_id, 100, "Completed"
            )

            duration = (datetime.now() - start_time).total_seconds()
            final_result = {
                'status': 'success',
                'latitude': latitude,
                'longitude': longitude,
                'risk_types': risk_types,
                'integrated_risk': integrated_result,
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat()
            }

            # 배치 작업 완료 처리
            DatabaseConnection.complete_batch_job(self.batch_id, final_result)

            logger.info(
                f"Ondemand risk calculation completed: "
                f"batch_id={self.batch_id}, duration={duration:.2f}s"
            )

            return final_result

        except Exception as e:
            # 배치 작업 실패 처리
            error_trace = traceback.format_exc()
            DatabaseConnection.fail_batch_job(
                self.batch_id,
                error_message=str(e),
                error_stack_trace=error_trace
            )

            logger.error(
                f"Ondemand risk calculation failed: "
                f"batch_id={self.batch_id}, error={e}\n{error_trace}"
            )

            raise

    def _fetch_hazard_and_probability(self, latitude: float, longitude: float,
                                      risk_types: List[str]) -> Dict[str, Any]:
        """
        H, P(H) DB 조회

        Args:
            latitude, longitude: 좌표
            risk_types: 리스크 타입 목록

        Returns:
            {
                'hazards': {
                    'extreme_heat': {'hazard_score': 0.75, ...},
                    ...
                },
                'probabilities': {
                    'extreme_heat': {'aal': 0.025, ...},
                    ...
                }
            }
        """
        logger.debug(f"Fetching H and P(H): lat={latitude}, lon={longitude}")

        hazards = DatabaseConnection.fetch_hazard_results(
            latitude, longitude, risk_types
        )
        probabilities = DatabaseConnection.fetch_probability_results(
            latitude, longitude, risk_types
        )

        return {
            'hazards': hazards,
            'probabilities': probabilities
        }

    def _calculate_exposures(self, latitude: float, longitude: float,
                            risk_types: List[str]) -> List[Dict[str, Any]]:
        """
        9개 리스크별 E 계산

        Progress: 10% → 50% (각 리스크당 4.4% 증가)

        Args:
            latitude, longitude: 좌표
            risk_types: 리스크 타입 목록

        Returns:
            E 계산 결과 리스트
        """
        logger.debug(f"Calculating E for {len(risk_types)} risks")

        results = []
        building_info = self._fetch_building_info(latitude, longitude)

        for idx, risk_type in enumerate(risk_types):
            try:
                # ExposureAgent 계산
                e_result = self.exposure_agent.calculate_exposure(
                    latitude, longitude, risk_type, building_info
                )

                results.append({
                    'latitude': latitude,
                    'longitude': longitude,
                    'risk_type': risk_type,
                    **e_result
                })

                # 진행률 업데이트
                progress = 10 + int((idx + 1) / len(risk_types) * 40)
                DatabaseConnection.update_batch_progress(
                    self.batch_id, progress, f"Calculating E for {risk_type}"
                )

                logger.debug(
                    f"E calculated for {risk_type}: "
                    f"score={e_result.get('exposure_score', 0):.3f}"
                )

            except Exception as e:
                logger.error(f"E calculation failed for {risk_type}: {e}")
                # 실패한 리스크는 기본값으로 처리
                results.append({
                    'latitude': latitude,
                    'longitude': longitude,
                    'risk_type': risk_type,
                    'exposure_score': 0.0,
                    'proximity_factor': 0.0,
                    'normalized_asset_value': 0.0
                })

        # DB 저장
        if results:
            DatabaseConnection.save_exposure_results(results)
            logger.info(f"E results saved: {len(results)} records")

        return results

    def _calculate_vulnerabilities(self, latitude: float, longitude: float,
                                  risk_types: List[str]) -> List[Dict[str, Any]]:
        """
        9개 리스크별 V 계산

        Progress: 50% → 80% (각 리스크당 3.3% 증가)

        Args:
            latitude, longitude: 좌표
            risk_types: 리스크 타입 목록

        Returns:
            V 계산 결과 리스트
        """
        logger.debug(f"Calculating V for {len(risk_types)} risks")

        results = []
        building_info = self._fetch_building_info(latitude, longitude)

        for idx, risk_type in enumerate(risk_types):
            try:
                # VulnerabilityAgent 계산
                v_result = self.vulnerability_agent.calculate_vulnerability(
                    risk_type, building_info
                )

                results.append({
                    'latitude': latitude,
                    'longitude': longitude,
                    'risk_type': risk_type,
                    **v_result
                })

                # 진행률 업데이트
                progress = 50 + int((idx + 1) / len(risk_types) * 30)
                DatabaseConnection.update_batch_progress(
                    self.batch_id, progress, f"Calculating V for {risk_type}"
                )

                logger.debug(
                    f"V calculated for {risk_type}: "
                    f"score={v_result.get('vulnerability_score', 0):.1f}, "
                    f"level={v_result.get('vulnerability_level', 'unknown')}"
                )

            except Exception as e:
                logger.error(f"V calculation failed for {risk_type}: {e}")
                # 실패한 리스크는 기본값으로 처리
                results.append({
                    'latitude': latitude,
                    'longitude': longitude,
                    'risk_type': risk_type,
                    'vulnerability_score': 50.0,
                    'vulnerability_level': 'medium',
                    'factors': {}
                })

        # DB 저장
        if results:
            DatabaseConnection.save_vulnerability_results(results)
            logger.info(f"V results saved: {len(results)} records")

        return results

    def _calculate_aal_scaled(self, latitude: float, longitude: float,
                             risk_types: List[str],
                             base_aals: Dict[str, Dict[str, Any]],
                             vulnerabilities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        9개 리스크별 AAL Scaling 계산

        Progress: 80% → 95% (각 리스크당 1.7% 증가)

        Args:
            latitude, longitude: 좌표
            risk_types: 리스크 타입 목록
            base_aals: P(H) 결과 (aal 포함)
            vulnerabilities: V 계산 결과

        Returns:
            AAL 계산 결과 리스트
        """
        logger.debug(f"Calculating AAL for {len(risk_types)} risks")

        results = []

        for idx, risk_type in enumerate(risk_types):
            try:
                # base_aal 조회
                base_aal = base_aals.get(risk_type, {}).get('aal', 0.0)

                # v_score 조회
                v_score = next(
                    (v['vulnerability_score'] for v in vulnerabilities
                     if v['risk_type'] == risk_type),
                    50.0  # 기본값
                )

                # AALScalingAgent 계산
                aal_result = self.aal_agent.calculate_scaled_aal(
                    base_aal, v_score, insurance_rate=0.0
                )

                results.append({
                    'latitude': latitude,
                    'longitude': longitude,
                    'risk_type': risk_type,
                    **aal_result
                })

                # 진행률 업데이트
                progress = 80 + int((idx + 1) / len(risk_types) * 15)
                DatabaseConnection.update_batch_progress(
                    self.batch_id, progress, f"Calculating AAL for {risk_type}"
                )

                logger.debug(
                    f"AAL calculated for {risk_type}: "
                    f"base={base_aal:.4f}, final={aal_result.get('final_aal', 0):.4f}"
                )

            except Exception as e:
                logger.error(f"AAL calculation failed for {risk_type}: {e}")
                # 실패한 리스크는 기본값으로 처리
                results.append({
                    'latitude': latitude,
                    'longitude': longitude,
                    'risk_type': risk_type,
                    'base_aal': 0.0,
                    'vulnerability_scale': 1.0,
                    'final_aal': 0.0,
                    'insurance_rate': 0.0,
                    'expected_loss': None
                })

        # DB 저장
        if results:
            DatabaseConnection.save_aal_scaled_results(results)
            logger.info(f"AAL results saved: {len(results)} records")

        return results

    def _calculate_integrated_risk(self, hazards: Dict[str, Dict[str, Any]],
                                   exposures: List[Dict[str, Any]],
                                   vulnerabilities: List[Dict[str, Any]],
                                   aals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        통합 리스크 계산 (H × E × V)

        Progress: 95% → 100%

        Args:
            hazards: H 결과
            exposures: E 결과
            vulnerabilities: V 결과
            aals: AAL 결과

        Returns:
            통합 리스크 결과
        """
        logger.debug("Calculating integrated risk")

        try:
            # IntegratedRiskAgent 계산
            integrated_result = self.integrated_agent.calculate_integrated_risk(
                hazards, exposures, vulnerabilities, aals
            )

            logger.info(
                f"Integrated risk calculated: "
                f"total_risk={integrated_result.get('total_risk_score', 0):.2f}"
            )

            return integrated_result

        except Exception as e:
            logger.error(f"Integrated risk calculation failed: {e}")
            return {
                'total_risk_score': 0.0,
                'risk_level': 'unknown',
                'risk_breakdown': {}
            }

    def _fetch_building_info(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        건물 정보 조회 (BuildingClient + location_admin 인구 데이터)

        Args:
            latitude, longitude: 좌표

        Returns:
            {
                'building_area': float,
                'building_age': int,
                'structure_type': str,
                'floors_above': int,
                'floors_below': int,
                'has_piloti': bool,
                'has_seismic_design': bool,
                'population_2020': int,
                'population_2050': int,
                ...
            }
        """
        logger.debug(f"Fetching building info: lat={latitude}, lon={longitude}")

        try:
            # 1. 격자 매핑
            grid_result = GridMapper.find_nearest_grid(latitude, longitude)
            if grid_result:
                grid_id, grid_lat, grid_lon = grid_result
            else:
                logger.warning(f"Grid not found for ({latitude}, {longitude})")
                grid_lat, grid_lon = latitude, longitude

            # 2. 건물 정보 조회
            client = BuildingClient()
            buildings = client.get_buildings_in_grid(grid_lat, grid_lon)

            building_data = {}
            if buildings:
                # 가장 가까운 건물 사용
                building = buildings[0]
                building_data = {
                    'building_area': building.get('area_sqm', 1000.0),
                    'building_age': datetime.now().year - building.get('built_year', 2000),
                    'structure_type': building.get('structure_type', 'rc'),
                    'floors_above': building.get('floors', 5),
                    'floors_below': 0,  # TODO: 실제 지하층 정보
                    'has_piloti': False,  # TODO: 실제 필로티 정보
                    'has_seismic_design': building.get('built_year', 2000) >= 2005
                }
            else:
                # 기본값
                building_data = {
                    'building_area': 1000.0,
                    'building_age': 20,
                    'structure_type': 'rc',
                    'floors_above': 5,
                    'floors_below': 0,
                    'has_piloti': False,
                    'has_seismic_design': True
                }

            # 3. 행정구역 인구 데이터 조회
            fetcher = BuildingDataFetcher()
            population_data = fetcher.get_population_data(latitude, longitude)

            # 4. 병합
            result = {**building_data, **population_data}

            logger.debug(f"Building info fetched: {len(result)} fields")

            return result

        except Exception as e:
            logger.error(f"Failed to fetch building info: {e}")
            # 에러 시 기본값 반환
            return {
                'building_area': 1000.0,
                'building_age': 20,
                'structure_type': 'rc',
                'floors_above': 5,
                'floors_below': 0,
                'has_piloti': False,
                'has_seismic_design': True,
                'population_2020': 0,
                'population_2050': 0
            }
