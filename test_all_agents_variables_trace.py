#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
모든 9개 리스크 Agent의 변수들 DB → Loader → Collector → Agent 추적 테스트
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
from modelops.utils.hazard_data_collector import HazardDataCollector

# Hazard Agents
from modelops.agents.hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent
from modelops.agents.hazard_calculate.extreme_cold_hscore_agent import ExtremeColdHScoreAgent
from modelops.agents.hazard_calculate.drought_hscore_agent import DroughtHScoreAgent
from modelops.agents.hazard_calculate.river_flood_hscore_agent import RiverFloodHScoreAgent
from modelops.agents.hazard_calculate.urban_flood_hscore_agent import UrbanFloodHScoreAgent
from modelops.agents.hazard_calculate.wildfire_hscore_agent import WildfireHScoreAgent
from modelops.agents.hazard_calculate.water_stress_hscore_agent import WaterStressHScoreAgent

# 테스트 좌표
TEST_LAT = 37.3825
TEST_LON = 127.122
SCENARIO = 'SSP245'
TARGET_YEAR = 2030

print("=" * 100)
print("🔍 모든 9개 리스크 Agent 변수 추적 테스트")
print("=" * 100)
print(f"📍 좌표: ({TEST_LAT}, {TEST_LON}), 시나리오: {SCENARIO}, 연도: {TARGET_YEAR}")
print()

loader = ClimateDataLoader(scenario=SCENARIO)

