#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
모든 변수들 DB → Loader → Collector → Agent 추적 테스트
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
from modelops.agents.hazard_calculate.extreme_heat_hscore_agent import ExtremeHeatHScoreAgent

# 테스트 좌표 (데이터 있는 격자)
TEST_LAT = 37.3825
TEST_LON = 127.122
SCENARIO = 'SSP245'
TARGET_YEAR = 2030

print("=" * 80)
print("🔍 모든 변수 추적 테스트: DB → Loader → Collector → Agent")
print("=" * 80)
print(f"📍 좌표: ({TEST_LAT}, {TEST_LON})")
print(f"📊 시나리오: {SCENARIO}, 연도: {TARGET_YEAR}")
print()

# ========== Step 1: DB에서 직접 조회 ==========
print("=" * 80)
print("📦 STEP 1: DB에서 직접 조회")
print("=" * 80)

with DatabaseConnection.get_connection() as conn:
    cursor = conn.cursor()
    
    # grid_id 조회
    cursor.execute("""
        SELECT grid_id FROM location_grid 
        ORDER BY SQRT(POWER(longitude - %s, 2) + POWER(latitude - %s, 2)) LIMIT 1
    """, (TEST_LON, TEST_LAT))
    grid_id = cursor.fetchone()['grid_id']
    print(f"🎯 Grid ID: {grid_id}")
    print()
    
    # 1) WSDI (wsdi_data - year 컬럼)
    print("1️⃣ WSDI (wsdi_data 테이블)")
    cursor.execute("""
        SELECT year, ssp2 as value FROM wsdi_data WHERE grid_id = %s AND year = %s
    """, (grid_id, TARGET_YEAR))
    wsdi_result = cursor.fetchone()
    wsdi_db = wsdi_result['value'] if wsdi_result else None
    print(f"   → DB 값: {wsdi_db}")
    print()
    
    # 2) TXx (tamax_data - observation_date 컬럼, MAX)
    print("2️⃣ TXx (tamax_data 테이블 - 연간 MAX)")
    cursor.execute("""
        SELECT MAX(ssp2) as value 
        FROM tamax_data 
        WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s
    """, (grid_id, TARGET_YEAR))
    txx_result = cursor.fetchone()
    txx_db = txx_result['value'] if txx_result else None
    print(f"   → DB 값: {txx_db}")
    print()
    
    # 3) SU25 (tamax_data - 25도 초과 COUNT)
    print("3️⃣ SU25 (tamax_data 테이블 - 최고기온 > 25도 COUNT)")
    cursor.execute("""
        SELECT COUNT(*) as value 
        FROM tamax_data 
        WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND ssp2 > 25
    """, (grid_id, TARGET_YEAR))
    su25_result = cursor.fetchone()
    su25_db = su25_result['value'] if su25_result else None
    print(f"   → DB 값: {su25_db}")
    print()
    
    # 4) TR25 (tamin_data - 25도 초과 COUNT)
    print("4️⃣ TR25 (tamin_data 테이블 - 최저기온 > 25도 COUNT)")
    cursor.execute("""
        SELECT COUNT(*) as value 
        FROM tamin_data 
        WHERE grid_id = %s AND EXTRACT(YEAR FROM observation_date) = %s AND ssp2 > 25
    """, (grid_id, TARGET_YEAR))
    tr25_result = cursor.fetchone()
    tr25_db = tr25_result['value'] if tr25_result else None
    print(f"   → DB 값: {tr25_db}")
    print()

# ========== Step 2: ClimateDataLoader로 조회 ==========
print("=" * 80)
print("📦 STEP 2: ClimateDataLoader.get_extreme_heat_data()")
print("=" * 80)

loader = ClimateDataLoader(scenario=SCENARIO)
loader_data = loader.get_extreme_heat_data(TEST_LAT, TEST_LON, TARGET_YEAR)

print(f"   data_source: {loader_data.get('data_source')}")
print(f"   1️⃣ wsdi (heat_wave_duration): {loader_data.get('wsdi')} / {loader_data.get('heat_wave_duration')}")
print(f"   2️⃣ TXx (annual_max_temp_celsius): {loader_data.get('annual_max_temp_celsius')}")
print(f"   3️⃣ SU25 (heatwave_days_per_year): {loader_data.get('heatwave_days_per_year')}")
print(f"   4️⃣ TR25 (tropical_nights): {loader_data.get('tropical_nights')}")
print()

# ========== Step 3: HazardDataCollector로 조회 ==========
print("=" * 80)
print("📦 STEP 3: HazardDataCollector.collect_data()")
print("=" * 80)

