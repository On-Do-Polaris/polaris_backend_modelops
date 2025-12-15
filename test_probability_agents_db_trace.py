"""
9개 Probability Agent DB 추적 테스트
- ClimateDataLoader.get_*_timeseries() → Agent._build_collected_data() → calculate_probability() 흐름 테스트
- DB에서 가져온 값이 Agent에서 올바르게 사용되는지 확인
- probability_results 테이블에 저장 확인
"""

import sys
sys.path.insert(0, '.')

from modelops.data_loaders.climate_data_loader import ClimateDataLoader
from modelops.database.connection import DatabaseConnection
from modelops.agents.probability_calculate.extreme_heat_probability_agent import ExtremeHeatProbabilityAgent
from modelops.agents.probability_calculate.extreme_cold_probability_agent import ExtremeColdProbabilityAgent
from modelops.agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent
from modelops.agents.probability_calculate.river_flood_probability_agent import RiverFloodProbabilityAgent
from modelops.agents.probability_calculate.urban_flood_probability_agent import UrbanFloodProbabilityAgent
from modelops.agents.probability_calculate.wildfire_probability_agent import WildfireProbabilityAgent
from modelops.agents.probability_calculate.water_stress_probability_agent import WaterStressProbabilityAgent
from modelops.agents.probability_calculate.sea_level_rise_probability_agent import SeaLevelRiseProbabilityAgent
from modelops.agents.probability_calculate.typhoon_probability_agent import TyphoonProbabilityAgent

# 테스트 파라미터
LAT, LON = 37.5665, 126.978  # 서울
SCENARIO = 'SSP245'
START_YEAR = 2021
END_YEAR = 2050


