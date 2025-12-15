#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exposure Agent DB 연동 테스트
"""

import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modelops.utils.hazard_data_collector import HazardDataCollector
from modelops.agents.exposure_calculate.extreme_heat_exposure_agent import ExtremeHeatExposureAgent
from modelops.agents.exposure_calculate.extreme_cold_exposure_agent import ExtremeColdExposureAgent
from modelops.agents.exposure_calculate.river_flood_exposure_agent import RiverFloodExposureAgent
from modelops.agents.exposure_calculate.urban_flood_exposure_agent import UrbanFloodExposureAgent
from modelops.agents.exposure_calculate.drought_exposure_agent import DroughtExposureAgent
from modelops.agents.exposure_calculate.wildfire_exposure_agent import WildfireExposureAgent
from modelops.agents.exposure_calculate.water_stress_exposure_agent import WaterStressExposureAgent
from modelops.agents.exposure_calculate.sea_level_rise_exposure_agent import SeaLevelRiseExposureAgent
from modelops.agents.exposure_calculate.typhoon_exposure_agent import TyphoonExposureAgent


EXPOSURE_AGENTS = {
    'extreme_heat': ExtremeHeatExposureAgent(),
    'extreme_cold': ExtremeColdExposureAgent(),
    'river_flood': RiverFloodExposureAgent(),
    'urban_flood': UrbanFloodExposureAgent(),
    'drought': DroughtExposureAgent(),
    'wildfire': WildfireExposureAgent(),
    'water_stress': WaterStressExposureAgent(),
    'sea_level_rise': SeaLevelRiseExposureAgent(),
    'typhoon': TyphoonExposureAgent(),
}


def test_exposure():
    """9개 리스크 타입 Exposure 테스트"""

    # 서울 좌표
    lat, lon = 37.5665, 126.978
    scenario = 'SSP245'
    target_year = 2030

    print("=" * 70)
    print("       Exposure Agent DB 연동 테스트")
    print("=" * 70)
    print(f"테스트 위치: 서울 ({lat}, {lon})")
    print(f"시나리오: {scenario}, 연도: {target_year}")
    print("=" * 70)

    # HazardDataCollector 초기화
    collector = HazardDataCollector(scenario=scenario, target_year=target_year)

    results = []

    for risk_type, agent in EXPOSURE_AGENTS.items():
        print(f"\n[{risk_type}]")
        print("-" * 50)

        try:
            # 1. 데이터 수집
            collected_data = collector.collect_data(lat=lat, lon=lon, risk_type=risk_type)

            building_data = collected_data.get('building_data', {})
            spatial_data = collected_data.get('spatial_data', {})

            # 데이터 수집 확인
            print(f"  building_data keys: {list(building_data.keys())[:5]}...")
            print(f"  spatial_data keys: {list(spatial_data.keys())[:5]}...")

            # 2. Exposure 계산
            e_result = agent.calculate_exposure(
                building_data=building_data,
                spatial_data=spatial_data,
                latitude=lat,
                longitude=lon
            )

            score = e_result.get('score', 0)
            data_source = e_result.get('data_source', 'unknown')

            print(f"  Exposure Score: {score}")
            print(f"  Data Source: {data_source}")

            # 주요 필드 출력
            for key, value in e_result.items():
                if key not in ['score', 'data_source'] and value is not None:
                    print(f"  {key}: {value}")

            results.append({
                'risk_type': risk_type,
                'score': score,
                'data_source': data_source,
                'status': 'success'
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
    print("─" * 70)
    print(f" 성공: {success_count}/9")

    return results


if __name__ == "__main__":
    test_exposure()
