"""
Database Connection Manager

역할:
- DB 연결 관리 (get_connection, get_connection_string)
- 결과 저장 (save_* 함수들)
- 배치 작업 관리 (create_batch_job, update_batch_progress 등)
- 결과 조회 (fetch_hazard_results, fetch_probability_results 등)

주의:
- 데이터 조회(fetch)는 data_loaders 모듈 사용
  - climate_data_loader.py: 기후 데이터
  - building_data_fetcher.py: 건물/하천 데이터
  - spatial_data_loader.py: 공간 데이터 (토지피복, DEM 등)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import uuid
import json
from datetime import datetime
from ..config.settings import settings


class DatabaseConnection:
    """PostgreSQL 데이터베이스 연결 관리"""

    # ==================== 연결 관리 ====================

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

    # ==================== 격자 좌표 조회 (배치 처리용) ====================

    @staticmethod
    def fetch_grid_coordinates() -> List[Dict[str, float]]:
        """모든 격자 좌표 조회 (배치 처리용)"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT latitude, longitude
                FROM location_grid
                ORDER BY latitude, longitude
            """)
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 결과 저장 ====================

    @staticmethod
    def save_probability_results(results: List[Dict[str, Any]]) -> None:
        """
        P(H) 계산 결과 저장

        Args:
            results: 저장할 결과 리스트
                - latitude: 위도
                - longitude: 경도
                - risk_type: 리스크 타입
                - aal: AAL (Annual Average Loss)
                - bin_probabilities: bin별 발생확률 배열 (JSON)
                - calculation_details: 계산 상세정보 (JSON)
        """
        import numpy as np

        def convert_to_native(obj):
            """numpy 타입을 Python 네이티브 타입으로 변환"""
            if isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            return obj

        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                bin_probs = convert_to_native(result.get('bin_probabilities', []))
                calc_details = convert_to_native(result.get('calculation_details', {}))
                bin_data = convert_to_native(result.get('bin_data', {}))
                aal_value = float(result.get('aal', 0.0))

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
                    aal_value,
                    json.dumps(bin_probs),
                    json.dumps(calc_details),
                    json.dumps(bin_data)
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
    def save_exposure_results(results: List[Dict[str, Any]]) -> None:
        """E (Exposure) 계산 결과 저장"""
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
        """V (Vulnerability) 계산 결과 저장"""
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
        """AAL 스케일링 결과 저장"""
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

    # ==================== 배치 작업 관리 ====================

    @staticmethod
    def create_batch_job(job_type: str, input_params: Dict[str, Any]) -> str:
        """배치 작업 생성"""
        batch_id = str(uuid.uuid4())
        input_params_json = json.dumps(input_params)

        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO batch_jobs
                (batch_id, job_type, status, progress, total_items, completed_items,
                 failed_items, input_params, created_at)
                VALUES (%s, %s, 'queued', 0, 0, 0, 0, %s::jsonb, NOW())
                RETURNING batch_id
            """, (batch_id, job_type, input_params_json))

            result = cursor.fetchone()
            return result['batch_id']

    @staticmethod
    def update_batch_progress(batch_id: str, progress: int,
                             current_step: str = None,
                             completed_items: int = None,
                             failed_items: int = None) -> None:
        """배치 진행률 업데이트"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            update_fields = ["progress = %s"]
            params = [progress]

            if current_step is not None:
                update_fields.append("status = 'running'")

            if completed_items is not None:
                update_fields.append("completed_items = %s")
                params.append(completed_items)

            if failed_items is not None:
                update_fields.append("failed_items = %s")
                params.append(failed_items)

            params.append(batch_id)

            query = f"""
                UPDATE batch_jobs
                SET {', '.join(update_fields)}
                WHERE batch_id = %s
            """
            cursor.execute(query, params)

    @staticmethod
    def complete_batch_job(batch_id: str, results: Dict[str, Any]) -> None:
        """배치 작업 완료 처리"""
        results_json = json.dumps(results)

        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE batch_jobs
                SET status = 'completed',
                    progress = 100,
                    results = %s::jsonb,
                    completed_at = NOW()
                WHERE batch_id = %s
            """, (results_json, batch_id))

    @staticmethod
    def fail_batch_job(batch_id: str, error_message: str,
                      error_stack_trace: str = None) -> None:
        """배치 작업 실패 처리"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE batch_jobs
                SET status = 'failed',
                    error_message = %s,
                    error_stack_trace = %s,
                    completed_at = NOW()
                WHERE batch_id = %s
            """, (error_message, error_stack_trace, batch_id))

    @staticmethod
    def get_batch_status(batch_id: str) -> Optional[Dict[str, Any]]:
        """배치 상태 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    batch_id,
                    job_type,
                    status,
                    progress,
                    total_items,
                    completed_items,
                    failed_items,
                    input_params,
                    results,
                    error_message,
                    error_stack_trace,
                    created_at,
                    started_at,
                    completed_at
                FROM batch_jobs
                WHERE batch_id = %s
            """, (batch_id,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # ==================== 결과 조회 ====================

    @staticmethod
    def fetch_base_aals(latitude: float, longitude: float) -> Dict[str, float]:
        """base_aal 조회 (probability_results.aal)"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT risk_type, aal AS base_aal
                FROM probability_results
                WHERE latitude = %s AND longitude = %s
            """, (latitude, longitude))

            return {row['risk_type']: row['base_aal'] for row in cursor.fetchall()}

    @staticmethod
    def fetch_hazard_results(latitude: float, longitude: float,
                            risk_types: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """Hazard Score 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            if risk_types:
                cursor.execute("""
                    SELECT risk_type, hazard_score, hazard_score_100, hazard_level
                    FROM hazard_results
                    WHERE latitude = %s AND longitude = %s
                      AND risk_type = ANY(%s)
                """, (latitude, longitude, risk_types))
            else:
                cursor.execute("""
                    SELECT risk_type, hazard_score, hazard_score_100, hazard_level
                    FROM hazard_results
                    WHERE latitude = %s AND longitude = %s
                """, (latitude, longitude))

            results = {}
            for row in cursor.fetchall():
                results[row['risk_type']] = {
                    'hazard_score': row['hazard_score'],
                    'hazard_score_100': row['hazard_score_100'],
                    'hazard_level': row['hazard_level']
                }

            return results

    @staticmethod
    def fetch_probability_results(latitude: float, longitude: float,
                                 risk_types: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """P(H) 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            if risk_types:
                cursor.execute("""
                    SELECT risk_type, aal, bin_probabilities, calculation_details, bin_data
                    FROM probability_results
                    WHERE latitude = %s AND longitude = %s
                      AND risk_type = ANY(%s)
                """, (latitude, longitude, risk_types))
            else:
                cursor.execute("""
                    SELECT risk_type, aal, bin_probabilities, calculation_details, bin_data
                    FROM probability_results
                    WHERE latitude = %s AND longitude = %s
                """, (latitude, longitude))

            results = {}
            for row in cursor.fetchall():
                results[row['risk_type']] = {
                    'aal': row['aal'],
                    'bin_probabilities': row['bin_probabilities'],
                    'calculation_details': row['calculation_details'],
                    'bin_data': row['bin_data']
                }

            return results

    @staticmethod
    def fetch_exposure_results(latitude: float, longitude: float,
                              risk_types: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """Exposure 결과 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            if risk_types:
                cursor.execute("""
                    SELECT risk_type, exposure_score, proximity_factor, normalized_asset_value
                    FROM exposure_results
                    WHERE latitude = %s AND longitude = %s
                      AND risk_type = ANY(%s)
                """, (latitude, longitude, risk_types))
            else:
                cursor.execute("""
                    SELECT risk_type, exposure_score, proximity_factor, normalized_asset_value
                    FROM exposure_results
                    WHERE latitude = %s AND longitude = %s
                """, (latitude, longitude))

            results = {}
            for row in cursor.fetchall():
                results[row['risk_type']] = {
                    'exposure_score': row['exposure_score'],
                    'proximity_factor': row['proximity_factor'],
                    'normalized_asset_value': row['normalized_asset_value']
                }

            return results

    @staticmethod
    def fetch_vulnerability_results(latitude: float, longitude: float,
                                   risk_types: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """Vulnerability 결과 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            if risk_types:
                cursor.execute("""
                    SELECT risk_type, vulnerability_score, vulnerability_level, factors
                    FROM vulnerability_results
                    WHERE latitude = %s AND longitude = %s
                      AND risk_type = ANY(%s)
                """, (latitude, longitude, risk_types))
            else:
                cursor.execute("""
                    SELECT risk_type, vulnerability_score, vulnerability_level, factors
                    FROM vulnerability_results
                    WHERE latitude = %s AND longitude = %s
                """, (latitude, longitude))

            results = {}
            for row in cursor.fetchall():
                results[row['risk_type']] = {
                    'vulnerability_score': row['vulnerability_score'],
                    'vulnerability_level': row['vulnerability_level'],
                    'factors': row['factors']
                }

            return results

    @staticmethod
    def fetch_aal_scaled_results(latitude: float, longitude: float,
                                risk_types: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """AAL Scaled 결과 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()

            if risk_types:
                cursor.execute("""
                    SELECT risk_type, base_aal, vulnerability_scale, final_aal,
                           insurance_rate, expected_loss
                    FROM aal_scaled_results
                    WHERE latitude = %s AND longitude = %s
                      AND risk_type = ANY(%s)
                """, (latitude, longitude, risk_types))
            else:
                cursor.execute("""
                    SELECT risk_type, base_aal, vulnerability_scale, final_aal,
                           insurance_rate, expected_loss
                    FROM aal_scaled_results
                    WHERE latitude = %s AND longitude = %s
                """, (latitude, longitude))

            results = {}
            for row in cursor.fetchall():
                results[row['risk_type']] = {
                    'base_aal': row['base_aal'],
                    'vulnerability_scale': row['vulnerability_scale'],
                    'final_aal': row['final_aal'],
                    'insurance_rate': row['insurance_rate'],
                    'expected_loss': row['expected_loss']
                }

            return results