def test_agent_with_trace(risk_type: str, agent, climate_loader: ClimateDataLoader,
                          timeseries_method_name: str, key_vars: list):
    """
    에이전트 테스트 및 변수 추적

    Args:
        risk_type: 리스크 타입
        agent: Probability 에이전트 인스턴스
        climate_loader: ClimateDataLoader 인스턴스
        timeseries_method_name: 시계열 메서드 이름
        key_vars: 추적할 핵심 변수 리스트
    """
    print(f"\n{'='*60}")
    print(f"  [{risk_type.upper()}] Probability Agent 테스트")
    print(f"{'='*60}")

    try:
        # 1. ClimateDataLoader에서 시계열 데이터 가져오기
        method = getattr(climate_loader, timeseries_method_name, None)
        if method:
            if 'timeseries' in timeseries_method_name:
                timeseries_data = method(LAT, LON, START_YEAR, END_YEAR)
            else:
                timeseries_data = method(LAT, LON)
        else:
            print(f"  ❌ {timeseries_method_name} 메서드가 없습니다.")
            return None

        print(f"\n  [1] ClimateDataLoader.{timeseries_method_name}() 결과:")
        for key in key_vars:
            value = timeseries_data.get(key)
            if isinstance(value, list):
                if len(value) > 5:
                    print(f"      {key}: [{value[0]:.2f}, {value[1]:.2f}, ... , {value[-1]:.2f}] ({len(value)}개)")
                else:
                    print(f"      {key}: {value}")
            else:
                print(f"      {key}: {value}")

        # 2. Agent._build_collected_data() 호출
        collected_data = agent._build_collected_data(timeseries_data)

        print(f"\n  [2] Agent._build_collected_data() 결과:")
        climate_data = collected_data.get('climate_data', {})
        for key in key_vars:
            value = climate_data.get(key)
            if value:
                if isinstance(value, list):
                    if len(value) > 5:
                        print(f"      {key}: [{value[0]:.2f}, {value[1]:.2f}, ... , {value[-1]:.2f}] ({len(value)}개)")
                    else:
                        print(f"      {key}: {value}")
                else:
                    print(f"      {key}: {value}")

        # 3. calculate_probability() 호출
        result = agent.calculate_probability(collected_data)

        print(f"\n  [3] calculate_probability() 결과:")
        print(f"      AAL: {result.get('aal', 0.0):.6f}")
        print(f"      bin_probabilities: {result.get('bin_probabilities', [])}")
        print(f"      status: {result.get('status', 'unknown')}")

        # 4. calculation_details 확인
        calc_details = result.get('calculation_details', {})
        print(f"\n  [4] calculation_details:")
        print(f"      method: {calc_details.get('method', 'N/A')}")
        print(f"      total_years: {calc_details.get('total_years', 'N/A')}")
        if 'bins' in calc_details:
            for bin_info in calc_details['bins'][:3]:  # 처음 3개만
                print(f"      bin{bin_info['bin']}: range={bin_info['range']}, prob={bin_info['probability']:.4f}, sample_count={bin_info.get('sample_count', 0)}")

        return result

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("="*60)
    print("  9개 Probability Agent DB 추적 테스트")
    print(f"  Location: ({LAT}, {LON})")
    print(f"  Scenario: {SCENARIO}, Period: {START_YEAR}-{END_YEAR}")
    print("="*60)

    # ClimateDataLoader 생성
    climate_loader = ClimateDataLoader(scenario=SCENARIO)

    # 9개 에이전트 정의: (risk_type, agent, timeseries_method, key_vars)
    agents = [
        ('extreme_heat', ExtremeHeatProbabilityAgent(), 'get_extreme_heat_timeseries', ['wsdi', 'txx']),
        ('extreme_cold', ExtremeColdProbabilityAgent(), 'get_extreme_cold_timeseries', ['csdi', 'tnn']),
        ('drought', DroughtProbabilityAgent(), 'get_drought_timeseries', ['spei12', 'cdd']),
        ('river_flood', RiverFloodProbabilityAgent(), 'get_flood_timeseries', ['rx1day', 'rx5day']),
        ('urban_flood', UrbanFloodProbabilityAgent(), 'get_flood_timeseries', ['rain80']),
        ('wildfire', WildfireProbabilityAgent(), 'get_wildfire_timeseries', ['ta', 'rhm', 'ws', 'rn']),
        ('water_stress', WaterStressProbabilityAgent(), 'get_water_stress_data', ['annual_rainfall_mm', 'cdd']),
        ('sea_level_rise', SeaLevelRiseProbabilityAgent(), 'get_sea_level_rise_timeseries', ['slr']),
        ('typhoon', TyphoonProbabilityAgent(), 'get_typhoon_data', ['typhoon_frequency', 'max_wind_speed_ms']),
    ]

    all_results = []

    for risk_type, agent, timeseries_method, key_vars in agents:
        result = test_agent_with_trace(risk_type, agent, climate_loader, timeseries_method, key_vars)
        if result and result.get('status') == 'completed':
            # numpy 타입을 Python 타입으로 변환
            bin_probs = result.get('bin_probabilities', [])
            bin_probs_native = [float(p) for p in bin_probs]
            aal = result.get('aal', 0.0)
            aal_native = float(aal) if aal is not None else 0.0

            all_results.append({
                'latitude': LAT,
                'longitude': LON,
                'scenario': SCENARIO,
                'target_year': 2030,  # 대표 연도
                'risk_type': risk_type,
                'aal': aal_native,
                'bin_probabilities': bin_probs_native
            })

    # 최종 요약
    print("\n" + "="*60)
    print("  최종 요약")
    print("="*60)

    success_count = 0
    for r in all_results:
        if r['aal'] is not None:
            print(f"  ✅ {r['risk_type']:20s}: AAL={r['aal']:.6f}")
            success_count += 1
        else:
            print(f"  ❌ {r['risk_type']:20s}: 계산 실패")

    print(f"\n  성공: {success_count}/9 에이전트")

    # DB 저장 테스트
    if all_results:
        print("\n" + "="*60)
        print("  DB 저장 테스트 (probability_results)")
        print("="*60)

        try:
            DatabaseConnection.save_probability_results(all_results)
            print(f"  ✅ {len(all_results)}개 결과 저장 완료!")

            # 저장 확인
            import psycopg2
            from psycopg2.extras import RealDictCursor
            from modelops.config.settings import settings

            conn_str = (
                f"host={settings.database_host} "
                f"port={settings.database_port} "
                f"dbname={settings.database_name} "
                f"user={settings.database_user} "
                f"password={settings.database_password}"
            )

            with psycopg2.connect(conn_str, cursor_factory=RealDictCursor) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT risk_type, target_year, ssp245_aal, ssp245_bin_probs
                    FROM probability_results
                    WHERE latitude = %s AND longitude = %s
                    ORDER BY risk_type
                """, (LAT, LON))

                rows = cursor.fetchall()
                if rows:
                    print(f"\n  저장된 데이터 확인 ({len(rows)}개):")
                    for row in rows:
                        aal = row['ssp245_aal'] or 0.0
                        bin_probs = row['ssp245_bin_probs']
                        print(f"    {row['risk_type']:20s}: AAL={aal:.6f}, bins={bin_probs}")
                else:
                    print("  ⚠️ 저장된 데이터가 없습니다.")

        except Exception as e:
            print(f"  ❌ DB 저장 실패: {e}")


if __name__ == "__main__":
    main()
