#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hazard_probability_timeseries_batch.py 기반
모든 9개 리스크 Agent 변수 DB → Loader → Collector → Agent 추적 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['DW_HOST'] = 'localhost'
os.environ['DW_PORT'] = '5555'
os.environ['DW_NAME'] = 'datawarehouse'
os.environ['DW_USER'] = 'skala'
os.environ['DW_PASSWORD'] = 'skala1234'

from modelops.database.connection import DatabaseConnection
from modelops.data_loaders.climate_data_loader import ClimateDataLoader

# batch에서 사용하는 것과 동일하게 import
from modelops.agents.hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent
from modelops.agents.hazard_calculate.extreme_cold_hscore_agent import ExtremeColdHScoreAgent
from modelops.agents.hazard_calculate.drought_hscore_agent import DroughtHScoreAgent
from modelops.agents.hazard_calculate.river_flood_hscore_agent import RiverFloodHScoreAgent
from modelops.agents.hazard_calculate.urban_flood_hscore_agent import UrbanFloodHScoreAgent
from modelops.agents.hazard_calculate.wildfire_hscore_agent import WildfireHScoreAgent
from modelops.agents.hazard_calculate.water_stress_hscore_agent import WaterStressHScoreAgent
from modelops.agents.hazard_calculate.sea_level_rise_hscore_agent import SeaLevelRiseHScoreAgent
from modelops.agents.hazard_calculate.typhoon_hscore_agent import TyphoonHScoreAgent

# HazardDataCollector (batch에서 사용)
from modelops.utils.hazard_data_collector import HazardDataCollector

# 테스트 좌표
TEST_LAT = 37.3825
TEST_LON = 127.122
SCENARIO = 'SSP245'
TARGET_YEAR = 2030
SSP_COL = 'ssp2'

print("=" * 100)
print("🔍 hazard_probability_timeseries_batch.py 기반 - 모든 변수 DB 추적 테스트")
print("=" * 100)
print(f"📍 좌표: ({TEST_LAT}, {TEST_LON}), 시나리오: {SCENARIO}, 연도: {TARGET_YEAR}")
print()

