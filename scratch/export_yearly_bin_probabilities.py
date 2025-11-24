"""
9대 리스크 SSP126/SSP585 연도별 bin 발생확률 추출
취약성 스케일링 테스트용 데이터 생성

출력: JSON 파일 (연도별 bin 확률)
"""
import sys
import json
from pathlib import Path
import numpy as np
import netCDF4 as nc

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aiops.agents.probability_calculate.high_temperature_probability_agent import HighTemperatureProbabilityAgent
from aiops.agents.probability_calculate.cold_wave_probability_agent import ColdWaveProbabilityAgent
from aiops.agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent
from aiops.agents.probability_calculate.inland_flood_probability_agent import InlandFloodProbabilityAgent
from aiops.agents.probability_calculate.urban_flood_probability_agent import UrbanFloodProbabilityAgent
from aiops.agents.probability_calculate.wildfire_probability_agent import WildfireProbabilityAgent
from aiops.agents.probability_calculate.water_scarcity_probability_agent import WaterScarcityProbabilityAgent
from aiops.agents.probability_calculate.typhoon_probability_agent import TyphoonProbabilityAgent
from aiops.agents.probability_calculate.coastal_flood_probability_agent import CoastalFloodProbabilityAgent

# 대덕 데이터센터 좌표
DAEJEON_LAT = 36.35
DAEJEON_LON = 127.38

# KMA 데이터 경로
KMA_DATA_DIR = Path(__file__).parent / "KMA"

# SSP 시나리오
SSP_SCENARIOS = ['SSP126', 'SSP585']

# 연도 범위
YEARS = list(range(2021, 2101))  # 2021-2100

# 윈도우 크기 (KDE용)
WINDOW_SIZE = 5


def get_nearest_idx(lat_arr, lon_arr, target_lat, target_lon):
    """가장 가까운 격자점 인덱스 반환"""
    lat_idx = np.argmin(np.abs(lat_arr - target_lat))
    lon_idx = np.argmin(np.abs(lon_arr - target_lon))
    return lat_idx, lon_idx


def load_yearly_data_by_scenario(var_name: str, start_year: int = 2021):
    """SSP 시나리오별 연간 데이터 로드"""
    results = {}

    for scenario in SSP_SCENARIOS:
        filename = f"{scenario}_{var_name}_gridraw_yearly_2021-2100.nc"
        filepath = KMA_DATA_DIR / filename

        if not filepath.exists():
            print(f"  [WARN] 파일 없음: {filename}")
            results[scenario] = {}
            continue

        ds = nc.Dataset(filepath)
        lat_arr = ds.variables['latitude'][:]
        lon_arr = ds.variables['longitude'][:]
        lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

        data = ds.variables[var_name][:, lat_idx, lon_idx]
        ds.close()

        if hasattr(data, 'data'):
            data = data.data

        year_dict = {}
        for i, val in enumerate(data):
            year_dict[start_year + i] = float(val)

        results[scenario] = year_dict

    return results


def load_monthly_data_by_scenario(var_name: str, start_year: int = 2021):
    """SSP 시나리오별 월간 데이터 로드"""
    results = {}

    for scenario in SSP_SCENARIOS:
        if scenario == 'SSP126':
            patterns = [
                f"SSP126_{var_name}_gridraw_monthly_2021-2100.nc",
                f"AR6_SSP126_5ENSMN_skorea_{var_name}_gridraw_monthly_2021_2100.nc"
            ]
        elif scenario == 'SSP585':
            patterns = [
                f"AR6_SSP585_5ENSMN_skorea_{var_name}_gridraw_monthly_2021_2100.nc",
                f"SSP585_{var_name}_gridraw_monthly_2021-2100.nc"
            ]
        else:
            patterns = [f"{scenario}_{var_name}_gridraw_monthly_2021-2100.nc"]

        filepath = None
        for pattern in patterns:
            test_path = KMA_DATA_DIR / pattern
            if test_path.exists():
                filepath = test_path
                break

        if filepath is None:
            print(f"  [WARN] {scenario} {var_name} 월별 데이터 없음")
            results[scenario] = []
            continue

        ds = nc.Dataset(filepath)
        lat_arr = ds.variables['latitude'][:]
        lon_arr = ds.variables['longitude'][:]
        lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

        data = ds.variables[var_name][:, lat_idx, lon_idx]
        ds.close()

        if hasattr(data, 'data'):
            data = data.data

        results[scenario] = list(data)

    return results


