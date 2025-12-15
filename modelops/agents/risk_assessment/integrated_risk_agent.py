"""
Integrated Risk Agent
H, E, V, AAL을 통합 계산하는 Mini-batch 오케스트레이터
"""

from typing import Dict, Any, Callable, Optional, Tuple
import logging
from datetime import datetime

from .aal_scaling_agent import AALScalingAgent

# Hazard Agents
from ..hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent
from ..hazard_calculate.extreme_cold_hscore_agent import ExtremeColdHScoreAgent
from ..hazard_calculate.drought_hscore_agent import DroughtHScoreAgent
from ..hazard_calculate.river_flood_hscore_agent import RiverFloodHScoreAgent
from ..hazard_calculate.urban_flood_hscore_agent import UrbanFloodHScoreAgent
from ..hazard_calculate.sea_level_rise_hscore_agent import SeaLevelRiseHScoreAgent
from ..hazard_calculate.typhoon_hscore_agent import TyphoonHScoreAgent
from ..hazard_calculate.wildfire_hscore_agent import WildfireHScoreAgent
from ..hazard_calculate.water_stress_hscore_agent import WaterStressHScoreAgent

# Exposure Agents
from ..exposure_calculate.river_flood_exposure_agent import RiverFloodExposureAgent
from ..exposure_calculate.extreme_heat_exposure_agent import ExtremeHeatExposureAgent
from ..exposure_calculate.extreme_cold_exposure_agent import ExtremeColdExposureAgent
from ..exposure_calculate.urban_flood_exposure_agent import UrbanFloodExposureAgent
from ..exposure_calculate.drought_exposure_agent import DroughtExposureAgent
from ..exposure_calculate.typhoon_exposure_agent import TyphoonExposureAgent
from ..exposure_calculate.sea_level_rise_exposure_agent import SeaLevelRiseExposureAgent
from ..exposure_calculate.wildfire_exposure_agent import WildfireExposureAgent
from ..exposure_calculate.water_stress_exposure_agent import WaterStressExposureAgent

# Vulnerability Agents
from ..vulnerability_calculate.extreme_heat_vulnerability_agent import ExtremeHeatVulnerabilityAgent
from ..vulnerability_calculate.extreme_cold_vulnerability_agent import ExtremeColdVulnerabilityAgent
from ..vulnerability_calculate.drought_vulnerability_agent import DroughtVulnerabilityAgent
from ..vulnerability_calculate.river_flood_vulnerability_agent import RiverFloodVulnerabilityAgent
from ..vulnerability_calculate.urban_flood_vulnerability_agent import UrbanFloodVulnerabilityAgent
from ..vulnerability_calculate.sea_level_rise_vulnerability_agent import SeaLevelRiseVulnerabilityAgent
from ..vulnerability_calculate.typhoon_vulnerability_agent import TyphoonVulnerabilityAgent
from ..vulnerability_calculate.wildfire_vulnerability_agent import WildfireVulnerabilityAgent
from ..vulnerability_calculate.water_stress_vulnerability_agent import WaterStressVulnerabilityAgent

# HazardDataCollector
from ...utils.hazard_data_collector import HazardDataCollector
from ...data_loaders.long_term_mapper import LongTermDataMapper

logger = logging.getLogger(__name__)


