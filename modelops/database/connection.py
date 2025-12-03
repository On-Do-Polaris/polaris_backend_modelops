import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any
from ..config.settings import settings


class DatabaseConnection:
    """PostgreSQL 데이터베이스 연결 관리"""

    @staticmethod
    def get_connection_string() -> str:
        """데이터베이스 연결 문자열 생성"""
        return (
            f"host={settings.database_host} "
            f"port={settings.database_port} "
            f"dbname={settings.database_name} "
            f"user={settings.database_user} "
            f"password={settings.database_password}"
        )

    @staticmethod
    @contextmanager
    def get_connection():
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = psycopg2.connect(
            DatabaseConnection.get_connection_string(),
            cursor_factory=RealDictCursor
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def fetch_grid_coordinates() -> List[Dict[str, float]]:
        """모든 격자 좌표 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT latitude, longitude
                FROM climate_data
                ORDER BY latitude, longitude
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def fetch_climate_data(latitude: float, longitude: float, risk_type: str = None,
                          ssp_scenario: str = 'ssp2') -> Dict[str, Any]:
        """
        특정 격자의 기후 데이터 조회 (전처리 레이어 적용)

        Args:
            latitude: 격자 위도
            longitude: 격자 경도
            risk_type: 리스크 타입 (extreme_heat, extreme_cold 등)
            ssp_scenario: SSP 시나리오 (ssp1, ssp2, ssp3, ssp5)

        Returns:
            리스크별 파생 지표 딕셔너리
        """
        # 1. 원시 데이터 조회
        raw_data = DatabaseConnection._fetch_raw_climate_data(latitude, longitude, ssp_scenario)

        # 2. 리스크 타입이 지정되지 않으면 원시 데이터 반환
        if not risk_type:
            return {'climate_data': raw_data}

        # 3. 전처리 레이어 호출
        from ..preprocessing.climate_indicators import ClimateIndicatorCalculator
        from ..preprocessing.baseline_splitter import BaselineSplitter

        calculator = ClimateIndicatorCalculator(raw_data)
        splitter = BaselineSplitter(start_year=2021, end_year=2100)

        # 4. 리스크별 필요 지표 계산
        result = {'climate_data': {}}

        if risk_type == 'extreme_heat':
            result['climate_data'] = calculator.get_heatwave_indicators()

        elif risk_type == 'extreme_cold':
            result['climate_data'] = calculator.get_coldwave_indicators()

        elif risk_type == 'wildfire':
            result['climate_data'] = calculator.get_wildfire_indicators()

        elif risk_type == 'river_flood':
            # rx5day 기준/미래 분리
            rx5day_split = splitter.split_rx5day(raw_data.get('rx5day', []))
            result['climate_data'] = rx5day_split
            result['climate_data']['watershed_area_km2'] = 100.0  # TODO: 실제 유역면적 조회
            result['climate_data']['stream_order'] = 2  # TODO: 실제 하천 차수 조회

        elif risk_type == 'urban_flood':
            # rx1day, sdii, rain80 기준/미래 분리
            rx1day_split = splitter.split_rx1day(raw_data.get('rx1day', []))
            sdii_split = splitter.split_sdii(raw_data.get('sdii', []))
            rain80_split = splitter.split_rain80(raw_data.get('rain80', []))
            result['climate_data'] = {**rx1day_split, **sdii_split, **rain80_split}

        elif risk_type == 'drought':
            result['climate_data'] = {
                'consecutive_dry_days': raw_data.get('cdd', []),
                'spi_index': raw_data.get('spei12', []),
                'soil_moisture': 0.5,  # TODO: 실제 토양수분 조회
                'drought_duration_months': 6  # TODO: 계산 필요
            }

        elif risk_type == 'typhoon':
            # 풍속 95분위수 기준/미래 분리
            wind_split = splitter.split_wind(raw_data.get('ws', []))
            result['climate_data'] = wind_split

        elif risk_type == 'sea_level_rise':
            # 해수면 상승 데이터 (별도 조회 필요)
            sea_level_data = DatabaseConnection._fetch_sea_level_data(latitude, longitude, ssp_scenario)
            result['climate_data'] = {'slr_cm': sea_level_data}

        elif risk_type == 'water_stress':
            # 강수량, 유역면적 등
            result['climate_data'] = {
                'precipitation_mm': raw_data.get('rn', []),
                'withdrawal_total': 0.0,  # TODO: WAMIS API 호출
                'basin_area_km2': 100.0,  # TODO: 유역면적 조회
                'runoff_coef': 0.6  # TODO: 유출계수 조회
            }
        else:
            # 기본값: 원시 데이터 반환
            result['climate_data'] = raw_data

        return result

    @staticmethod
    def _fetch_raw_climate_data(latitude: float, longitude: float, ssp_scenario: str = 'ssp2') -> Dict[str, List[float]]:
        """
        원시 기후 데이터 조회 (DB 테이블에서 직접 조회)

        Args:
            latitude: 격자 위도
            longitude: 격자 경도
            ssp_scenario: SSP 시나리오 (ssp1, ssp2, ssp3, ssp5)

        Returns:
            {
                'tamax': List[float],  # 일별 최고기온
                'tamin': List[float],  # 일별 최저기온
                'ta': List[float],     # 월별 평균기온
                'rn': List[float],     # 월별 강수량
                'ws': List[float],     # 월별 풍속
                'rhm': List[float],    # 월별 상대습도
                'si': List[float],     # 월별 일사량
                'wsdi': List[float],   # 연별 WSDI
                'csdi': List[float],   # 연별 CSDI
                'rx1day': List[float], # 연별 1일 최대강수
                'rx5day': List[float], # 연별 5일 최대강수
                'cdd': List[float],    # 연별 연속 무강수일
                'rain80': List[float], # 연별 80mm 이상 강수일수
                'sdii': List[float],   # 연별 강수강도
                'spei12': List[float]  # 월별 SPEI12
            }
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            # 1. location_grid에서 grid_id 조회
            cursor.execute("""
                SELECT grid_id
                FROM location_grid
                WHERE latitude = %s AND longitude = %s
                LIMIT 1
            """, (latitude, longitude))

            grid_result = cursor.fetchone()
            if not grid_result:
                # 격자가 없으면 빈 데이터 반환
                return {}

            grid_id = grid_result['grid_id']

            raw_data = {}

            # 2. 일별 데이터 조회 (tamax, tamin) - admin_id 기반
            # TODO: 좌표 → admin_id 매핑 필요
            # 현재는 스킵하고 월별/연별 데이터만 조회

            # 3. 월별 데이터 조회 (ta, rn, ws, rhm, si, spei12)
            monthly_tables = {
                'ta': 'ta_data',
                'rn': 'rn_data',
                'ws': 'ws_data',
                'rhm': 'rhm_data',
                'si': 'si_data',
                'spei12': 'spei12_data'
            }

            for key, table in monthly_tables.items():
                cursor.execute(f"""
                    SELECT {ssp_scenario}
                    FROM {table}
                    WHERE grid_id = %s
                    ORDER BY observation_date
                """, (grid_id,))

                rows = cursor.fetchall()
                raw_data[key] = [row[ssp_scenario] for row in rows if row[ssp_scenario] is not None]

            # 4. 연별 데이터 조회 (wsdi, csdi, rx1day, rx5day, cdd, rain80, sdii)
            yearly_tables = {
                'wsdi': 'wsdi_data',
                'csdi': 'csdi_data',
                'rx1day': 'rx1day_data',
                'rx5day': 'rx5day_data',
                'cdd': 'cdd_data',
                'rain80': 'rain80_data',
                'sdii': 'sdii_data'
            }

            for key, table in yearly_tables.items():
                cursor.execute(f"""
                    SELECT {ssp_scenario}
                    FROM {table}
                    WHERE grid_id = %s
                    ORDER BY year
                """, (grid_id,))

                rows = cursor.fetchall()
                raw_data[key] = [row[ssp_scenario] for row in rows if row[ssp_scenario] is not None]

            return raw_data

    @staticmethod
    def _fetch_sea_level_data(latitude: float, longitude: float, ssp_scenario: str = 'ssp2') -> List[float]:
        """
        해수면 상승 데이터 조회

        Args:
            latitude: 격자 위도
            longitude: 격자 경도
            ssp_scenario: SSP 시나리오

        Returns:
            연도별 해수면 상승값 (cm) 리스트
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            # 1. sea_level_grid에서 grid_id 조회
            cursor.execute("""
                SELECT grid_id
                FROM sea_level_grid
                WHERE latitude = %s AND longitude = %s
                LIMIT 1
            """, (latitude, longitude))

            grid_result = cursor.fetchone()
            if not grid_result:
                return []

            grid_id = grid_result['grid_id']

            # 2. sea_level_data 조회
            cursor.execute(f"""
                SELECT {ssp_scenario}
                FROM sea_level_data
                WHERE grid_id = %s
                ORDER BY year
            """, (grid_id,))

            rows = cursor.fetchall()
            return [row[ssp_scenario] for row in rows if row[ssp_scenario] is not None]

    @staticmethod
    def save_probability_results(results: List[Dict[str, Any]]) -> None:
        """
        P(H) 계산 결과 저장 (업데이트: aal, bin_probabilities, calculation_details)

        Args:
            results: 저장할 결과 리스트
                - latitude: 위도
                - longitude: 경도
                - risk_type: 리스크 타입
                - aal: AAL (Annual Average Loss) = Σ(P[i] × DR[i])
                - bin_probabilities: bin별 발생확률 배열 (JSON)
                - calculation_details: 계산 상세정보 (JSON)
                - bin_data: (하위 호환성) bin별 상세 정보 (선택)
        """
        import json

        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                # bin_probabilities와 calculation_details를 JSON으로 변환
                bin_prob_json = json.dumps(result.get('bin_probabilities', []))
                calc_details_json = json.dumps(result.get('calculation_details', {}))
                bin_data_json = json.dumps(result.get('bin_data', {}))

                cursor.execute("""
                    INSERT INTO probability_results
                    (latitude, longitude, risk_type, aal, bin_probabilities,
                     calculation_details, bin_data, calculated_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        aal = EXCLUDED.aal,
                        bin_probabilities = EXCLUDED.bin_probabilities,
                        calculation_details = EXCLUDED.calculation_details,
                        bin_data = EXCLUDED.bin_data,
                        calculated_at = EXCLUDED.calculated_at
                """, (
                    result['latitude'],
                    result['longitude'],
                    result['risk_type'],
                    result.get('aal', 0.0),
                    bin_prob_json,
                    calc_details_json,
                    bin_data_json
                ))

    @staticmethod
    def save_hazard_results(results: List[Dict[str, Any]]) -> None:
        """Hazard Score 계산 결과 저장"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO hazard_results
                    (latitude, longitude, risk_type, hazard_score,
                     hazard_score_100, hazard_level, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(hazard_score)s, %(hazard_score_100)s,
                            %(hazard_level)s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        hazard_score = EXCLUDED.hazard_score,
                        hazard_score_100 = EXCLUDED.hazard_score_100,
                        hazard_level = EXCLUDED.hazard_level,
                        calculated_at = EXCLUDED.calculated_at
                """, result)

    @staticmethod
    def fetch_building_info(latitude: float, longitude: float) -> Dict[str, Any]:
        """
        건물 정보 조회 (격자 좌표에서 가장 가까운 건물 찾기)

        Args:
            latitude: 격자 위도
            longitude: 격자 경도

        Returns:
            건물 정보 딕셔너리 (없으면 빈 딕셔너리)
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            # 격자 좌표 기준으로 가장 가까운 건물 찾기
            cursor.execute("""
                SELECT
                    EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM use_apr_day) as building_age,
                    strct_nm as structure,
                    main_purp_cd_nm as main_purpose,
                    ugrnd_flr_cnt as floors_below,
                    grnd_flr_cnt as floors_above,
                    tot_area as total_area,
                    arch_area
                FROM api_buildings
                WHERE location IS NOT NULL
                ORDER BY ST_Distance(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                )
                LIMIT 1
            """, (longitude, latitude))

            result = cursor.fetchone()
            return dict(result) if result else {}

    @staticmethod
    def fetch_base_aals(latitude: float, longitude: float) -> Dict[str, float]:
        """
        base_aal 조회 (probability_results.probability)

        Args:
            latitude: 위도
            longitude: 경도

        Returns:
            {risk_type: base_aal} 딕셔너리
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT risk_type, probability AS base_aal
                FROM probability_results
                WHERE latitude = %s AND longitude = %s
            """, (latitude, longitude))

            return {row['risk_type']: row['base_aal'] for row in cursor.fetchall()}

    @staticmethod
    def save_exposure_results(results: List[Dict[str, Any]]) -> None:
        """
        E (Exposure) 계산 결과 저장

        Args:
            results: 저장할 결과 리스트
                - latitude: 위도
                - longitude: 경도
                - risk_type: 리스크 타입
                - exposure_score: 노출도 점수 (0-1)
                - proximity_factor: 근접도 (0-1)
                - normalized_asset_value: 정규화된 자산가치 (0-1)
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO exposure_results
                    (latitude, longitude, risk_type, exposure_score, proximity_factor,
                     normalized_asset_value, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        exposure_score = EXCLUDED.exposure_score,
                        proximity_factor = EXCLUDED.proximity_factor,
                        normalized_asset_value = EXCLUDED.normalized_asset_value,
                        calculated_at = EXCLUDED.calculated_at
                """, (
                    result['latitude'],
                    result['longitude'],
                    result['risk_type'],
                    result.get('exposure_score', 0.0),
                    result.get('proximity_factor', 0.0),
                    result.get('normalized_asset_value', 0.0)
                ))

    @staticmethod
    def save_vulnerability_results(results: List[Dict[str, Any]]) -> None:
        """
        V (Vulnerability) 계산 결과 저장

        Args:
            results: 저장할 결과 리스트
                - latitude: 위도
                - longitude: 경도
                - risk_type: 리스크 타입
                - vulnerability_score: 취약성 점수 (0-100)
                - vulnerability_level: 취약성 등급
                - factors: 취약성 요인 딕셔너리 (JSONB)
        """
        import json

        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                factors_json = json.dumps(result.get('factors', {}))

                cursor.execute("""
                    INSERT INTO vulnerability_results
                    (latitude, longitude, risk_type, vulnerability_score,
                     vulnerability_level, factors, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        vulnerability_score = EXCLUDED.vulnerability_score,
                        vulnerability_level = EXCLUDED.vulnerability_level,
                        factors = EXCLUDED.factors,
                        calculated_at = EXCLUDED.calculated_at
                """, (
                    result['latitude'],
                    result['longitude'],
                    result['risk_type'],
                    result.get('vulnerability_score', 0.0),
                    result.get('vulnerability_level', 'medium'),
                    factors_json
                ))

    @staticmethod
    def save_aal_scaled_results(results: List[Dict[str, Any]]) -> None:
        """
        AAL 스케일링 결과 저장

        Args:
            results: 저장할 결과 리스트
                - latitude: 위도
                - longitude: 경도
                - risk_type: 리스크 타입
                - base_aal: 기본 AAL
                - vulnerability_scale: F_vuln (0.9-1.1)
                - final_aal: 최종 AAL
                - insurance_rate: 보험 보전율 (기본 0.0)
                - expected_loss: 예상 손실액 (선택, 기본 None)
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO aal_scaled_results
                    (latitude, longitude, risk_type, base_aal, vulnerability_scale,
                     final_aal, insurance_rate, expected_loss, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        base_aal = EXCLUDED.base_aal,
                        vulnerability_scale = EXCLUDED.vulnerability_scale,
                        final_aal = EXCLUDED.final_aal,
                        insurance_rate = EXCLUDED.insurance_rate,
                        expected_loss = EXCLUDED.expected_loss,
                        calculated_at = EXCLUDED.calculated_at
                """, (
                    result['latitude'],
                    result['longitude'],
                    result['risk_type'],
                    result.get('base_aal', 0.0),
                    result.get('vulnerability_scale', 1.0),
                    result.get('final_aal', 0.0),
                    result.get('insurance_rate', 0.0),
                    result.get('expected_loss')
                ))
