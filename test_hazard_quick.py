"""extreme_heat 1개만 빠르게 테스트"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modelops.batch.hazard_probability_timeseries_batch import calculate_hazard, save_hazard_results

LAT, LON = 35.591000, 129.303000

print(">>> extreme_heat 계산 중...")
h = calculate_hazard(LAT, LON, 'SSP245', 2030, 'extreme_heat')
print(f"    Score: {h['hazard_score_100']:.2f} ({h['hazard_level']})")
print(f"    raw_data: {h.get('raw_data', {})}")

# DB 저장 테스트
result = [{
    'latitude': LAT, 'longitude': LON, 'scenario': 'SSP245', 'target_year': 2030,
    'risk_type': 'extreme_heat',
    'hazard_score': h['hazard_score'],
    'hazard_score_100': h['hazard_score_100'],
    'hazard_level': h['hazard_level']
}]
print("\n>>> DB 저장 테스트...")
try:
    save_hazard_results(result)
    print("    저장 완료!")
except Exception as e:
    print(f"    저장 실패: {e}")
