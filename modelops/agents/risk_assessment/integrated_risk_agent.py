"""
Integrated Risk Agent
E, V, AAL을 통합 계산하는 Mini-batch 오케스트레이터
"""

from typing import Dict, Any, Callable, Optional
import logging
from datetime import datetime

from .exposure_agent import ExposureAgent
from .vulnerability_agent import VulnerabilityAgent
from .aal_scaling_agent import AALScalingAgent

logger = logging.getLogger(__name__)


class IntegratedRiskAgent:
    """E, V, AAL을 통합 계산하는 Agent (Mini-batch 처리)"""

    def __init__(self, database_connection=None):
        """
        IntegratedRiskAgent 초기화

        Args:
            database_connection: DatabaseConnection 클래스 (주입)
        """
        self.exposure_agent = ExposureAgent()
        self.vulnerability_agent = VulnerabilityAgent()
        self.aal_scaling_agent = AALScalingAgent()

        # 9개 리스크 타입
        self.risk_types = [
            'extreme_heat',
            'extreme_cold',
            'wildfire',
            'drought',
            'water_stress',
            'sea_level_rise',
            'river_flood',
            'urban_flood',
            'typhoon'
        ]

        # DatabaseConnection 주입 (나중에 설정)
        self.db = database_connection

    def set_database_connection(self, database_connection):
        """DatabaseConnection 설정"""
        self.db = database_connection

    def calculate_all_risks(
        self,
        latitude: float,
        longitude: float,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Mini-batch로 9개 리스크 순차 계산

        Args:
            latitude: 위도
            longitude: 경도
            progress_callback: 진행상황 콜백 함수(current, total, risk_type)

        Returns:
            {
                'exposure': {risk_type: {...}},
                'vulnerability': {risk_type: {...}},
                'aal_scaled': {risk_type: {...}},
                'summary': {...},
                'metadata': {...}
            }
        """
        start_time = datetime.now()
        logger.info(f"통합 리스크 계산 시작: ({latitude}, {longitude})")

        try:
            # 1. 필요한 데이터 수집
            building_info = self._fetch_building_info(latitude, longitude)
            asset_info = self._fetch_asset_info(latitude, longitude)
            base_aals = self._fetch_base_aals(latitude, longitude)
            infrastructure_info = self._fetch_infrastructure_info(latitude, longitude)

            # 결과 저장소
            results = {
                'exposure': {},
                'vulnerability': {},
                'aal_scaled': {}
            }

            # 2. Mini-batch 처리 (9개 리스크)
            total_risks = len(self.risk_types)

            for i, risk_type in enumerate(self.risk_types, 1):
                logger.info(f"[{i}/{total_risks}] {risk_type} 계산 중...")

                # E 계산
                e_result = self.exposure_agent.calculate_exposure(
                    latitude=latitude,
                    longitude=longitude,
                    risk_type=risk_type,
                    building_info=building_info,
                    asset_info=asset_info
                )
                results['exposure'][risk_type] = e_result

                # V 계산
                v_result = self.vulnerability_agent.calculate_vulnerability(
                    risk_type=risk_type,
                    building_info=building_info,
                    infrastructure_info=infrastructure_info
                )
                results['vulnerability'][risk_type] = v_result

                # AAL 스케일링
                base_aal = base_aals.get(risk_type, 0.0)
                v_score = v_result.get('vulnerability_score', 50.0)
                insurance_rate = asset_info.get('insurance_coverage_rate', 0.0)
                asset_value = asset_info.get('total_asset_value')

                aal_result = self.aal_scaling_agent.scale_aal(
                    base_aal=base_aal,
                    vulnerability_score=v_score,
                    insurance_rate=insurance_rate,
                    asset_value=asset_value
                )
                results['aal_scaled'][risk_type] = aal_result

                # 진행상황 콜백
                if progress_callback:
                    try:
                        progress_callback(
                            current=i,
                            total=total_risks,
                            risk_type=risk_type
                        )
                    except Exception as e:
                        logger.warning(f"진행상황 콜백 실패: {e}")

                # DB 저장 (각 리스크 계산 후 즉시)
                self._save_results(
                    latitude=latitude,
                    longitude=longitude,
                    risk_type=risk_type,
                    e_result=e_result,
                    v_result=v_result,
                    aal_result=aal_result
                )

            # 3. 요약 통계 계산
            summary = self._calculate_summary(results)

            # 4. 메타데이터 추가
            end_time = datetime.now()
            metadata = {
                'latitude': latitude,
                'longitude': longitude,
                'calculation_time': (end_time - start_time).total_seconds(),
                'calculated_at': end_time.isoformat(),
                'total_risks_processed': total_risks,
                'building_info': {
                    'building_age': building_info.get('building_age'),
                    'structure': building_info.get('structure'),
                    'main_purpose': building_info.get('main_purpose')
                }
            }

            logger.info(f"통합 리스크 계산 완료: {metadata['calculation_time']:.2f}초")

            return {
                'exposure': results['exposure'],
                'vulnerability': results['vulnerability'],
                'aal_scaled': results['aal_scaled'],
                'summary': summary,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"통합 리스크 계산 실패: {e}", exc_info=True)
            raise

    def _fetch_building_info(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        건물 정보 조회 (격자 → 가장 가까운 건물 매칭)

        DB 연결이 없으면 기본값 반환
        """
        if self.db is None:
            logger.warning("DB 연결 없음 - 기본 건물 정보 사용")
            return self._get_default_building_info()

        try:
            building_info = self.db.fetch_building_info(latitude, longitude)
            if not building_info:
                logger.warning(f"건물 정보 없음: ({latitude}, {longitude}) - 기본값 사용")
                return self._get_default_building_info()
            return building_info

        except Exception as e:
            logger.error(f"건물 정보 조회 실패: {e}")
            return self._get_default_building_info()

    def _fetch_asset_info(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        자산 정보 조회

        현재는 기본값 반환 (보험율 0.0, 자산값 None)
        """
        return {
            'total_asset_value': None,  # AAL은 %이므로 불필요
            'insurance_coverage_rate': 0.0,  # 보험 없음
            'floor_area': None
        }

    def _fetch_base_aals(self, latitude: float, longitude: float) -> Dict[str, float]:
        """
        base_aal 조회 (probability_results.probability)

        DB 연결이 없으면 빈 딕셔너리 반환
        """
        if self.db is None:
            logger.warning("DB 연결 없음 - 기본 AAL 값 사용")
            return {risk_type: 0.01 for risk_type in self.risk_types}

        try:
            base_aals = self.db.fetch_base_aals(latitude, longitude)
            if not base_aals:
                logger.warning(f"Base AAL 없음: ({latitude}, {longitude}) - 기본값 사용")
                return {risk_type: 0.01 for risk_type in self.risk_types}
            return base_aals

        except Exception as e:
            logger.error(f"Base AAL 조회 실패: {e}")
            return {risk_type: 0.01 for risk_type in self.risk_types}

    def _fetch_infrastructure_info(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        인프라 정보 조회 (필로티, 내진설계, 해발고도 등)

        현재는 기본값 반환
        """
        return {
            'has_piloti': False,
            'has_seismic_design': False,
            'in_flood_zone': False,
            'water_supply_available': True,
            'fire_access': True,
            'elevation': 50.0  # 기본 해발고도 50m
        }

    def _save_results(
        self,
        latitude: float,
        longitude: float,
        risk_type: str,
        e_result: Dict[str, Any],
        v_result: Dict[str, Any],
        aal_result: Dict[str, Any]
    ) -> None:
        """각 리스크 계산 결과 DB 저장"""
        if self.db is None:
            logger.warning("DB 연결 없음 - 결과 저장 건너뜀")
            return

        try:
            # Exposure 저장
            self.db.save_exposure_results([{
                'latitude': latitude,
                'longitude': longitude,
                'risk_type': risk_type,
                'exposure_score': e_result.get('exposure_score', 0.0),
                'proximity_factor': e_result.get('proximity_factor', 0.0)
            }])

            # Vulnerability 저장
            self.db.save_vulnerability_results([{
                'latitude': latitude,
                'longitude': longitude,
                'risk_type': risk_type,
                'vulnerability_score': v_result.get('vulnerability_score', 0.0),
                'vulnerability_level': v_result.get('vulnerability_level', 'medium'),
                'factors': v_result.get('factors', {})
            }])

            # AAL 저장
            self.db.save_aal_scaled_results([{
                'latitude': latitude,
                'longitude': longitude,
                'risk_type': risk_type,
                'base_aal': aal_result.get('base_aal', 0.0),
                'vulnerability_scale': aal_result.get('vulnerability_scale', 1.0),
                'final_aal': aal_result.get('final_aal', 0.0),
                'insurance_rate': aal_result.get('insurance_rate', 0.0),
                'expected_loss': aal_result.get('expected_loss')
            }])

        except Exception as e:
            logger.error(f"결과 저장 실패 ({risk_type}): {e}")

    def _calculate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """요약 통계 계산"""
        # 총 AAL 계산
        total_aal_summary = self.aal_scaling_agent.calculate_total_aal(
            results['aal_scaled']
        )

        # 평균 취약성 계산
        v_scores = [
            v['vulnerability_score']
            for v in results['vulnerability'].values()
        ]
        avg_vulnerability = sum(v_scores) / len(v_scores) if v_scores else 0.0

        # 평균 노출도 계산
        e_scores = [
            e['exposure_score']
            for e in results['exposure'].values()
        ]
        avg_exposure = sum(e_scores) / len(e_scores) if e_scores else 0.0

        # 최고 리스크 식별
        highest_aal_risk = max(
            results['aal_scaled'].items(),
            key=lambda x: x[1].get('final_aal', 0.0)
        )

        highest_v_risk = max(
            results['vulnerability'].items(),
            key=lambda x: x[1].get('vulnerability_score', 0.0)
        )

        return {
            'total_final_aal': total_aal_summary['total_final_aal'],
            'total_expected_loss': total_aal_summary['total_expected_loss'],
            'average_vulnerability': round(avg_vulnerability, 2),
            'average_exposure': round(avg_exposure, 4),
            'highest_aal_risk': {
                'risk_type': highest_aal_risk[0],
                'final_aal': highest_aal_risk[1].get('final_aal', 0.0)
            },
            'highest_vulnerability_risk': {
                'risk_type': highest_v_risk[0],
                'vulnerability_score': highest_v_risk[1].get('vulnerability_score', 0.0)
            },
            'risk_breakdown': total_aal_summary['risk_breakdown']
        }

    def _get_default_building_info(self) -> Dict[str, Any]:
        """기본 건물 정보 반환"""
        return {
            'building_age': 20,
            'structure': '철근콘크리트',
            'main_purpose': '주거시설',
            'floors_below': 0,
            'floors_above': 5,
            'total_area': 1000.0,
            'arch_area': 200.0
        }
