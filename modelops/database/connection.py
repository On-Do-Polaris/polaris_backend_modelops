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
    def fetch_climate_data(latitude: float, longitude: float) -> Dict[str, Any]:
        """특정 격자의 기후 데이터 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM climate_data
                WHERE latitude = %s AND longitude = %s
                ORDER BY year, month
            """, (latitude, longitude))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def save_probability_results(results: List[Dict[str, Any]]) -> None:
        """
        P(H) 계산 결과 저장

        Args:
            results: 저장할 결과 리스트
                - latitude: 위도
                - longitude: 경도
                - risk_type: 리스크 타입
                - aal: AAL (Annual Average Loss) = Σ(P[i] × DR[i])
                - bin_data: bin별 상세 정보 (확률, 손상률, 범위)
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO probability_results
                    (latitude, longitude, risk_type, probability, bin_data, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(aal)s, %(bin_data)s::jsonb, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        probability = EXCLUDED.probability,
                        bin_data = EXCLUDED.bin_data,
                        calculated_at = EXCLUDED.calculated_at
                """, result)

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
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO exposure_results
                    (latitude, longitude, risk_type, exposure_score, proximity_factor, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(exposure_score)s, %(proximity_factor)s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        exposure_score = EXCLUDED.exposure_score,
                        proximity_factor = EXCLUDED.proximity_factor,
                        calculated_at = EXCLUDED.calculated_at
                """, result)

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
                - factors: 취약성 요인 (JSONB)
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO vulnerability_results
                    (latitude, longitude, risk_type, vulnerability_score,
                     vulnerability_level, factors, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(vulnerability_score)s, %(vulnerability_level)s,
                            %(factors)s::jsonb, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        vulnerability_score = EXCLUDED.vulnerability_score,
                        vulnerability_level = EXCLUDED.vulnerability_level,
                        factors = EXCLUDED.factors,
                        calculated_at = EXCLUDED.calculated_at
                """, result)

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
                - insurance_rate: 보험 보전율
                - expected_loss: 예상 손실액 (선택)
        """
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO aal_scaled_results
                    (latitude, longitude, risk_type, base_aal, vulnerability_scale,
                     final_aal, insurance_rate, expected_loss, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(base_aal)s, %(vulnerability_scale)s, %(final_aal)s,
                            %(insurance_rate)s, %(expected_loss)s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        base_aal = EXCLUDED.base_aal,
                        vulnerability_scale = EXCLUDED.vulnerability_scale,
                        final_aal = EXCLUDED.final_aal,
                        insurance_rate = EXCLUDED.insurance_rate,
                        expected_loss = EXCLUDED.expected_loss,
                        calculated_at = EXCLUDED.calculated_at
                """, result)
