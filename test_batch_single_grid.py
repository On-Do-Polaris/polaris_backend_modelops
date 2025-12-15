"""
hazard_probability_timeseries_batch.py 단일 격자점 테스트
- 실제 배치 스크립트의 run_batch() 함수 사용
- 1개 격자점, 1개 시나리오, 1개 연도로 테스트
- DB 값 추적: calculation_details, data_source 확인
"""
import sys
sys.path.insert(0, '.')
import logging

# DEBUG 레벨로 설정해서 DB 값 추적 로그 출력
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from modelops.batch.hazard_probability_timeseries_batch import (
    calculate_hazard, calculate_probability, RISK_TYPES
)

LAT, LON = 37.5665, 126.978
SCENARIO = 'SSP245'
YEAR = 2030

print("="*70)
print("  hazard_probability_timeseries_batch.py 단일 격자점 테스트")
print(f"  위치: ({LAT}, {LON}), 시나리오: {SCENARIO}, 연도: {YEAR}")
print("="*70)

print("\n" + "="*70)
print("  [Hazard] 9개 리스크 계산 + DB 값 추적")
print("="*70)

hazard_results = []
for risk_type in RISK_TYPES:
    result = calculate_hazard(LAT, LON, SCENARIO, YEAR, risk_type)
    hazard_results.append(result)

    # DB 값 추적 출력
    calc_details = result.get('calculation_details', {})
    data_source = result.get('data_source', 'unknown')
    score = result.get('hazard_score_100', 0)

    print(f"\n[{risk_type.upper()}]")
    print(f"  H Score: {score:.2f}/100")
    print(f"  Data Source: {data_source}")
    print(f"  Calculation Details: {calc_details}")

print("\n" + "="*70)
print("  [Probability] 9개 리스크 계산 + DB 값 추적")
print("="*70)

prob_results = []
for risk_type in RISK_TYPES:
    result = calculate_probability(LAT, LON, SCENARIO, YEAR, risk_type, 0.5)
    prob_results.append(result)

    # DB 값 추적 출력
    calc_details = result.get('calculation_details', {})
    data_source = result.get('data_source', 'unknown')
    aal = result.get('aal', 0)

    print(f"\n[{risk_type.upper()}]")
    print(f"  AAL: {aal:.6f}")
    print(f"  Data Source: {data_source}")
    print(f"  Method: {calc_details.get('method', 'N/A')}")
    print(f"  Total Years: {calc_details.get('total_years', 'N/A')}")

print("\n" + "="*70)
print("  요약: DB 데이터 사용 여부")
print("="*70)

for i, risk_type in enumerate(RISK_TYPES):
    h_source = hazard_results[i].get('data_source', 'unknown')
    p_source = prob_results[i].get('data_source', 'unknown')
    h_score = hazard_results[i].get('hazard_score_100', 0)
    p_aal = prob_results[i].get('aal', 0)

    h_status = "✅ DB" if h_source == 'DB' else f"⚠️ {h_source}"
    p_status = "✅ DB" if p_source == 'DB' else f"⚠️ {p_source}"

    print(f"  {risk_type:20s}: H={h_score:6.2f} ({h_status}), P={p_aal:.6f} ({p_status})")
