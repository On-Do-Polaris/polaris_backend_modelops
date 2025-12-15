"""
hazard_probability_timeseries_batch.py 테스트 스크립트
- DB → Loader → HazardDataCollector → Agent 흐름 검증
- 9개 Hazard Agent 동작 및 DB 저장 테스트
- 실제 DB 격자점 좌표 사용
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from modelops.batch.hazard_probability_timeseries_batch import (
    calculate_hazard,
    save_hazard_results,
    RISK_TYPES
)

# 테스트 파라미터 (DB에서 가져온 실제 격자점)
TEST_LAT = 35.591000  # location_grid에서 가져온 값
TEST_LON = 129.303000
TEST_SCENARIO = 'SSP245'
TEST_YEAR = 2030

print("=" * 70)
print("hazard_probability_timeseries_batch.py 테스트")
print("=" * 70)
print(f"위치: ({TEST_LAT}, {TEST_LON}) - DB location_grid 실제 좌표")
print(f"시나리오: {TEST_SCENARIO}, 연도: {TEST_YEAR}")
print(f"리스크 타입: {len(RISK_TYPES)}개")
print("=" * 70)

hazard_results = []

print("\n[1단계] 9개 Hazard Agent 계산 테스트")
print("-" * 70)

for risk_type in RISK_TYPES:
    print(f"\n>>> {risk_type} 계산 중...")
    
    # H 계산
    h_result = calculate_hazard(TEST_LAT, TEST_LON, TEST_SCENARIO, TEST_YEAR, risk_type)
    
    if 'error' in h_result:
        print(f"    [H] ERROR: {h_result['error']}")
    else:
        print(f"    [H] Score: {h_result['hazard_score_100']:.2f} ({h_result['hazard_level']})")
    
    hazard_results.append({
        'latitude': TEST_LAT,
        'longitude': TEST_LON,
        'scenario': TEST_SCENARIO,
        'target_year': TEST_YEAR,
        'risk_type': risk_type,
        'hazard_score': h_result['hazard_score'],
        'hazard_score_100': h_result['hazard_score_100'],
        'hazard_level': h_result['hazard_level']
    })

print("\n" + "=" * 70)
print("[2단계] Hazard 결과 요약")
print("-" * 70)

print("\n--- Hazard (H) 결과 ---")
for r in hazard_results:
    print(f"  {r['risk_type']:20s}: {r['hazard_score_100']:6.2f} ({r['hazard_level']})")

print("\n" + "=" * 70)
print("[3단계] DB 저장 테스트")
print("-" * 70)

try:
    save_hazard_results(hazard_results)
    print(f"  Hazard 저장 완료: {len(hazard_results)}개 레코드")
except Exception as e:
    print(f"  Hazard 저장 실패: {e}")

print("\n" + "=" * 70)
print("테스트 완료")
print("=" * 70)