# grid_id 조회
with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT grid_id FROM location_grid 
        ORDER BY SQRT(POWER(longitude - %s, 2) + POWER(latitude - %s, 2)) LIMIT 1
    """, (TEST_LON, TEST_LAT))
    grid_id = cursor.fetchone()['grid_id']
    print(f"🎯 Grid ID: {grid_id}")
print()

# ========== 1. EXTREME HEAT ==========
print("=" * 100)
print("🔥 1. EXTREME HEAT")
print("=" * 100)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT year, ssp2 FROM wsdi_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    wsdi_db = r['ssp2'] if r else None
    
    cursor.execute("SELECT MAX(ssp2) as v FROM tamax_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    txx_db = r['v'] if r else None
    
    cursor.execute("SELECT COUNT(*) as v FROM tamax_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND ssp2 > 25", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    su25_db = r['v'] if r else None
    
    cursor.execute("SELECT COUNT(*) as v FROM tamin_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND ssp2 > 25", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    tr25_db = r['v'] if r else None

loader_data = loader.get_extreme_heat_data(TEST_LAT, TEST_LON, TARGET_YEAR)
collector = HazardDataCollector(scenario=SCENARIO, target_year=TARGET_YEAR)
collected = collector.collect_data(TEST_LAT, TEST_LON, 'extreme_heat')
agent = ExtremeHeatHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('extreme_heat', {})

print(f"  📊 변수 추적:")
print(f"  | WSDI  | DB: {wsdi_db:<10} → Loader: {loader_data.get('wsdi'):<10} → Agent: {details.get('wsdi')}")
print(f"  | TXx   | DB: {txx_db:<10} → Loader: {loader_data.get('annual_max_temp_celsius'):<10} → Agent: (tx90p로 사용)")
print(f"  | SU25  | DB: {su25_db:<10} → Loader: {loader_data.get('heatwave_days_per_year'):<10} → Agent: {details.get('su25')}")
print(f"  | TR25  | DB: {tr25_db:<10} → Loader: {loader_data.get('tropical_nights'):<10} → Agent: {details.get('tr25')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 2. EXTREME COLD ==========
print("=" * 100)
print("❄️ 2. EXTREME COLD")
print("=" * 100)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ssp2 FROM csdi_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    csdi_db = r['ssp2'] if r else None
    
    cursor.execute("SELECT MIN(ssp2) as v FROM tamin_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    tnn_db = r['v'] if r else None
    
    cursor.execute("SELECT COUNT(*) as v FROM tamin_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND ssp2 < 0", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    fd0_db = r['v'] if r else None
    
    cursor.execute("SELECT COUNT(*) as v FROM tamax_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND ssp2 < 0", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    id0_db = r['v'] if r else None

loader_data = loader.get_extreme_cold_data(TEST_LAT, TEST_LON, TARGET_YEAR)
collected = collector.collect_data(TEST_LAT, TEST_LON, 'extreme_cold')
agent = ExtremeColdHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('extreme_cold', {})

print(f"  📊 변수 추적:")
print(f"  | CSDI  | DB: {csdi_db:<10} → Loader: {loader_data.get('csdi'):<10} → Agent: {details.get('csdi')}")
print(f"  | TNn   | DB: {tnn_db:<10} → Loader: {loader_data.get('annual_min_temp_celsius'):<10} → Agent: {details.get('tnn')}")
print(f"  | FD0   | DB: {fd0_db:<10} → Loader: {loader_data.get('coldwave_days_per_year'):<10} → Agent: {details.get('fd0')}")
print(f"  | ID0   | DB: {id0_db:<10} → Loader: {loader_data.get('ice_days'):<10} → Agent: {details.get('id0')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 3. DROUGHT ==========
print("=" * 100)
print("🏜️ 3. DROUGHT")
print("=" * 100)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    
    cursor.execute("SELECT ssp2 FROM cdd_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    cdd_db = r['ssp2'] if r else None
    
    cursor.execute("""
        SELECT ssp2 FROM spei12_data 
        WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND EXTRACT(MONTH FROM observation_date) = 6
    """, (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    spei_db = r['ssp2'] if r else None
    
    cursor.execute("SELECT ssp2 FROM sdii_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    sdii_db = r['ssp2'] if r else None

loader_data = loader.get_drought_data(TEST_LAT, TEST_LON, TARGET_YEAR)
collected = collector.collect_data(TEST_LAT, TEST_LON, 'drought')
agent = DroughtHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('drought', {})

print(f"  📊 변수 추적:")
print(f"  | CDD    | DB: {cdd_db:<10} → Loader: {loader_data.get('cdd'):<10} → Agent: {details.get('cdd')}")
print(f"  | SPEI12 | DB: {spei_db:<10} → Loader: {loader_data.get('spei12_index'):<10} → Agent: {details.get('spei12')}")
print(f"  | SDII   | DB: {sdii_db:<10} → Loader: {loader_data.get('sdii'):<10} → Agent: {details.get('sdii')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 4. RIVER FLOOD ==========
print("=" * 100)
print("🌊 4. RIVER FLOOD")
print("=" * 100)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    
    cursor.execute("SELECT ssp2 FROM rx1day_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    rx1day_db = r['ssp2'] if r else None
    
    cursor.execute("SELECT ssp2 FROM rx5day_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    rx5day_db = r['ssp2'] if r else None
    
    cursor.execute("SELECT ssp2 FROM rain80_data WHERE grid_id = %s AND year = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    rain80_db = r['ssp2'] if r else None

loader_data = loader.get_flood_data(TEST_LAT, TEST_LON, TARGET_YEAR)
collected = collector.collect_data(TEST_LAT, TEST_LON, 'river_flood')
agent = RiverFloodHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('river_flood', {})

print(f"  📊 변수 추적:")
print(f"  | RX1DAY | DB: {rx1day_db:<10} → Loader: {loader_data.get('rx1day'):<10} → Agent: {details.get('rx1day')}")
print(f"  | RX5DAY | DB: {rx5day_db:<10} → Loader: {loader_data.get('rx5day'):<10} → Agent: {details.get('rx5day')}")
print(f"  | RAIN80 | DB: {rain80_db:<10} → Loader: {loader_data.get('rain80'):<10} → Agent: {details.get('rain80')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 5. URBAN FLOOD ==========
print("=" * 100)
print("🏙️ 5. URBAN FLOOD")
print("=" * 100)

collected = collector.collect_data(TEST_LAT, TEST_LON, 'urban_flood')
agent = UrbanFloodHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('urban_flood', {})

print(f"  📊 변수 추적 (River Flood와 동일한 기후 데이터 사용):")
print(f"  | RX1DAY | DB: {rx1day_db:<10} → Agent: {details.get('rx1day')}")
print(f"  | RX5DAY | DB: {rx5day_db:<10} → Agent: {details.get('rx5day')}")
print(f"  | RAIN80 | DB: {rain80_db:<10} → Agent: {details.get('rain80')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 6. WILDFIRE ==========
print("=" * 100)
print("🔥 6. WILDFIRE")
print("=" * 100)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    
    cursor.execute("SELECT AVG(ssp2) as v FROM rhm_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    rhm_db = round(r['v'], 2) if r and r['v'] else None
    
    cursor.execute("SELECT AVG(ssp2) as v FROM ws_data WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s", (grid_id, TARGET_YEAR))
    r = cursor.fetchone()
    ws_db = round(r['v'], 2) if r and r['v'] else None

loader_data = loader.get_fwi_input_data(TEST_LAT, TEST_LON, TARGET_YEAR)
collected = collector.collect_data(TEST_LAT, TEST_LON, 'wildfire')
agent = WildfireHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('wildfire', {})

print(f"  📊 변수 추적:")
print(f"  | RHM   | DB: {rhm_db:<10} → Loader: {loader_data.get('rhm'):<10} → Agent: {details.get('rhm')}")
print(f"  | WS    | DB: {ws_db:<10} → Loader: {loader_data.get('ws'):<10} → Agent: {details.get('ws')}")
print(f"  | CDD   | DB: {cdd_db:<10} → Agent: {details.get('cdd')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 7. WATER STRESS ==========
print("=" * 100)
print("💧 7. WATER STRESS")
print("=" * 100)

collected = collector.collect_data(TEST_LAT, TEST_LON, 'water_stress')
agent = WaterStressHScoreAgent()
result = agent.calculate_hazard_score(collected)
details = collected.get('calculation_details', {}).get('water_stress', {})

print(f"  📊 변수 추적:")
print(f"  | CDD    | DB: {cdd_db:<10} → Agent: {details.get('cdd')}")
print(f"  | SPEI12 | DB: {spei_db:<10} → Agent: {details.get('spei12')}")
print(f"  ✅ Hazard Score: {result.get('hazard_score_100'):.1f}/100 ({result.get('hazard_level')})")
print()

# ========== 8. SEA LEVEL RISE ==========
print("=" * 100)
print("🌅 8. SEA LEVEL RISE")
print("=" * 100)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT d.ssp2 as slr_cm
        FROM sea_level_grid g
        INNER JOIN sea_level_data d ON g.grid_id = d.grid_id
        WHERE d.year = %s AND d.ssp2 IS NOT NULL
        ORDER BY g.geom::geography <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        LIMIT 1
    """, (TARGET_YEAR, TEST_LON, TEST_LAT))
    r = cursor.fetchone()
    slr_db = r['slr_cm'] if r else None

loader_data = loader.get_sea_level_rise_data(TEST_LAT, TEST_LON, TARGET_YEAR)

print(f"  📊 변수 추적:")
print(f"  | SLR(cm)  | DB: {slr_db:<10} → Loader: {loader_data.get('sea_level_rise_cm')}")
print(f"  | Distance | {loader_data.get('distance_to_coast_m'):.0f}m")
print(f"  ℹ️ Note: 내륙 지역은 해수면상승 영향 낮음")
print()

# ========== 9. TYPHOON ==========
print("=" * 100)
print("🌀 9. TYPHOON")
print("=" * 100)

loader_data = loader.get_typhoon_data(TEST_LAT, TEST_LON, TARGET_YEAR)

print(f"  📊 변수 추적:")
print(f"  | 태풍빈도     | {loader_data.get('typhoon_frequency')}회 (500km 반경 통과)")
print(f"  | 최대풍속     | {loader_data.get('max_wind_speed_ms')} m/s")
print(f"  | RX1DAY       | {loader_data.get('rx1day')} mm")
print(f"  | 해안거리     | {loader_data.get('distance_to_coast_m'):.0f}m")
print()

print("=" * 100)
print("✅ 모든 9개 리스크 Agent 변수 추적 완료!")
print("=" * 100)
