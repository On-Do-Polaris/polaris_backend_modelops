"""
9개 에이전트 전체 변수 DB 추적 테스트
- hazard_probability_timeseries_batch.py 흐름대로 테스트
- DB → DataLoader → Collector → Agent → calculation_details 전체 추적
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
sys.path.insert(0, '.')

from modelops.utils.hazard_data_collector import HazardDataCollector
from modelops.agents.hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent
from modelops.agents.hazard_calculate.extreme_cold_hscore_agent import ExtremeColdHScoreAgent
from modelops.agents.hazard_calculate.drought_hscore_agent import DroughtHScoreAgent
from modelops.agents.hazard_calculate.river_flood_hscore_agent import RiverFloodHScoreAgent
from modelops.agents.hazard_calculate.urban_flood_hscore_agent import UrbanFloodHScoreAgent
from modelops.agents.hazard_calculate.wildfire_hscore_agent import WildfireHScoreAgent
from modelops.agents.hazard_calculate.water_stress_hscore_agent import WaterStressHScoreAgent
from modelops.agents.hazard_calculate.sea_level_rise_hscore_agent import SeaLevelRiseHScoreAgent
from modelops.agents.hazard_calculate.typhoon_hscore_agent import TyphoonHScoreAgent

# DB 연결
DB_CONFIG = {
    'host': 'localhost',
    'port': 5555,
    'dbname': 'datawarehouse',
    'user': 'skala',
    'password': 'skala1234'
}

# 테스트 파라미터
LAT, LON = 37.5665, 126.978  # 서울
SCENARIO = 'SSP245'
YEAR = 2030

# SSP 시나리오 → 컬럼 매핑
SSP_COLUMN_MAP = {
    'SSP126': 'ssp1',
    'SSP245': 'ssp2',
    'SSP370': 'ssp3',
    'SSP585': 'ssp5'
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def query_db_value(table_name, lat, lon, year, scenario='SSP245'):
    """DB에서 직접 값 조회"""
    ssp_col = SSP_COLUMN_MAP.get(scenario, 'ssp2')

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 가장 가까운 격자점 찾기
            cursor.execute(f"""
                SELECT {ssp_col} as value, year, latitude, longitude
                FROM {table_name}
                WHERE year = %s
                ORDER BY ST_Distance(
                    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
                LIMIT 1
            """, (year, lon, lat))

            result = cursor.fetchone()
            if result:
                return float(result['value']) if result['value'] is not None else None
            return None
    except Exception as e:
        return f"ERROR: {e}"


def query_typhoon_data(lat, lon):
    """태풍 데이터 직접 조회"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 태풍 빈도 및 최대풍속
            cursor.execute("""
                SELECT COUNT(DISTINCT year || '-' || tcid) as count,
                       MAX(max_wind_speed) as max_wind
                FROM api_typhoon_besttrack
                WHERE ST_DWithin(
                    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    500000
                )
            """, (lon, lat))

            result = cursor.fetchone()
            return {
                'frequency': int(result['count'] or 0),
                'max_wind': float(result['max_wind'] or 0)
            }
    except Exception as e:
        return {'frequency': f"ERROR: {e}", 'max_wind': f"ERROR: {e}"}


def query_sea_level_data(lat, lon, year, scenario='SSP245'):
    """해수면 상승 데이터 직접 조회"""
    ssp_col = SSP_COLUMN_MAP.get(scenario, 'ssp2')

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT {ssp_col} as slr, year
                FROM sea_level_data
                WHERE year = %s
                ORDER BY ST_Distance(
                    geom,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
                LIMIT 1
            """, (year, lon, lat))

            result = cursor.fetchone()
            if result:
                return float(result['slr']) if result['slr'] is not None else None
            return None
    except Exception as e:
        return f"ERROR: {e}"


def test_agent(risk_type, agent, collector, expected_vars):
    """에이전트 테스트 및 변수 추적"""
    print(f"\n{'='*60}")
    print(f"  [{risk_type.upper()}] 변수 추적")
    print(f"{'='*60}")

    # 1. Collector로 데이터 수집
    collected = collector.collect_data(LAT, LON, risk_type)

    # 2. Agent로 Hazard Score 계산
    hazard_score = agent.calculate_hazard(collected)

    # 3. calculation_details 추출
    calc_details = collected.get('calculation_details', {}).get(risk_type, {})

    print(f"\n  Hazard Score: {hazard_score}")
    print(f"\n  [변수 추적]")

    results = []
    for var_name, db_table, detail_key in expected_vars:
        # DB에서 직접 조회
        if db_table == 'api_typhoon_besttrack':
            db_data = query_typhoon_data(LAT, LON)
            db_value = db_data.get(detail_key.split('_')[0], 'N/A')  # frequency or max_wind
        elif db_table == 'sea_level_data':
            db_value = query_sea_level_data(LAT, LON, YEAR, SCENARIO)
        elif db_table:
            db_value = query_db_value(db_table, LAT, LON, YEAR, SCENARIO)
        else:
            db_value = 'N/A (no table)'

        # Agent에서 사용한 값 (calculation_details에서)
        agent_value = calc_details.get(detail_key, 'NOT RECORDED')

        # 비교
        match = "✅" if str(db_value)[:8] == str(agent_value)[:8] else "⚠️"
        if agent_value == 'NOT RECORDED':
            match = "❌"

        results.append((var_name, db_table, db_value, agent_value, match))
        print(f"    {match} {var_name}:")
        print(f"       DB({db_table}): {db_value}")
        print(f"       Agent: {agent_value}")

    return hazard_score, results


def main():
    print("="*60)
    print("  9개 에이전트 DB → Agent 변수 추적 테스트")
    print(f"  Location: ({LAT}, {LON})")
    print(f"  Scenario: {SCENARIO}, Year: {YEAR}")
    print("="*60)

    # Collector 생성
    collector = HazardDataCollector(scenario=SCENARIO, target_year=YEAR)

    # 에이전트 및 예상 변수 정의
    # (변수명, DB테이블, calculation_details 키)
    tests = [
        ('extreme_heat', ExtremeHeatHScoreAgent(), [
            ('WSDI (폭염지속일수)', 'wsdi_data', 'wsdi'),
            ('SU25 (폭염일수)', 'wsdi_data', 'su25'),  # wsdi 테이블 사용
            ('TR25 (열대야일수)', None, 'tr25'),  # 별도 테이블 없음
        ]),
        ('extreme_cold', ExtremeColdHScoreAgent(), [
            ('CSDI (한파지속일수)', 'csdi_data', 'csdi'),
            ('TNN (최저기온)', 'tamin_data', 'tnn'),
            ('FD0 (서리일수)', None, 'fd0'),
            ('ID0 (결빙일수)', None, 'id0'),
        ]),
        ('drought', DroughtHScoreAgent(), [
            ('SPEI12 (가뭄지수)', 'spei12_data', 'spei12'),
            ('CDD (연속무강수일)', 'cdd_data', 'cdd'),
            ('Annual Rainfall (연강수량)', 'rn_data', 'annual_rainfall'),
        ]),
        ('river_flood', RiverFloodHScoreAgent(), [
            ('RX1DAY (1일최대강수)', 'rx1day_data', 'rx1day'),
            ('TWI (지형습윤지수)', None, 'twi'),
            ('Distance to River', None, 'distance_to_river'),
        ]),
        ('urban_flood', UrbanFloodHScoreAgent(), [
            ('RX1DAY (1일최대강수)', 'rx1day_data', 'rx1day'),
            ('Effective Drainage', None, 'effective_drainage'),
        ]),
        ('wildfire', WildfireHScoreAgent(), [
            ('TA (평균기온)', 'ta_data', 'ta'),
            ('RHM (상대습도)', 'rhm_data', 'rhm'),
            ('WS (풍속)', 'ws_data', 'ws'),
            ('RN (연강수량)', 'rn_data', 'rn'),
            ('FWI (화재기상지수)', None, 'fwi'),
        ]),
        ('water_stress', WaterStressHScoreAgent(), [
            ('Rainfall (연강수량)', 'rn_data', 'rainfall'),
            ('CDD (연속무강수일)', 'cdd_data', 'cdd'),
            ('Stress Index', None, 'stress_index'),
        ]),
        ('sea_level_rise', SeaLevelRiseHScoreAgent(), [
            ('SLR (해수면상승)', 'sea_level_data', 'slr'),
            ('Distance to Coast', None, 'distance'),
        ]),
        ('typhoon', TyphoonHScoreAgent(), [
            ('Typhoon Frequency', 'api_typhoon_besttrack', 'frequency'),
            ('Max Wind Speed', 'api_typhoon_besttrack', 'max_wind'),
            ('RX1DAY', 'rx1day_data', 'rx1day_mm'),
        ]),
    ]

    all_results = {}

    for risk_type, agent, expected_vars in tests:
        try:
            score, results = test_agent(risk_type, agent, collector, expected_vars)
            all_results[risk_type] = {'score': score, 'results': results}
        except Exception as e:
            print(f"\n  [{risk_type.upper()}] ERROR: {e}")
            all_results[risk_type] = {'error': str(e)}

    # 최종 요약
    print("\n" + "="*60)
    print("  최종 요약")
    print("="*60)

    for risk_type, data in all_results.items():
        if 'error' in data:
            print(f"  {risk_type}: ❌ ERROR")
        else:
            matched = sum(1 for r in data['results'] if r[4] == "✅")
            total = len(data['results'])
            status = "✅" if matched == total else "⚠️"
            print(f"  {status} {risk_type}: H={data['score']:.4f}, 변수 {matched}/{total} 매칭")


if __name__ == "__main__":
    main()
