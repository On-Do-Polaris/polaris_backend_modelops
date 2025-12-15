"""
evaal_ondemand_api.py 테스트 스크립트
- DB → Loader → HazardDataCollector → Agent 흐름 검증
- 9개 리스크 타입 E, V, AAL 계산 및 DB 저장 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from modelops.batch.evaal_ondemand_api import calculate_evaal_ondemand

# 테스트 파라미터
TEST_LAT = 37.5665  # 서울
TEST_LON = 126.9780
TEST_SCENARIO = 'SSP245'
TEST_YEAR = 2030

print("=" * 60)
print("evaal_ondemand_api.py 테스트")
print("=" * 60)
print(f"위치: ({TEST_LAT}, {TEST_LON})")
print(f"시나리오: {TEST_SCENARIO}, 연도: {TEST_YEAR}")
print("=" * 60)

# 테스트 실행 (DB 저장 없이 먼저)
print("\n[1단계] 계산만 테스트 (save_to_db=False)")
result = calculate_evaal_ondemand(
    latitude=TEST_LAT,
    longitude=TEST_LON,
    scenario=TEST_SCENARIO,
    target_year=TEST_YEAR,
    save_to_db=False
)

print(f"\n상태: {result.get('status')}")

if result.get('status') == 'success':
    print("\n[계산 결과 요약]")
    
    # Hazard 결과
    print("\n--- Hazard (H) ---")
    for risk_type, h_data in result['results']['hazard'].items():
        score = h_data.get('hazard_score_100', 0)
        level = h_data.get('hazard_level', 'N/A')
        print(f"  {risk_type}: {score:.2f} ({level})")
    
    # Exposure 결과
    print("\n--- Exposure (E) ---")
    for risk_type, e_data in result['results']['exposure'].items():
        score = e_data.get('exposure_score', 0)
        error = e_data.get('error', None)
        if error:
            print(f"  {risk_type}: ERROR - {error}")
        else:
            print(f"  {risk_type}: {score:.2f}")
    
    # Vulnerability 결과
    print("\n--- Vulnerability (V) ---")
    for risk_type, v_data in result['results']['vulnerability'].items():
        score = v_data.get('vulnerability_score', 0)
        level = v_data.get('vulnerability_level', 'N/A')
        print(f"  {risk_type}: {score:.2f} ({level})")
    
    # AAL 결과
    print("\n--- AAL ---")
    for risk_type, aal_data in result['results']['aal'].items():
        final_aal = aal_data.get('final_aal', 0)
        grade = aal_data.get('grade', 'N/A')
        print(f"  {risk_type}: {final_aal:.6f} ({grade})")
    
    # 통합 리스크
    print("\n--- Integrated Risk (H × E × V) ---")
    for risk_type, risk_data in result['results']['integrated_risk'].items():
        score = risk_data.get('integrated_risk_score', 0)
        level = risk_data.get('risk_level', 'N/A')
        print(f"  {risk_type}: {score:.2f} ({level})")
    
    # Summary
    print("\n--- Summary ---")
    summary = result.get('summary', {})
    print(f"  평균 Hazard: {summary.get('average_hazard', 0):.2f}")
    print(f"  평균 Exposure: {summary.get('average_exposure', 0):.2f}")
    print(f"  평균 Vulnerability: {summary.get('average_vulnerability', 0):.2f}")
    print(f"  평균 통합 리스크: {summary.get('average_integrated_risk', 0):.2f}")
    
    highest = summary.get('highest_integrated_risk', {})
    if highest:
        print(f"  최고 위험: {highest.get('risk_type')} ({highest.get('score'):.2f})")
    
    # Metadata
    print("\n--- Metadata ---")
    metadata = result.get('metadata', {})
    print(f"  계산 시간: {metadata.get('calculation_time', 0):.2f}초")
    print(f"  처리된 리스크: {metadata.get('total_risks_processed', 0)}개")
    
else:
    print(f"\n오류: {result.get('error')}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