def calculate_yearly_probs(agent, yearly_data: dict, years: list, window: int = 5):
    """
    연도별 bin 확률 계산 (KDE 기반)
    윈도우 내 데이터로 확률 분포 추정
    """
    yearly_probs = {}
    all_years = sorted(yearly_data.keys())

    for year in years:
        if year not in yearly_data:
            continue

        # 윈도우 내 데이터 추출
        window_data = [
            yearly_data[y] for y in all_years
            if abs(y - year) <= window // 2 and y in yearly_data
        ]

        if len(window_data) < 3:
            continue

        # 에이전트로 확률 계산
        collected_data = {'climate_data': {get_data_key(agent): window_data}}

        # baseline 설정 (분위수 기반 에이전트용)
        if hasattr(agent, 'set_baseline_percentiles') and agent.percentile_thresholds is None:
            all_values = list(yearly_data.values())
            agent.set_baseline_percentiles(np.array(all_values))

        result = agent.calculate_probability(collected_data)
        yearly_probs[year] = result['bin_probabilities']

    return yearly_probs


def get_data_key(agent):
    """에이전트 타입에 따른 데이터 키 반환"""
    risk_type = agent.risk_type
    key_map = {
        '극심한 고온': 'wsdi',
        '극심한 한파': 'csdi',
        '가뭄': 'spei12',
        '하천 홍수': 'rx1day',
        '도시 홍수': 'rain80',
        '산불': 'fwi',
        '물부족': 'wsi',
        '태풍': 's_tc',
        '해수면 상승': 'zos'
    }
    return key_map.get(risk_type, 'data')


def calculate_monthly_yearly_probs(agent, monthly_data: list, years: list, start_year: int = 2021):
    """월별 데이터 기반 연도별 확률 계산"""
    yearly_probs = {}

    for year in years:
        year_offset = year - start_year
        start_idx = year_offset * 12
        end_idx = start_idx + 12

        if start_idx < 0 or end_idx > len(monthly_data):
            continue

        year_monthly = monthly_data[start_idx:end_idx]

        if len(year_monthly) < 12:
            continue

        data_key = get_data_key(agent)
        collected_data = {'climate_data': {data_key: year_monthly}}

        result = agent.calculate_probability(collected_data)
        yearly_probs[year] = result['bin_probabilities']

    return yearly_probs


