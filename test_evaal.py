#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
evaal_ondemand_api.py DB 연동 테스트
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# evaal_ondemand_api에서 직접 import
from modelops.batch.evaal_ondemand_api import (
    calculate_exposure,
    calculate_vulnerability,
    calculate_aal,
    calculate_integrated_risk,
    calculate_evaal_ondemand
)


def test_single_exposure():
    """단일 Exposure 테스트"""
    lat, lon = 37.5665, 126.978
    scenario = 'SSP245'
    target_year = 2030

    print("=" * 70)
    print("       단일 Exposure 테스트 (extreme_heat)")
    print("=" * 70)

    result = calculate_exposure(
        latitude=lat,
        longitude=lon,
        scenario=scenario,
        target_year=target_year,
        risk_type='extreme_heat'
    )

    print(f"Result: {result}")
    return result


def test_all_exposure():
    """9개 리스크 Exposure 테스트"""
    lat, lon = 37.5665, 126.978
    scenario = 'SSP245'
    target_year = 2030

    risk_types = [
        'extreme_heat', 'extreme_cold', 'drought', 'river_flood',
        'urban_flood', 'wildfire', 'water_stress', 'sea_level_rise', 'typhoon'
    ]

    print("=" * 70)
    print("       9개 리스크 Exposure 테스트")
    print("=" * 70)
    print(f"위치: ({lat}, {lon}), 시나리오: {scenario}, 연도: {target_year}")
    print("=" * 70)

    results = []

    for risk_type in risk_types:
        print(f"\n[{risk_type}]")
        print("-" * 50)

        try:
            result = calculate_exposure(
                latitude=lat,
                longitude=lon,
                scenario=scenario,
                target_year=target_year,
                risk_type=risk_type
            )

            score = result.get('exposure_score', 0)
            raw_data = result.get('raw_data', {})
            data_source = raw_data.get('data_source', 'unknown')

            print(f"  Score: {score}")
            print(f"  Data Source: {data_source}")

            # 주요 raw_data 필드 출력 (5개까지)
            for i, (k, v) in enumerate(raw_data.items()):
                if i >= 5:
                    break
                if k not in ['data_source', 'score']:
                    print(f"  {k}: {v}")

            results.append({
                'risk_type': risk_type,
                'score': score,
                'data_source': data_source,
                'status': 'success' if 'error' not in result else result.get('error')
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                'risk_type': risk_type,
                'score': 0,
                'data_source': 'error',
                'status': str(e)
            })

    # 요약
    print("\n" + "=" * 70)
    print("       요약")
    print("=" * 70)
    print(f" Risk Type       │ Score │ Data Source │ Status")
    print("─" * 70)

    for r in results:
        status_mark = "✓" if r['status'] == 'success' else "✗"
        print(f" {r['risk_type']:<16} │ {r['score']:>5} │ {r['data_source']:<11} │ {status_mark}")

    success_count = sum(1 for r in results if r['status'] == 'success')
    db_count = sum(1 for r in results if 'DB' in str(r['data_source']).upper() or 'collected' in str(r['data_source']).lower())
    print("─" * 70)
    print(f" 성공: {success_count}/9, DB 데이터 사용: {db_count}/9")

    return results


def test_full_evaal():
    """전체 E, V, AAL 계산 테스트 (1개 리스크)"""
    lat, lon = 37.5665, 126.978
    scenario = 'SSP245'
    target_year = 2030

    print("\n" + "=" * 70)
    print("       전체 E, V, AAL 계산 테스트 (extreme_heat)")
    print("=" * 70)

    result = calculate_evaal_ondemand(
        latitude=lat,
        longitude=lon,
        scenario=scenario,
        target_year=target_year,
        risk_types=['extreme_heat'],
        save_to_db=False
    )

    if result.get('status') == 'success':
        exposure = result['results']['exposure'].get('extreme_heat', {})
        vulnerability = result['results']['vulnerability'].get('extreme_heat', {})
        aal = result['results']['aal'].get('extreme_heat', {})
        integrated = result['results']['integrated_risk'].get('extreme_heat', {})

        print(f"\n  [Exposure]")
        print(f"    Score: {exposure.get('exposure_score', 0)}")
        print(f"    Data: {exposure.get('raw_data', {}).get('data_source', 'unknown')}")

        print(f"\n  [Vulnerability]")
        print(f"    Score: {vulnerability.get('vulnerability_score', 0)}")
        print(f"    Level: {vulnerability.get('vulnerability_level', 'unknown')}")

        print(f"\n  [AAL]")
        print(f"    Base AAL: {aal.get('base_aal', 0)}")
        print(f"    Final AAL: {aal.get('final_aal', 0)}")
        print(f"    Grade: {aal.get('grade', '-')}")

        print(f"\n  [Integrated Risk]")
        print(f"    H × E × V Score: {integrated.get('integrated_risk_score', 0)}")
        print(f"    Level: {integrated.get('risk_level', 'unknown')}")
    else:
        print(f"  ERROR: {result.get('error')}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', choices=['single', 'all', 'full'], default='all')
    args = parser.parse_args()

    if args.test == 'single':
        test_single_exposure()
    elif args.test == 'all':
        test_all_exposure()
    elif args.test == 'full':
        test_full_evaal()