collector = HazardDataCollector(scenario=SCENARIO, target_year=TARGET_YEAR)
collected_data = collector.collect_data(TEST_LAT, TEST_LON, 'extreme_heat')
climate_data = collected_data.get('climate_data', {})

print(f"   data_source: {climate_data.get('data_source')}")
print(f"   1️⃣ wsdi / heat_wave_duration: {climate_data.get('wsdi')} / {climate_data.get('heat_wave_duration')}")
print(f"   2️⃣ annual_max_temp_celsius: {climate_data.get('annual_max_temp_celsius')}")
print(f"   3️⃣ heatwave_days_per_year: {climate_data.get('heatwave_days_per_year')}")
print(f"   4️⃣ tropical_nights: {climate_data.get('tropical_nights')}")
print()

# ========== Step 4: ExtremeHeatHScoreAgent 계산 ==========
print("=" * 80)
print("📦 STEP 4: ExtremeHeatHScoreAgent.calculate_hazard_score()")
print("=" * 80)

agent = ExtremeHeatHScoreAgent()
hazard_result = agent.calculate_hazard_score(collected_data)

print(f"   hazard_score (0-1): {hazard_result.get('hazard_score')}")
print(f"   hazard_score_100 (0-100): {hazard_result.get('hazard_score_100')}")
print(f"   hazard_level: {hazard_result.get('hazard_level')}")
print()

# 계산 상세 확인
calc_details = collected_data.get('calculation_details', {}).get('extreme_heat', {})
if calc_details:
    print("   📐 계산에 사용된 값:")
    print(f"      SU25 (폭염일수): {calc_details.get('su25')}")
    print(f"      WSDI (지속일수): {calc_details.get('wsdi')}")
    print(f"      TR25 (열대야): {calc_details.get('tr25')}")
    print()
    print("   📐 정규화된 값:")
    factors = calc_details.get('factors', {})
    print(f"      su25_norm: {factors.get('su25_norm')}")
    print(f"      wsdi_norm: {factors.get('wsdi_norm')}")
    print(f"      tr25_norm: {factors.get('tr25_norm')}")
    print(f"   📐 HCI = 0.3*su25 + 0.3*wsdi + 0.2*tr25 + 0.2*tx90p = {calc_details.get('hci')}")

# ========== 요약 ==========
print()
print("=" * 80)
print("📊 변수별 흐름 요약")
print("=" * 80)
print()
print("┌─────────┬─────────────────┬─────────────────┬─────────────────┐")
print("│ 변수    │ DB 직접 조회    │ ClimateLoader   │ Agent 사용값    │")
print("├─────────┼─────────────────┼─────────────────┼─────────────────┤")
print(f"│ WSDI    │ {str(wsdi_db):<15} │ {str(loader_data.get('wsdi')):<15} │ {str(calc_details.get('wsdi')):<15} │")
print(f"│ TXx     │ {str(txx_db):<15} │ {str(loader_data.get('annual_max_temp_celsius')):<15} │ (tx90p=su25)    │")
print(f"│ SU25    │ {str(su25_db):<15} │ {str(loader_data.get('heatwave_days_per_year')):<15} │ {str(calc_details.get('su25')):<15} │")
print(f"│ TR25    │ {str(tr25_db):<15} │ {str(loader_data.get('tropical_nights')):<15} │ {str(calc_details.get('tr25')):<15} │")
print("└─────────┴─────────────────┴─────────────────┴─────────────────┘")
print()

# 일치 여부 확인
all_match = True
mismatches = []

if wsdi_db is not None and loader_data.get('wsdi') != wsdi_db:
    mismatches.append(f"WSDI: DB={wsdi_db}, Loader={loader_data.get('wsdi')}")
    all_match = False

if txx_db is not None and loader_data.get('annual_max_temp_celsius') != txx_db:
    mismatches.append(f"TXx: DB={txx_db}, Loader={loader_data.get('annual_max_temp_celsius')}")
    all_match = False

if su25_db is not None and loader_data.get('heatwave_days_per_year') != su25_db:
    mismatches.append(f"SU25: DB={su25_db}, Loader={loader_data.get('heatwave_days_per_year')}")
    all_match = False
    
if tr25_db is not None and loader_data.get('tropical_nights') != tr25_db:
    mismatches.append(f"TR25: DB={tr25_db}, Loader={loader_data.get('tropical_nights')}")
    all_match = False

if all_match:
    print("✅ 모든 변수가 DB → Loader → Agent 경로로 정상 전달됨!")
else:
    print("⚠️ 불일치 발견:")
    for m in mismatches:
        print(f"   - {m}")

print()
print("테스트 완료!")