def process_heat_wave():
    """1. 폭염 (WSDI)"""
    print("\n1. 폭염 (WSDI) 처리 중...")
    wsdi_data = load_yearly_data_by_scenario('WSDI')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not wsdi_data.get(scenario):
            continue

        agent = HighTemperatureProbabilityAgent()
        # baseline 설정
        all_values = np.array(list(wsdi_data[scenario].values()))
        agent.set_baseline_percentiles(all_values)

        yearly_probs = calculate_yearly_probs(agent, wsdi_data[scenario], YEARS, WINDOW_SIZE)
        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_cold_wave():
    """2. 한파 (CSDI)"""
    print("\n2. 한파 (CSDI) 처리 중...")
    csdi_data = load_yearly_data_by_scenario('CSDI')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not csdi_data.get(scenario):
            continue

        agent = ColdWaveProbabilityAgent()
        all_values = np.array(list(csdi_data[scenario].values()))
        agent.set_baseline_percentiles(all_values)

        yearly_probs = calculate_yearly_probs(agent, csdi_data[scenario], YEARS, WINDOW_SIZE)
        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_drought():
    """3. 가뭄 (SPEI12)"""
    print("\n3. 가뭄 (SPEI12) 처리 중...")
    spei_data = load_monthly_data_by_scenario('SPEI12')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not spei_data.get(scenario):
            continue

        agent = DroughtProbabilityAgent()
        yearly_probs = calculate_monthly_yearly_probs(agent, spei_data[scenario], YEARS)
        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_inland_flood():
    """4. 하천홍수 (RX1DAY)"""
    print("\n4. 하천홍수 (RX1DAY) 처리 중...")
    rx1day_data = load_yearly_data_by_scenario('RX1DAY')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not rx1day_data.get(scenario):
            continue

        agent = InlandFloodProbabilityAgent()
        yearly_probs = calculate_yearly_probs(agent, rx1day_data[scenario], YEARS, WINDOW_SIZE)
        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_urban_flood():
    """5. 도시홍수 (RAIN80)"""
    print("\n5. 도시홍수 (RAIN80) 처리 중...")
    rain80_data = load_yearly_data_by_scenario('RAIN80')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not rain80_data.get(scenario):
            continue

        agent = UrbanFloodProbabilityAgent()
        yearly_probs = calculate_yearly_probs(agent, rain80_data[scenario], YEARS, WINDOW_SIZE)
        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_wildfire():
    """6. 산불 (FWI)"""
    print("\n6. 산불 (FWI) 처리 중...")
    ta_data = load_monthly_data_by_scenario('TA')
    rhm_data = load_monthly_data_by_scenario('RHM')
    ws_data = load_monthly_data_by_scenario('WS')
    rn_data = load_monthly_data_by_scenario('RN')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not all([ta_data.get(scenario), rhm_data.get(scenario),
                   ws_data.get(scenario), rn_data.get(scenario)]):
            continue

        agent = WildfireProbabilityAgent()
        yearly_probs = {}

        for year in YEARS:
            year_offset = year - 2021
            start_idx = year_offset * 12
            end_idx = start_idx + 12

            if start_idx < 0 or end_idx > len(ta_data[scenario]):
                continue

            collected_data = {
                'climate_data': {
                    'ta': ta_data[scenario][start_idx:end_idx],
                    'rhm': rhm_data[scenario][start_idx:end_idx],
                    'ws': ws_data[scenario][start_idx:end_idx],
                    'rn': rn_data[scenario][start_idx:end_idx]
                }
            }

            result = agent.calculate_probability(collected_data)
            yearly_probs[year] = result['bin_probabilities']

        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_water_scarcity():
    """7. 물부족 (WSI) - Aqueduct 기반"""
    print("\n7. 물부족 (WSI) 처리 중...")

    agent = WaterScarcityProbabilityAgent()

    # 가상 데이터 (실제 데이터 필요시 교체)
    baseline_withdrawal = 500_000_000
    aqueduct_data = {
        'baseline': 0.15,
        'opt': {'2030': 0.12, '2050': 0.10, '2080': 0.08},
        'bau': {'2030': 0.18, '2050': 0.22, '2080': 0.28},
        'pes': {'2030': 0.20, '2050': 0.30, '2080': 0.45}
    }

    ssp_mapping = {
        'SSP126': 'SSP1-2.6',
        'SSP585': 'SSP5-8.5'
    }

    water_data = [{'year': y, 'withdrawal': baseline_withdrawal * (1 + 0.01 * (y - 2000))}
                  for y in range(1991, 2024)]
    flow_data = [{'year': y, 'daily_flows': [100.0] * 365} for y in range(1991, 2024)]

    results = {}
    for scenario in SSP_SCENARIOS:
        ssp_scenario = ssp_mapping.get(scenario, 'SSP3-7.0')
        yearly_probs = {}

        for year in YEARS:
            collected_data = {
                'water_data': water_data,
                'flow_data': flow_data,
                'baseline_years': list(range(1991, 2021)),
                'aqueduct_data': aqueduct_data,
                'ssp_scenario': ssp_scenario,
                'target_years': [year]
            }

            result = agent.calculate_probability(collected_data)
            yearly_probs[year] = result['bin_probabilities']

        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_typhoon():
    """8. 태풍 (S_tc) - IPCC 스케일링 기반"""
    print("\n8. 태풍 (S_tc) 처리 중...")

    agent = TyphoonProbabilityAgent()
    site_location = {'lon': DAEJEON_LON, 'lat': DAEJEON_LAT}

    # 가상 과거 데이터 (실제 Best Track 필요)
    np.random.seed(42)
    historical_tracks = []
    for year in range(2015, 2025):
        n_typhoons = np.random.randint(2, 4)
        for t in range(n_typhoons):
            tracks = []
            for i in range(20):
                tracks.append({
                    'lat': 25.0 + i * 0.5 + np.random.randn() * 0.5,
                    'lon': 125.0 + i * 0.3 + np.random.randn() * 0.5,
                    'grade': np.random.choice(['TD', 'TS', 'STS', 'TY'], p=[0.3, 0.3, 0.25, 0.15]),
                    'gale_long': 200, 'gale_short': 150, 'gale_dir': 45,
                    'storm_long': 100, 'storm_short': 80, 'storm_dir': 45
                })
            historical_tracks.append({
                'year': year, 'storm_id': f'{year}_{t+1}', 'tracks': tracks
            })

    agent.initialize_baseline(historical_tracks, site_location, baseline_temp=14.2)

    ta_yearly = load_yearly_data_by_scenario('TA')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not ta_yearly.get(scenario):
            continue

        yearly_probs = {}
        for year in YEARS:
            yearly_temps = {year: ta_yearly[scenario].get(year, 14.2)}

            collected_data = {
                'future_scenario': {
                    'scenario': scenario,
                    'target_years': [year],
                    'yearly_temps': yearly_temps,
                    'site_location': site_location
                }
            }

            result = agent.calculate_probability(collected_data)
            yearly_probs[year] = result['bin_probabilities']

        results[scenario] = yearly_probs
        print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

    return results


