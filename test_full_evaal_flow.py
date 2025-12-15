"""
Full E-V-AAL Flow Test via evaal_ondemand_api.py
Tests real DB data flow for all 9 risk types
"""
import sys
sys.path.insert(0, '/Users/odong-i/Desktop/SKALA/FinalProject/DB_ALL/modelops')

from modelops.batch.evaal_ondemand_api import calculate_evaal_ondemand

# Test coordinates (광주광역시 서구 치평동 - 건물 데이터 있음)
TEST_LAT = 35.1595
TEST_LON = 126.8526

RISK_TYPES = [
    'extreme_heat', 'extreme_cold', 'drought',
    'river_flood', 'urban_flood', 'wildfire',
    'water_stress', 'sea_level_rise', 'typhoon'
]


def test_full_flow():
    print("="*70)
    print("Full E-V-AAL Flow Test via evaal_ondemand_api.py")
    print("="*70)
    print(f"Test Coordinates: ({TEST_LAT}, {TEST_LON})")
    print()

    try:
        result = calculate_evaal_ondemand(
            latitude=TEST_LAT,
            longitude=TEST_LON,
            scenario='SSP245',
            target_year=2050,
            risk_types=RISK_TYPES
        )

        # 결과 구조 확인
        print(f"Status: {result.get('status')}")
        results = result.get('results', {})

        for risk_type in RISK_TYPES:
            print(f"\n{'='*70}")
            print(f"[{risk_type.upper()}]")
            print('='*70)

            # Exposure (results['exposure'][risk_type])
            e_data = results.get('exposure', {}).get(risk_type, {})
            e_score = e_data.get('exposure_score', 'N/A')
            e_raw = e_data.get('raw_data', {})

            print(f"\n[Exposure] score={e_score}")
            if e_raw:
                print(f"  data_source: {e_raw.get('data_source', 'N/A')}")
                for key in ['landcover_type', 'distance_to_river_m', 'distance_to_coast_m',
                           'elevation_m', 'building_age_years', 'imperviousness_percent',
                           'main_purpose', 'water_dependency']:
                    if key in e_raw:
                        print(f"  {key}: {e_raw.get(key)}")

            # Vulnerability (results['vulnerability'][risk_type])
            v_data = results.get('vulnerability', {}).get(risk_type, {})
            v_score = v_data.get('vulnerability_score', 'N/A')
            v_raw = v_data.get('raw_data', {})

            print(f"\n[Vulnerability] score={v_score}")
            if v_raw:
                print(f"  data_source: {v_raw.get('data_source', 'N/A')}")
                factors = v_raw.get('factors', {})
                if factors:
                    for key in ['building_age', 'main_purpose', 'structure_type', 'ground_floors']:
                        if key in factors:
                            print(f"  {key}: {factors.get(key)}")

            # Hazard (results['hazard'][risk_type])
            h_data = results.get('hazard', {}).get(risk_type, {})
            print(f"\n[Hazard] score_100={h_data.get('hazard_score_100', 'N/A')}")

            # AAL (results['aal'][risk_type])
            aal_data = results.get('aal', {}).get(risk_type, {})
            print(f"[AAL] aal={aal_data.get('aal', 'N/A')}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_full_flow()