class IntegratedRiskAgent:
    """H, E, V, AAL을 통합 계산하는 Agent (Mini-batch 처리)"""

    def __init__(self, scenario='SSP245', target_year: Any = 2030, time_scope='yearly', database_connection=None):
        """
        IntegratedRiskAgent 초기화

        Args:
            scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
            target_year: 분석 연도 (int or "2030s" string)
            time_scope: 분석 범위 ('yearly' or 'decadal')
            database_connection: DatabaseConnection 클래스 (주입)
        """
        self.scenario = scenario
        self.time_scope = time_scope

        # Store the original target_year value for saving (can be int or '2030s' string)
        self.target_year = target_year 

        # Determine the integer year/decade for data fetching/processing
        if isinstance(target_year, str) and target_year.endswith('s'):
            try:
                self._int_year_for_data_fetch = int(target_year.replace('s', ''))
                self.time_scope = 'decadal' # Force decadal if 's' suffix is present
            except ValueError:
                logger.warning(f"Invalid target_year string format: {target_year}. Defaulting to 2030 and 'yearly' scope.")
                self._int_year_for_data_fetch = 2030
                self.time_scope = 'yearly'
        else:
            self._int_year_for_data_fetch = int(target_year)
            # If target_year is int, time_scope comes from input (default 'yearly')

        # HazardDataCollector 초기화 (uses integer year)
        self.hazard_data_collector = HazardDataCollector(
            scenario=scenario,
            target_year=self._int_year_for_data_fetch 
        )

        # AAL Agent
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

        # Hazard Agent 매핑
        self.hazard_agents = {
            'extreme_heat': ExtremeHeatHScoreAgent(),
            'extreme_cold': ExtremeColdHScoreAgent(),
            'drought': DroughtHScoreAgent(),
            'river_flood': RiverFloodHScoreAgent(),
            'urban_flood': UrbanFloodHScoreAgent(),
            'sea_level_rise': SeaLevelRiseHScoreAgent(),
            'typhoon': TyphoonHScoreAgent(),
            'wildfire': WildfireHScoreAgent(),
            'water_stress': WaterStressHScoreAgent()
        }

        # Exposure Agent 매핑
        self.exposure_agents = {
            'extreme_heat': ExtremeHeatExposureAgent(),
            'extreme_cold': ExtremeColdExposureAgent(),
            'drought': DroughtExposureAgent(),
            'river_flood': RiverFloodExposureAgent(),
            'urban_flood': UrbanFloodExposureAgent(),
            'sea_level_rise': SeaLevelRiseExposureAgent(),
            'typhoon': TyphoonExposureAgent(),
            'wildfire': WildfireExposureAgent(),
            'water_stress': WaterStressExposureAgent()
        }

        # Vulnerability Agent 매핑
        self.vulnerability_agents = {
            'extreme_heat': ExtremeHeatVulnerabilityAgent(),
            'extreme_cold': ExtremeColdVulnerabilityAgent(),
            'drought': DroughtVulnerabilityAgent(),
            'river_flood': RiverFloodVulnerabilityAgent(),
            'urban_flood': UrbanFloodVulnerabilityAgent(),
            'sea_level_rise': SeaLevelRiseVulnerabilityAgent(),
            'typhoon': TyphoonVulnerabilityAgent(),
            'wildfire': WildfireVulnerabilityAgent(),
            'water_stress': WaterStressVulnerabilityAgent()
        }

        # DatabaseConnection 주입 (나중에 설정)
        self.db = database_connection # This will be DatabaseConnection from connection.py if default or set externally

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
        Mini-batch로 9개 리스크 순차 계산 (H × E × V)

        Args:
            latitude: 위도
            longitude: 경도
            progress_callback: 진행상황 콜백 함수(current, total, risk_type)

        Returns:
            {
                'hazard': {risk_type: {...}},
                'exposure': {risk_type: {...}},
                'vulnerability': {risk_type: {...}},
                'integrated_risk': {risk_type: {...}},  # H × E × V
                'aal_scaled': {risk_type: {...}},
                'summary': {...},
                'metadata': {...}
            }
        """
        start_time = datetime.now()
        logger.info(f"통합 리스크 계산 시작: ({latitude}, {longitude})")
        logger.info(f"시나리오: {self.scenario}, 분석 연도: {self.target_year}, 범위: {self.time_scope}")

        try:
            # 1. DB에서 기본 데이터 조회 (선택적)
            asset_info = self._fetch_asset_info(latitude, longitude)
            base_aals = self._fetch_base_aals(latitude, longitude)

            # 결과 저장소
            results = {
                'hazard': {},
                'exposure': {},
                'vulnerability': {},
                'integrated_risk': {},  # H × E × V 추가
                'aal_scaled': {}
            }

            # 2. Mini-batch 처리 (9개 리스크)
            total_risks = len(self.risk_types)

            # 장기(decadal) 분석인 경우 한 번에 데이터 조회
            long_term_data = None
            if self.time_scope == 'decadal':
                try:
                    from ...database.connection_long import DatabaseConnectionLong
                    # decade 식별 (예: 2030 -> 2030s)
                    decade = (self.target_year // 10) * 10
                    long_term_data = DatabaseConnectionLong.fetch_climate_data_by_decade(
                        latitude, longitude, decade, self.scenario.lower() if self.scenario.startswith('SSP') else 'ssp2'
                    )
                except Exception as e:
                    logger.error(f"장기 데이터 조회 실패: {e}")
                    long_term_data = {}

            for i, risk_type in enumerate(self.risk_types, 1):
                logger.info(f"[{i}/{total_risks}] {risk_type} 계산 중...")

                # Step 1: 데이터 수집 (Time Scope 분기)
                collected_data = {}
                try:
                    if self.time_scope == 'decadal' and long_term_data:
                        base_info = {
                            'latitude': latitude,
                            'longitude': longitude,
                            'scenario': self.scenario,
                            'target_year': self.target_year,
                            'time_scope': self.time_scope,
                            'building_data': self._fetch_building_info(latitude, longitude)
                        }
                        collected_data = LongTermDataMapper.map_data(
                            risk_type, long_term_data, base_info
                        )
                    else:
                        collected_data = self.hazard_data_collector.collect_data(
                            lat=latitude,
                            lon=longitude,
                            risk_type=risk_type
                        )
                    logger.debug(f"{risk_type}: 데이터 수집 완료")
                except Exception as e:
                    logger.error(f"{risk_type}: 데이터 수집 실패 - {e}")
                    collected_data = {
                        'latitude': latitude,
                        'longitude': longitude
                    }

                # Step 2: H 계산
                h_result = self._calculate_hazard(risk_type, collected_data)
                results['hazard'][risk_type] = h_result

                # Step 3: E 계산 (리스크별 개별 에이전트 사용)
                e_result = self._calculate_exposure(risk_type, collected_data)
                results['exposure'][risk_type] = e_result

                # Step 4: V 계산 (리스크별 개별 에이전트 사용)
                v_result = self._calculate_vulnerability(risk_type, e_result)
                results['vulnerability'][risk_type] = v_result

                # Step 5: H × E × V 통합 리스크 계산
                integrated_risk = self._calculate_integrated_risk(
                    risk_type, h_result, e_result, v_result
                )
                results['integrated_risk'][risk_type] = integrated_risk

                # Step 6: AAL 스케일링 (기존 로직 유지)
                base_aal = base_aals.get(risk_type, 0.01)
                v_score = v_result.get('vulnerability_score', 50.0)
                insurance_rate = asset_info.get('insurance_coverage_rate', 0.0)
                asset_value = asset_info.get('total_asset_value')

                aal_result = self.aal_scaling_agent.scale_aal(
                    base_aal=base_aal,
                    vulnerability_score=v_score,
                    insurance_rate=insurance_rate,
                    asset_value=asset_value
                )

                # AAL 등급 분류
                final_aal = round(aal_result.get('final_aal', 0.0), 2)
                grade = self.aal_scaling_agent.classify_aal_grade(final_aal)
                aal_result['grade'] = grade
                aal_result['final_aal'] = final_aal

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

                # DB 저장 로직 제거 (Batch 또는 API 레벨에서 처리)
                # self._save_results(...) 삭제됨

            # 3. 요약 통계 계산
            summary = self._calculate_summary(results)

            # 4. 메타데이터 추가
            end_time = datetime.now()
            metadata = {
                'latitude': latitude,
                'longitude': longitude,
                'scenario': self.scenario,
                'target_year': self.target_year,
                'time_scope': self.time_scope,
                'calculation_time': (end_time - start_time).total_seconds(),
                'calculated_at': end_time.isoformat(),
                'total_risks_processed': total_risks
            }

            logger.info(f"통합 리스크 계산 완료: {metadata['calculation_time']:.2f}초")

            return {
                'hazard': results['hazard'],
                'exposure': results['exposure'],
                'vulnerability': results['vulnerability'],
                'integrated_risk': results['integrated_risk'],
                'aal_scaled': results['aal_scaled'],
                'summary': summary,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"통합 리스크 계산 실패: {e}", exc_info=True)
            raise



    def _calculate_hazard(self, risk_type: str, collected_data: Dict) -> Dict:
        """
        HazardHScoreAgent를 호출하여 H 점수 계산

        Args:
            risk_type: 리스크 유형 (extreme_heat, river_flood 등)
            collected_data: HazardDataCollector가 수집한 데이터

        Returns:
            {
                'hazard_score': float,           # 0-100 점수
                'hazard_score_normalized': float, # 0-1 정규화
                'hazard_level': str,             # Very High/High/Medium/Low/Very Low
                'raw_data': Dict                 # 원본 계산 결과
            }
        """
        try:
            agent = self.hazard_agents.get(risk_type)
            if not agent:
                logger.warning(f"Unknown risk_type: {risk_type}, 기본값 사용")
                return {
                    'hazard_score': 0.0,
                    'hazard_score_normalized': 0.0,
                    'hazard_level': 'Very Low',
                    'raw_data': {},
                    'error': f'Unknown risk_type: {risk_type}'
                }

            # HazardAgent 호출
            h_result = agent.calculate_hazard_score(collected_data)

            return {
                'hazard_score': h_result.get('hazard_score_100', 0.0),  # 0-100
                'hazard_score_normalized': h_result.get('hazard_score', 0.0),  # 0-1
                'hazard_level': h_result.get('hazard_level', 'Very Low'),
                'raw_data': h_result
            }

        except Exception as e:
            logger.error(f"Hazard 계산 실패 ({risk_type}): {e}")
            return {
                'hazard_score': 0.0,
                'hazard_score_normalized': 0.0,
                'hazard_level': 'Very Low',
                'raw_data': {},
                'error': str(e)
            }

    def _calculate_exposure(self, risk_type: str, collected_data: Dict) -> Dict:
        """
        리스크별 ExposureAgent를 호출하여 E 점수 계산

        Args:
            risk_type: 리스크 유형
            collected_data: HazardDataCollector가 수집한 데이터

        Returns:
            {
                'exposure_score': float,  # 0-100 점수
                'raw_data': Dict          # 원본 계산 결과
            }
        """
        try:
            agent = self.exposure_agents.get(risk_type)
            if not agent:
                logger.warning(f"Unknown risk_type for exposure: {risk_type}, 기본값 사용")
                return {
                    'exposure_score': 0.0,
                    'raw_data': {},
                    'error': f'Unknown risk_type: {risk_type}'
                }

            # collected_data에서 필요한 정보 추출
            building_data = collected_data.get('building_data', {})
            spatial_data = collected_data.get('spatial_data', {})
            latitude = collected_data.get('latitude', 0.0)
            longitude = collected_data.get('longitude', 0.0)

            # ExposureAgent 호출
            e_result = agent.calculate_exposure(
                building_data=building_data,
                spatial_data=spatial_data,
                latitude=latitude,
                longitude=longitude
            )

            # score 추출 (각 에이전트의 반환 형식에 따라)
            exposure_score = e_result.get('score', 0.0)

            return {
                'exposure_score': exposure_score,
                'raw_data': e_result
            }

        except Exception as e:
            logger.error(f"Exposure 계산 실패 ({risk_type}): {e}")
            return {
                'exposure_score': 0.0,
                'raw_data': {},
                'error': str(e)
            }

    def _calculate_vulnerability(self, risk_type: str, exposure_data: Dict) -> Dict:
        """
        리스크별 VulnerabilityAgent를 호출하여 V 점수 계산

        Args:
            risk_type: 리스크 유형
            exposure_data: Exposure 계산 결과 (building 정보 포함)

        Returns:
            {
                'vulnerability_score': float,  # 0-100 점수
                'vulnerability_level': str,    # very_high/high/medium/low/very_low
                'factors': Dict,               # 취약성 요인
                'raw_data': Dict               # 원본 계산 결과
            }
        """
        try:
            agent = self.vulnerability_agents.get(risk_type)
            if not agent:
                logger.warning(f"Unknown risk_type for vulnerability: {risk_type}, 기본값 사용")
                return {
                    'vulnerability_score': 50.0,
                    'vulnerability_level': 'medium',
                    'factors': {},
                    'raw_data': {},
                    'error': f'Unknown risk_type: {risk_type}'
                }

            # VulnerabilityAgent 호출 (exposure_data 전체 전달)
            v_result = agent.calculate_vulnerability(exposure_data.get('raw_data', {}))

            return {
                'vulnerability_score': v_result.get('score', 50.0),
                'vulnerability_level': v_result.get('level', 'medium'),
                'factors': v_result.get('factors', {}),
                'raw_data': v_result
            }

        except Exception as e:
            logger.error(f"Vulnerability 계산 실패 ({risk_type}): {e}")
            return {
                'vulnerability_score': 50.0,
                'vulnerability_level': 'medium',
                'factors': {},
                'raw_data': {},
                'error': str(e)
            }

    def _calculate_integrated_risk(
        self,
        risk_type: str,
        h_result: Dict,
        e_result: Dict,
        v_result: Dict
    ) -> Dict:
        """
        H × E × V 곱셈으로 통합 리스크 점수 계산

        원본 공식 (physical_risk_module_core_merge):
        Risk = (H × E × V) / 10,000

        Args:
            risk_type: 리스크 유형
            h_result: Hazard 계산 결과
            e_result: Exposure 계산 결과
            v_result: Vulnerability 계산 결과

        Returns:
            {
                'h_score': float,                  # 0-100
                'e_score': float,                  # 0-100
                'v_score': float,                  # 0-100
                'integrated_risk_score': float,    # 0-100 (H×E×V 정규화)
                'risk_level': str,                 # Very High/High/Medium/Low/Very Low
                'calculation_method': str,         # 'H × E × V / 10000'
                'formula': str                     # 계산식 표시
            }
        """
        # 1. 각 점수 추출 (0-100 스케일)
        h_score = h_result.get('hazard_score', 0.0)
        e_score = e_result.get('exposure_score', 0.0)
        v_score = v_result.get('vulnerability_score', 0.0)

        # 2. H × E × V 계산 (정규화)
        # 각 점수가 0-100이므로, 최대값은 100×100×100 = 1,000,000
        # /10000 하면 0-100 범위로 정규화됨
        raw_risk = (h_score * e_score * v_score) / 10000.0  # 0-100 범위

        # 3. 위험도 등급 분류
        risk_level = self._classify_risk_level(raw_risk)

        return {
            'h_score': round(h_score, 2),
            'e_score': round(e_score, 2),
            'v_score': round(v_score, 2),
            'integrated_risk_score': round(raw_risk, 2),
            'risk_level': risk_level,
            'calculation_method': 'H × E × V / 10000',
            'formula': f'{h_score:.2f} × {e_score:.2f} × {v_score:.2f} / 10000 = {raw_risk:.2f}'
        }

    def _classify_risk_level(self, score: float) -> str:
        """
        리스크 점수를 등급으로 분류

        Args:
            score: 0-100 리스크 점수

        Returns:
            'Very High', 'High', 'Medium', 'Low', 'Very Low'
        """
        if score >= 80:
            return 'Very High'
        elif score >= 60:
            return 'High'
        elif score >= 40:
            return 'Medium'
        elif score >= 20:
            return 'Low'
        else:
            return 'Very Low'

    def _extract_exposure_fields(
        self,
        e_result: Dict,
        risk_type: str
    ) -> Tuple[float, float, Optional[float]]:
        """
        ExposureAgent의 nested 결과에서 DB 저장용 필드 추출

        Args:
            e_result: ExposureAgent.calculate_exposure() 결과
            risk_type: 리스크 유형

        Returns:
            (exposure_score, proximity_factor, normalized_asset_value)
        """
        # Risk type별 nested path 매핑
        exposure_mappings = {
            'river_flood': ('flood_exposure', 'score', 'distance_to_river_m'),
            'urban_flood': ('urban_flood_exposure', 'score', None),
            'extreme_heat': ('heat_exposure', 'urban_heat_island', None),
            'drought': ('drought_exposure', 'score', None),
            'typhoon': ('typhoon_exposure', 'coastal_distance_score', 'distance_to_coast_m'),
            'sea_level_rise': ('sea_level_rise_exposure', 'coastal_distance_score', 'distance_to_coast_m'),
            'wildfire': ('wildfire_exposure', 'score', 'distance_to_forest_m'),
            'extreme_cold': (None, None, None),  # Default
            'water_stress': (None, None, None)   # Default
        }

        section, score_field, distance_field = exposure_mappings.get(
            risk_type,
            (None, None, None)
        )

        # 1. exposure_score 추출
        if section and score_field:
            exposure_data = e_result.get(section, {})
            exposure_score = exposure_data.get(score_field, 0.0)
        else:
            exposure_score = 0.0

        # 2. proximity_factor 계산
        if distance_field and section:
            distance_m = e_result.get(section, {}).get(distance_field, 10000.0)
            # 거리 기반 근접도: 가까울수록 높음 (0-1 범위)
            proximity_factor = max(0.0, 1.0 - (distance_m / 10000.0))
        else:
            proximity_factor = 0.0

        # 3. normalized_asset_value 
        normalized_asset_value = None # 현재는 None으로 설정

        return exposure_score, proximity_factor, normalized_asset_value

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
        base_aal 조회 (probability_results.aal)
        target_year를 고려하여 정확한 연도의 AAL을 조회
        """
        if self.db is None:
            logger.warning("DB 연결 없음 - 기본 AAL 값 사용")
            return {risk_type: 0.01 for risk_type in self.risk_types}

        try:
            # DatabaseConnection의 get_connection을 직접 사용하여 쿼리 수행
            # (기존 fetch_base_aals는 target_year 필터링이 없음)
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT risk_type, aal AS base_aal
                    FROM probability_results
                    WHERE latitude = %s 
                      AND longitude = %s
                      AND target_year = %s
                """, (latitude, longitude, self.target_year))
                
                base_aals = {row['risk_type']: row['base_aal'] for row in cursor.fetchall()}
                
                # 데이터가 없으면 로그 남기고 기본값(빈 딕셔너리 리턴 후 메인 로직에서 처리 or 여기서 default)
                if not base_aals:
                    logger.debug(f" base AAL 데이터 없음: ({latitude}, {longitude}, {self.target_year})")
                    # 일부 리스크만 있을 수 있으므로 반환된 것만 리턴
                
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



    def _calculate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """요약 통계 계산 (H, E, V, Integrated Risk 포함)"""
        # 각 리스크별 등급 분류
        risk_breakdown = {}
        for risk_type in self.risk_types:
            risk_breakdown[risk_type] = {
                'hazard_score': results['hazard'].get(risk_type, {}).get('hazard_score', 0.0),
                'exposure_score': results['exposure'].get(risk_type, {}).get('exposure_score', 0.0),
                'vulnerability_score': results['vulnerability'].get(risk_type, {}).get('vulnerability_score', 0.0),
                'integrated_risk_score': results['integrated_risk'].get(risk_type, {}).get('integrated_risk_score', 0.0),
                'risk_level': results['integrated_risk'].get(risk_type, {}).get('risk_level', 'Very Low'),
                'aal_grade': results['aal_scaled'].get(risk_type, {}).get('grade', '-')
            }

        # 평균 점수 계산
        h_scores = [h.get('hazard_score', 0.0) for h in results['hazard'].values()]
        e_scores = [e.get('exposure_score', 0.0) for e in results['exposure'].values()]
        v_scores = [v.get('vulnerability_score', 0.0) for v in results['vulnerability'].values()]
        risk_scores = [r.get('integrated_risk_score', 0.0) for r in results['integrated_risk'].values()]

        avg_hazard = sum(h_scores) / len(h_scores) if h_scores else 0.0
        avg_exposure = sum(e_scores) / len(e_scores) if e_scores else 0.0
        avg_vulnerability = sum(v_scores) / len(v_scores) if v_scores else 0.0
        avg_integrated_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

        # 최고 통합 리스크 식별 (H×E×V 기준)
        highest_integrated_risk = max(
            results['integrated_risk'].items(),
            key=lambda x: x[1].get('integrated_risk_score', 0.0)
        ) if results['integrated_risk'] else (None, {})

        # 최고 AAL 리스크 식별
        highest_aal_risk = max(
            results['aal_scaled'].items(),
            key=lambda x: x[1].get('final_aal', 0.0)
        ) if results['aal_scaled'] else (None, {})

        # Top 3 리스크 (통합 리스크 점수 기준)
        top_3_risks = sorted(
            results['integrated_risk'].items(),
            key=lambda x: x[1].get('integrated_risk_score', 0.0),
            reverse=True
        )[:3]

        return {
            'average_hazard': round(avg_hazard, 2),
            'average_exposure': round(avg_exposure, 2),
            'average_vulnerability': round(avg_vulnerability, 2),
            'average_integrated_risk': round(avg_integrated_risk, 2),
            'highest_integrated_risk': {
                'risk_type': highest_integrated_risk[0],
                'integrated_risk_score': highest_integrated_risk[1].get('integrated_risk_score', 0.0),
                'risk_level': highest_integrated_risk[1].get('risk_level', 'Very Low')
            } if highest_integrated_risk[0] else None,
            'highest_aal_risk': {
                'risk_type': highest_aal_risk[0],
                'final_aal': highest_aal_risk[1].get('final_aal', 0.0),
                'grade': highest_aal_risk[1].get('grade', '-')
            } if highest_aal_risk[0] else None,
            'top_3_risks': [
                {
                    'rank': i + 1,
                    'risk_type': risk_type,
                    'integrated_risk_score': risk_data.get('integrated_risk_score', 0.0),
                    'risk_level': risk_data.get('risk_level', 'Very Low')
                }
                for i, (risk_type, risk_data) in enumerate(top_3_risks)
            ],
            'risk_breakdown': risk_breakdown
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