def process_coastal_flood():
    """9. 해수면상승 (ZOS)"""
    print("\n9. 해수면상승 (ZOS) 처리 중...")

    results = {}

    # SSP126 ZOS
    zos_file_126 = Path(__file__).parent / "zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc"
    # SSP585 ZOS
    zos_file_585 = KMA_DATA_DIR / "cmip6_ssp585_zos_yearly_2015-2100.nc"

    zos_files = {
        'SSP126': zos_file_126,
        'SSP585': zos_file_585
    }

    for scenario, zos_file in zos_files.items():
        if not zos_file.exists():
            print(f"  [WARN] {scenario} ZOS 파일 없음: {zos_file}")
            continue

        try:
            ds = nc.Dataset(zos_file)

            # 변수명 확인
            if 'lat' in ds.variables:
                lat_arr = ds.variables['lat'][:]
                lon_arr = ds.variables['lon'][:]
            elif 'latitude' in ds.variables:
                lat_arr = ds.variables['latitude'][:]
                lon_arr = ds.variables['longitude'][:]
            else:
                print(f"  [WARN] {scenario} 위경도 변수 찾을 수 없음")
                ds.close()
                continue

            coastal_lat, coastal_lon = 36.45, 126.50
            lat_idx = np.argmin(np.abs(lat_arr - coastal_lat))
            lon_idx = np.argmin(np.abs(lon_arr - coastal_lon))

            zos_data = ds.variables['zos'][:, lat_idx, lon_idx]
            ds.close()

            if hasattr(zos_data, 'data'):
                zos_data = zos_data.data

            agent = CoastalFloodProbabilityAgent()
            yearly_probs = {}

            start_year = 2015
            for year in YEARS:
                year_idx = year - start_year
                if year_idx < 0 or year_idx >= len(zos_data):
                    continue

                zos_val = float(zos_data[year_idx])

                collected_data = {
                    'ocean_data': {
                        'zos_data': [{'year': year, 'zos_values': [zos_val]}],
                        'ground_level': 0.5
                    }
                }

                result = agent.calculate_probability(collected_data)
                yearly_probs[year] = result['bin_probabilities']

            results[scenario] = yearly_probs
            print(f"  {scenario}: {len(yearly_probs)}년 처리 완료")

        except Exception as e:
            print(f"  [ERROR] {scenario} ZOS 처리 실패: {e}")

    return results