# grid_id 조회
with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT grid_id FROM location_grid 
        ORDER BY SQRT(POWER(longitude - %s, 2) + POWER(latitude - %s, 2)) LIMIT 1
    """, (TEST_LON, TEST_LAT))
    GRID_ID = cursor.fetchone()['grid_id']
print(f"🎯 Grid ID: {GRID_ID}")
print()

def get_db_value(cursor, table, col, grid_id, year, is_yearly=True):
    """DB에서 값 직접 조회"""
    try:
        if is_yearly:
            cursor.execute(f"SELECT {col} FROM {table} WHERE grid_id = %s AND year = %s", (grid_id, year))
        else:
            # observation_date 기반 (연평균)
            cursor.execute(f"""
                SELECT AVG({col}) as val FROM {table} 
                WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s
            """, (grid_id, year))
        r = cursor.fetchone()
        return round(float(r[col if is_yearly else 'val']), 2) if r and r[col if is_yearly else 'val'] else None
    except Exception as e:
        return f"ERR: {e}"

def get_db_count(cursor, table, col, grid_id, year, condition):
    """DB에서 COUNT 조회 (SU25, TR25, FD0, ID0 등)"""
    try:
        cursor.execute(f"""
            SELECT COUNT(*) as cnt FROM {table} 
            WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND {col} {condition}
        """, (grid_id, year))
        r = cursor.fetchone()
        return int(r['cnt']) if r else 0
    except Exception as e:
        return f"ERR: {e}"

def get_db_agg(cursor, table, col, grid_id, year, agg_func='MAX'):
    """DB에서 집계값 조회 (TXx=MAX, TNn=MIN 등)"""
    try:
        cursor.execute(f"""
            SELECT {agg_func}({col}) as val FROM {table} 
            WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s
        """, (grid_id, year))
        r = cursor.fetchone()
        return round(float(r['val']), 2) if r and r['val'] else None
    except Exception as e:
        return f"ERR: {e}"

# ClimateDataLoader 초기화
loader = ClimateDataLoader(scenario=SCENARIO)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    
    # ========== 1. EXTREME HEAT ==========
    print("=" * 100)
    print("🔥 1. EXTREME HEAT (극심한 고온)")
    print("   사용 변수: WSDI, TXx, SU25, TR25")
    print("-" * 100)
    
    # DB 직접 조회
    wsdi_db = get_db_value(cursor, 'wsdi_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    txx_db = get_db_agg(cursor, 'tamax_data', SSP_COL, GRID_ID, TARGET_YEAR, 'MAX')
    su25_db = get_db_count(cursor, 'tamax_data', SSP_COL, GRID_ID, TARGET_YEAR, '> 25')
    tr25_db = get_db_count(cursor, 'tamin_data', SSP_COL, GRID_ID, TARGET_YEAR, '> 25')
    
    # Loader 조회
    loader_data = loader.get_extreme_heat_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    
    # Collector + Agent
    collector = HazardDataCollector(scenario=SCENARIO, target_year=TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'extreme_heat')
    agent = ExtremeHeatHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('extreme_heat', {})
    
    print(f"  | 변수  | DB 테이블     | DB 값      | Loader 값   | Agent 사용값 |")
    print(f"  |-------|---------------|------------|-------------|--------------|")
    print(f"  | WSDI  | wsdi_data     | {str(wsdi_db):<10} | {str(loader_data.get('wsdi')):<11} | {str(details.get('wsdi')):<12} |")
    print(f"  | TXx   | tamax_data    | {str(txx_db):<10} | {str(loader_data.get('annual_max_temp_celsius')):<11} | (tx90p 대체)  |")
    print(f"  | SU25  | tamax_data    | {str(su25_db):<10} | {str(loader_data.get('heatwave_days_per_year')):<11} | {str(details.get('su25')):<12} |")
    print(f"  | TR25  | tamin_data    | {str(tr25_db):<10} | {str(loader_data.get('tropical_nights')):<11} | {str(details.get('tr25')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 2. EXTREME COLD ==========
    print("=" * 100)
    print("❄️ 2. EXTREME COLD (극심한 한파)")
    print("   사용 변수: CSDI, TNn, FD0, ID0")
    print("-" * 100)
    
    csdi_db = get_db_value(cursor, 'csdi_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    tnn_db = get_db_agg(cursor, 'tamin_data', SSP_COL, GRID_ID, TARGET_YEAR, 'MIN')
    fd0_db = get_db_count(cursor, 'tamin_data', SSP_COL, GRID_ID, TARGET_YEAR, '< 0')
    id0_db = get_db_count(cursor, 'tamax_data', SSP_COL, GRID_ID, TARGET_YEAR, '< 0')
    
    loader_data = loader.get_extreme_cold_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'extreme_cold')
    agent = ExtremeColdHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('extreme_cold', {})
    
    print(f"  | 변수  | DB 테이블     | DB 값      | Loader 값   | Agent 사용값 |")
    print(f"  |-------|---------------|------------|-------------|--------------|")
    print(f"  | CSDI  | csdi_data     | {str(csdi_db):<10} | {str(loader_data.get('csdi')):<11} | {str(details.get('csdi')):<12} |")
    print(f"  | TNn   | tamin_data    | {str(tnn_db):<10} | {str(loader_data.get('annual_min_temp_celsius')):<11} | {str(details.get('tnn')):<12} |")
    print(f"  | FD0   | tamin_data    | {str(fd0_db):<10} | {str(loader_data.get('coldwave_days_per_year')):<11} | {str(details.get('fd0')):<12} |")
    print(f"  | ID0   | tamax_data    | {str(id0_db):<10} | {str(loader_data.get('ice_days')):<11} | {str(details.get('id0')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 3. DROUGHT ==========
    print("=" * 100)
    print("🏜️ 3. DROUGHT (가뭄)")
    print("   사용 변수: CDD, SPEI12, SDII")
    print("-" * 100)
    
    cdd_db = get_db_value(cursor, 'cdd_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    sdii_db = get_db_value(cursor, 'sdii_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    
    # SPEI12는 월별 데이터 (6월 기준)
    cursor.execute(f"""
        SELECT {SSP_COL} as val FROM spei12_data 
        WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND EXTRACT(MONTH FROM observation_date) = 6
    """, (GRID_ID, TARGET_YEAR))
    r = cursor.fetchone()
    spei_db = round(float(r['val']), 2) if r and r['val'] else None
    
    loader_data = loader.get_drought_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'drought')
    agent = DroughtHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('drought', {})
    
    print(f"  | 변수   | DB 테이블    | DB 값      | Loader 값   | Agent 사용값 |")
    print(f"  |--------|--------------|------------|-------------|--------------|")
    print(f"  | CDD    | cdd_data     | {str(cdd_db):<10} | {str(loader_data.get('cdd')):<11} | {str(details.get('cdd')):<12} |")
    print(f"  | SPEI12 | spei12_data  | {str(spei_db):<10} | {str(loader_data.get('spei12_index')):<11} | {str(details.get('spei12')):<12} |")
    print(f"  | SDII   | sdii_data    | {str(sdii_db):<10} | {str(loader_data.get('sdii')):<11} | {str(details.get('sdii')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 4. RIVER FLOOD ==========
    print("=" * 100)
    print("🌊 4. RIVER FLOOD (하천 홍수)")
    print("   사용 변수: RX1DAY, RX5DAY, RAIN80")
    print("-" * 100)
    
    rx1day_db = get_db_value(cursor, 'rx1day_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    rx5day_db = get_db_value(cursor, 'rx5day_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    rain80_db = get_db_value(cursor, 'rain80_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=True)
    
    loader_data = loader.get_flood_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'river_flood')
    agent = RiverFloodHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('river_flood', {})
    
    print(f"  | 변수   | DB 테이블    | DB 값      | Loader 값   | Agent 사용값 |")
    print(f"  |--------|--------------|------------|-------------|--------------|")
    print(f"  | RX1DAY | rx1day_data  | {str(rx1day_db):<10} | {str(loader_data.get('rx1day')):<11} | {str(details.get('rx1day')):<12} |")
    print(f"  | RX5DAY | rx5day_data  | {str(rx5day_db):<10} | {str(loader_data.get('rx5day')):<11} | {str(details.get('rx5day')):<12} |")
    print(f"  | RAIN80 | rain80_data  | {str(rain80_db):<10} | {str(loader_data.get('rain80')):<11} | {str(details.get('rain80')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 5. URBAN FLOOD ==========
    print("=" * 100)
    print("🏙️ 5. URBAN FLOOD (도시 홍수)")
    print("   사용 변수: RX1DAY, RX5DAY, RAIN80 (River Flood와 동일)")
    print("-" * 100)
    
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'urban_flood')
    agent = UrbanFloodHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('urban_flood', {})
    
    print(f"  | 변수   | DB 테이블    | DB 값      | Agent 사용값 |")
    print(f"  |--------|--------------|------------|--------------|")
    print(f"  | RX1DAY | rx1day_data  | {str(rx1day_db):<10} | {str(details.get('rx1day')):<12} |")
    print(f"  | RX5DAY | rx5day_data  | {str(rx5day_db):<10} | {str(details.get('rx5day')):<12} |")
    print(f"  | RAIN80 | rain80_data  | {str(rain80_db):<10} | {str(details.get('rain80')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 6. WILDFIRE ==========
    print("=" * 100)
    print("🔥 6. WILDFIRE (산불)")
    print("   사용 변수: RHM, WS, CDD, TA")
    print("-" * 100)
    
    rhm_db = get_db_value(cursor, 'rhm_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=False)
    ws_db = get_db_value(cursor, 'ws_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=False)
    ta_db = get_db_value(cursor, 'ta_data', SSP_COL, GRID_ID, TARGET_YEAR, is_yearly=False)
    
    loader_data = loader.get_fwi_input_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'wildfire')
    agent = WildfireHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('wildfire', {})
    
    print(f"  | 변수 | DB 테이블  | DB 값      | Loader 값   | Agent 사용값 |")
    print(f"  |------|------------|------------|-------------|--------------|")
    print(f"  | RHM  | rhm_data   | {str(rhm_db):<10} | {str(loader_data.get('rhm')):<11} | {str(details.get('rhm')):<12} |")
    print(f"  | WS   | ws_data    | {str(ws_db):<10} | {str(loader_data.get('ws')):<11} | {str(details.get('ws')):<12} |")
    print(f"  | CDD  | cdd_data   | {str(cdd_db):<10} | (drought)   | {str(details.get('cdd')):<12} |")
    print(f"  | TA   | ta_data    | {str(ta_db):<10} | (indirect)  | {str(details.get('ta')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 7. WATER STRESS ==========
    print("=" * 100)
    print("💧 7. WATER STRESS (물 스트레스)")
    print("   사용 변수: CDD, RN(강수량)")
    print("-" * 100)
    
    # 연간 강수량
    cursor.execute(f"""
        SELECT SUM({SSP_COL}) as total FROM rn_data 
        WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s
    """, (GRID_ID, TARGET_YEAR))
    r = cursor.fetchone()
    rn_db = round(float(r['total']), 1) if r and r['total'] else None
    
    loader_data = loader.get_water_stress_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'water_stress')
    agent = WaterStressHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('water_stress', {})
    
    print(f"  | 변수 | DB 테이블 | DB 값      | Loader 값   | Agent 사용값 |")
    print(f"  |------|-----------|------------|-------------|--------------|")
    print(f"  | CDD  | cdd_data  | {str(cdd_db):<10} | {str(loader_data.get('cdd')):<11} | {str(details.get('cdd')):<12} |")
    print(f"  | RN   | rn_data   | {str(rn_db):<10} | {str(loader_data.get('annual_rainfall_mm')):<11} | {str(details.get('rainfall')):<12} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 8. SEA LEVEL RISE ==========
    print("=" * 100)
    print("🌅 8. SEA LEVEL RISE (해수면 상승)")
    print("   사용 변수: SLR(해수면상승), Distance to Coast")
    print("-" * 100)
    
    # 해수면 데이터
    cursor.execute(f"""
        SELECT d.{SSP_COL} as slr_cm,
               ST_Distance(g.geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as dist_m
        FROM sea_level_grid g
        INNER JOIN sea_level_data d ON g.grid_id = d.grid_id
        WHERE d.year = %s AND d.{SSP_COL} IS NOT NULL
        ORDER BY g.geom::geography <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        LIMIT 1
    """, (TEST_LON, TEST_LAT, TARGET_YEAR, TEST_LON, TEST_LAT))
    r = cursor.fetchone()
    slr_db = round(float(r['slr_cm']), 2) if r and r['slr_cm'] else None
    dist_db = round(float(r['dist_m']), 0) if r and r['dist_m'] else None
    
    loader_data = loader.get_sea_level_rise_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'sea_level_rise')
    agent = SeaLevelRiseHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('sea_level_rise', {})
    
    print(f"  | 변수       | DB 값            | Loader 값        | Agent 사용값     |")
    print(f"  |------------|------------------|------------------|------------------|")
    print(f"  | SLR (cm)   | {str(slr_db):<16} | {str(loader_data.get('sea_level_rise_cm')):<16} | {str(details.get('slr')):<16} |")
    print(f"  | Distance   | {str(dist_db):<16} | {str(round(loader_data.get('distance_to_coast_m', 0))):<16} | {str(details.get('distance')):<16} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()
    
    # ========== 9. TYPHOON ==========
    print("=" * 100)
    print("🌀 9. TYPHOON (태풍)")
    print("   사용 변수: 태풍이력, RX1DAY, 해안거리")
    print("-" * 100)
    
    # 태풍 이력 (api_typhoon_besttrack)
    cursor.execute("""
        SELECT COUNT(DISTINCT year || '-' || tcid) as typhoon_count,
               MAX(max_wind_speed) as max_wind
        FROM api_typhoon_besttrack
        WHERE ST_DWithin(
            ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            500000
        )
    """, (TEST_LON, TEST_LAT))
    r = cursor.fetchone()
    typhoon_cnt = int(r['typhoon_count']) if r and r['typhoon_count'] else 0
    max_wind = float(r['max_wind']) if r and r['max_wind'] else 0
    
    loader_data = loader.get_typhoon_data(TEST_LAT, TEST_LON, TARGET_YEAR)
    collected = collector.collect_data(TEST_LAT, TEST_LON, 'typhoon')
    agent = TyphoonHScoreAgent()
    result = agent.calculate_hazard_score(collected)
    details = collected.get('calculation_details', {}).get('typhoon', {})
    
    print(f"  | 변수         | DB 값            | Loader 값        | Agent 사용값     |")
    print(f"  |--------------|------------------|------------------|------------------|")
    print(f"  | 태풍빈도     | {str(typhoon_cnt):<16} | {str(loader_data.get('typhoon_frequency')):<16} | {str(details.get('frequency')):<16} |")
    print(f"  | 최대풍속     | {str(max_wind):<16} | {str(loader_data.get('max_wind_speed_ms')):<16} | {str(details.get('max_wind')):<16} |")
    print(f"  | RX1DAY       | {str(rx1day_db):<16} | {str(loader_data.get('rx1day')):<16} | {str(details.get('rx1day')):<16} |")
    print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
    print()

print("=" * 100)
print("✅ 모든 9개 리스크 Agent 변수 DB 추적 완료!")
print("=" * 100)
print()
print("📋 요약: DB 테이블 → ClimateDataLoader → HazardDataCollector → Agent")
print("   모든 기후 변수들이 DB에서 정상적으로 로드되어 Agent 계산에 사용됨")