def main():
    print("=" * 60)
    print("9대 리스크 SSP126/SSP585 연도별 bin 발생확률 추출")
    print("위치: 대덕 데이터센터 (대전광역시 유성구)")
    print(f"기간: {YEARS[0]}-{YEARS[-1]}")
    print("=" * 60)

    all_results = {
        'metadata': {
            'location': '대전광역시 유성구 (대덕 데이터센터)',
            'lat': DAEJEON_LAT,
            'lon': DAEJEON_LON,
            'years': f'{YEARS[0]}-{YEARS[-1]}',
            'scenarios': SSP_SCENARIOS,
            'window_size': WINDOW_SIZE
        },
        'risks': {}
    }

    # 1. 폭염
    all_results['risks']['heat_wave'] = {
        'name': '폭염',
        'indicator': 'WSDI',
        'bin_labels': ['일반(<Q80)', '상위20%(Q80-Q90)', '상위10%(Q90-Q95)', '상위5%(Q95-Q99)', '극한1%(≥Q99)'],
        'data': process_heat_wave()
    }

    # 2. 한파
    all_results['risks']['cold_wave'] = {
        'name': '한파',
        'indicator': 'CSDI',
        'bin_labels': ['거의없음(<Q80)', '약함(Q80-Q90)', '중간(Q90-Q95)', '강함(Q95-Q99)', '극한(≥Q99)'],
        'data': process_cold_wave()
    }

    # 3. 가뭄
    all_results['risks']['drought'] = {
        'name': '가뭄',
        'indicator': 'SPEI12',
        'bin_labels': ['정상(>-1)', '중간(-1.5~-1)', '심각(-2~-1.5)', '극심(≤-2)'],
        'data': process_drought()
    }

    # 4. 하천홍수
    all_results['risks']['inland_flood'] = {
        'name': '하천홍수',
        'indicator': 'RX1DAY',
        'bin_labels': ['평범(<Q80)', '상위20%(Q80-Q95)', '상위5%(Q95-Q99)', '극한(≥Q99)'],
        'data': process_inland_flood()
    }

    # 5. 도시홍수
    all_results['risks']['urban_flood'] = {
        'name': '도시홍수',
        'indicator': 'RAIN80',
        'bin_labels': ['없음(0일)', '저빈도(1-2일)', '중간(3-4일)', '반복(5-7일)', '고빈도(≥8일)'],
        'data': process_urban_flood()
    }

    # 6. 산불
    all_results['risks']['wildfire'] = {
        'name': '산불',
        'indicator': 'FWI',
        'bin_labels': ['Low(0-11.2)', 'Moderate(11.2-21.3)', 'High(21.3-38)', 'VeryHigh(38-50)', 'Extreme(≥50)'],
        'data': process_wildfire()
    }

    # 7. 물부족
    all_results['risks']['water_scarcity'] = {
        'name': '물부족',
        'indicator': 'WSI',
        'bin_labels': ['Low(<0.2)', 'LowMed(0.2-0.4)', 'MedHigh(0.4-0.8)', 'High(≥0.8)'],
        'data': process_water_scarcity()
    }

    # 8. 태풍
    all_results['risks']['typhoon'] = {
        'name': '태풍',
        'indicator': 'S_tc',
        'bin_labels': ['영향없음(0)', '약함(0-5)', '중간(5-15)', '강함(>15)'],
        'data': process_typhoon()
    }

    # 9. 해수면상승
    all_results['risks']['coastal_flood'] = {
        'name': '해수면상승',
        'indicator': 'ZOS (inundation depth)',
        'bin_labels': ['없음(0m)', '경미(0-0.3m)', '중간(0.3-1m)', '심각(≥1m)'],
        'data': process_coastal_flood()
    }

    # int 키를 str로 변환 (JSON 호환)
    def convert_keys(obj):
        if isinstance(obj, dict):
            return {str(k): convert_keys(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_keys(i) for i in obj]
        else:
            return obj

    all_results = convert_keys(all_results)

    # JSON 저장
    output_path = Path(__file__).parent / 'yearly_bin_probabilities.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"결과 저장: {output_path}")
    print(f"{'='*60}")

    # 샘플 출력 (2030년, 2050년, 2080년)
    print("\n[샘플 출력: 2030, 2050, 2080년 bin 확률]")
    sample_years = ['2030', '2050', '2080']

    for risk_key, risk_data in all_results['risks'].items():
        print(f"\n{risk_data['name']} ({risk_data['indicator']}):")
        for scenario in SSP_SCENARIOS:
            if scenario not in risk_data['data']:
                continue
            print(f"  {scenario}:")
            for year in sample_years:
                if year in risk_data['data'][scenario]:
                    probs = risk_data['data'][scenario][year]
                    prob_str = ', '.join([f'{p*100:.1f}%' for p in probs])
                    print(f"    {year}: [{prob_str}]")


if __name__ == '__main__':
    main()
