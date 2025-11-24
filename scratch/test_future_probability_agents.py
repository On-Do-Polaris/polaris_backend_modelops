"""
미래 시나리오 기반 리스크 발생확률 테스트
대덕 데이터센터 (대전광역시 유성구) 기준

SSP 시나리오별 (SSP126, SSP245, SSP370, SSP585) 발생확률 계산
- 기간: 중기 (2026-2030), 장기 (2031-2050)
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
WAMIS_DATA_DIR = Path(__file__).parent / "wamis"

# SSP 시나리오 목록 (현재 데이터 있는 시나리오만)
SSP_SCENARIOS = ['SSP126', 'SSP585']

# 기간 설정
PERIODS = {
    'mid_term': list(range(2026, 2031)),  # 중기: 2026-2030
    'long_term': list(range(2031, 2051))  # 장기: 2031-2050
}


def get_nearest_idx(lat_arr, lon_arr, target_lat, target_lon):
    """가장 가까운 격자점 인덱스 반환"""
    lat_idx = np.argmin(np.abs(lat_arr - target_lat))
    lon_idx = np.argmin(np.abs(lon_arr - target_lon))
    return lat_idx, lon_idx


def load_yearly_data_by_scenario(var_name: str, start_year: int = 2021):
    """
    SSP 시나리오별 연간 데이터 로드
    Returns: {scenario: {year: value}}
    """
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

        # 연도별 딕셔너리로 변환
        year_dict = {}
        for i, val in enumerate(data):
            year_dict[start_year + i] = float(val)

        results[scenario] = year_dict

    return results


def load_monthly_data_by_scenario(var_name: str, start_year: int = 2021):
    """
    SSP 시나리오별 월간 데이터 로드
    Returns: {scenario: [monthly_values]}
    """
    results = {}

    for scenario in SSP_SCENARIOS:
        # 파일명 패턴 시도 (SSP126, SSP585 모두 지원)
        patterns = [
            f"{scenario}_{var_name}_gridraw_monthly_2021-2100.nc",
            f"AR6_{scenario}_5ENSMN_skorea_{var_name}_gridraw_monthly_2021_2100.nc"
        ]

        # SSP126과 SSP585 별도 처리 (SSP585는 AR6 형식만 있음)
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


def extract_period_data(yearly_dict: dict, years: list) -> list:
    """특정 기간의 데이터만 추출"""
    return [yearly_dict.get(y, 0) for y in years if y in yearly_dict]


def extract_period_monthly_data(monthly_list: list, years: list, start_year: int = 2021) -> list:
    """특정 기간의 월별 데이터 추출"""
    result = []
    for year in years:
        year_offset = year - start_year
        start_idx = year_offset * 12
        end_idx = start_idx + 12
        if start_idx >= 0 and end_idx <= len(monthly_list):
            result.extend(monthly_list[start_idx:end_idx])
    return result


def test_heat_wave(period_name: str, years: list):
    """폭염 (WSDI) 테스트"""
    print(f"\n{'='*60}")
    print(f"1. 폭염 (WSDI) - {period_name}")
    print(f"{'='*60}")

    wsdi_data = load_yearly_data_by_scenario('WSDI')
    agent = HighTemperatureProbabilityAgent()

    results = {}
    for scenario in SSP_SCENARIOS:
        if not wsdi_data.get(scenario):
            continue

        period_values = extract_period_data(wsdi_data[scenario], years)
        if not period_values:
            continue

        collected_data = {'climate_data': {'wsdi': period_values}}
        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] {len(period_values)}년, WSDI 범위: {min(period_values):.1f} ~ {max(period_values):.1f}")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_cold_wave(period_name: str, years: list):
    """한파 (CSDI) 테스트"""
    print(f"\n{'='*60}")
    print(f"2. 한파 (CSDI) - {period_name}")
    print(f"{'='*60}")

    csdi_data = load_yearly_data_by_scenario('CSDI')
    agent = ColdWaveProbabilityAgent()

    results = {}
    for scenario in SSP_SCENARIOS:
        if not csdi_data.get(scenario):
            continue

        period_values = extract_period_data(csdi_data[scenario], years)
        if not period_values:
            continue

        collected_data = {'climate_data': {'csdi': period_values}}
        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] {len(period_values)}년, CSDI 범위: {min(period_values):.1f} ~ {max(period_values):.1f}")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_drought(period_name: str, years: list):
    """가뭄 (SPEI12) 테스트"""
    print(f"\n{'='*60}")
    print(f"3. 가뭄 (SPEI12) - {period_name}")
    print(f"{'='*60}")

    spei_data = load_monthly_data_by_scenario('SPEI12')
    agent = DroughtProbabilityAgent()

    results = {}
    for scenario in SSP_SCENARIOS:
        if not spei_data.get(scenario):
            continue

        period_values = extract_period_monthly_data(spei_data[scenario], years)
        if not period_values:
            continue

        collected_data = {'climate_data': {'spei12': period_values}}
        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] {len(period_values)}개월, SPEI12 범위: {min(period_values):.2f} ~ {max(period_values):.2f}")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_inland_flood(period_name: str, years: list):
    """하천홍수 (RX1DAY) 테스트"""
    print(f"\n{'='*60}")
    print(f"4. 하천홍수 (RX1DAY) - {period_name}")
    print(f"{'='*60}")

    rx1day_data = load_yearly_data_by_scenario('RX1DAY')
    agent = InlandFloodProbabilityAgent()

    results = {}
    for scenario in SSP_SCENARIOS:
        if not rx1day_data.get(scenario):
            continue

        # baseline으로 전체 데이터 사용 (분위수 계산)
        all_values = list(rx1day_data[scenario].values())
        period_values = extract_period_data(rx1day_data[scenario], years)
        if not period_values:
            continue

        collected_data = {
            'climate_data': {
                'rx1day': period_values,
                'baseline_rx1day': all_values  # 분위수 계산용
            }
        }
        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] {len(period_values)}년, RX1DAY 범위: {min(period_values):.1f} ~ {max(period_values):.1f} mm")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_urban_flood(period_name: str, years: list):
    """도시홍수 (RAIN80) 테스트"""
    print(f"\n{'='*60}")
    print(f"5. 도시홍수 (RAIN80) - {period_name}")
    print(f"{'='*60}")

    rain80_data = load_yearly_data_by_scenario('RAIN80')
    agent = UrbanFloodProbabilityAgent()

    results = {}
    for scenario in SSP_SCENARIOS:
        if not rain80_data.get(scenario):
            continue

        period_values = extract_period_data(rain80_data[scenario], years)
        if not period_values:
            continue

        collected_data = {'climate_data': {'rain80': period_values}}
        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] {len(period_values)}년, RAIN80 범위: {min(period_values):.1f} ~ {max(period_values):.1f} 일")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_wildfire(period_name: str, years: list):
    """산불 (FWI) 테스트"""
    print(f"\n{'='*60}")
    print(f"6. 산불 (FWI) - {period_name}")
    print(f"{'='*60}")

    ta_data = load_monthly_data_by_scenario('TA')
    rhm_data = load_monthly_data_by_scenario('RHM')
    ws_data = load_monthly_data_by_scenario('WS')
    rn_data = load_monthly_data_by_scenario('RN')

    agent = WildfireProbabilityAgent()

    results = {}
    for scenario in SSP_SCENARIOS:
        if not all([ta_data.get(scenario), rhm_data.get(scenario),
                   ws_data.get(scenario), rn_data.get(scenario)]):
            continue

        ta_period = extract_period_monthly_data(ta_data[scenario], years)
        rhm_period = extract_period_monthly_data(rhm_data[scenario], years)
        ws_period = extract_period_monthly_data(ws_data[scenario], years)
        rn_period = extract_period_monthly_data(rn_data[scenario], years)

        if not ta_period:
            continue

        collected_data = {
            'climate_data': {
                'ta': ta_period,
                'rhm': rhm_period,
                'ws': ws_period,
                'rn': rn_period
            }
        }
        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] {len(ta_period)}개월")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_water_scarcity(period_name: str, years: list):
    """물부족 (WSI) 테스트 - Aqueduct BWS 기반 미래 추정"""
    print(f"\n{'='*60}")
    print(f"7. 물부족 (WSI) - {period_name} [Aqueduct BWS 기반]")
    print(f"{'='*60}")

    agent = WaterScarcityProbabilityAgent()

    # WAMIS 기준 용수이용량 데이터 (대전광역시)
    # 실제 데이터가 없으면 가상 데이터 사용
    baseline_withdrawal = 500_000_000  # 5억 m³/year (가상)

    # Aqueduct 4.0 BWS 데이터 (대전 지역 추정값)
    aqueduct_data = {
        'baseline': 0.15,  # 2019 baseline BWS
        'opt': {'2030': 0.12, '2050': 0.10, '2080': 0.08},   # SSP1-2.6 (낙관)
        'bau': {'2030': 0.18, '2050': 0.22, '2080': 0.28},   # SSP3-7.0 (중간)
        'pes': {'2030': 0.20, '2050': 0.30, '2080': 0.45}    # SSP5-8.5 (비관)
    }

    # SSP 시나리오 매핑
    ssp_mapping = {
        'SSP126': 'SSP1-2.6',
        'SSP245': 'SSP2-4.5',
        'SSP370': 'SSP3-7.0',
        'SSP585': 'SSP5-8.5'
    }

    # 가상 과거 데이터 (1991-2023)
    water_data = [{'year': y, 'withdrawal': baseline_withdrawal * (1 + 0.01 * (y - 2000))}
                  for y in range(1991, 2024)]

    # 가상 유량 데이터
    flow_data = [{'year': y, 'daily_flows': [100.0] * 365} for y in range(1991, 2024)]

    results = {}
    for scenario in SSP_SCENARIOS:
        ssp_scenario = ssp_mapping.get(scenario, 'SSP3-7.0')

        collected_data = {
            'water_data': water_data,
            'flow_data': flow_data,
            'baseline_years': list(range(1991, 2021)),
            'aqueduct_data': aqueduct_data,
            'ssp_scenario': ssp_scenario,
            'target_years': years
        }

        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        print(f"\n  [{scenario}] ({ssp_scenario})")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_typhoon(period_name: str, years: list):
    """태풍 (S_tc) 테스트 - IPCC AR6 기온 스케일링 기반"""
    print(f"\n{'='*60}")
    print(f"8. 태풍 (S_tc) - {period_name} [IPCC AR6 스케일링]")
    print(f"{'='*60}")

    agent = TyphoonProbabilityAgent()

    # 과거 Best Track 데이터 로드 (가상 데이터)
    # 실제로는 KMA API에서 가져와야 함
    historical_tracks = []
    for year in range(2015, 2025):
        # 연도별 2-3개 태풍 가정
        n_typhoons = np.random.randint(2, 4)
        for t in range(n_typhoons):
            tracks = []
            for i in range(20):  # 20개 관측점
                tracks.append({
                    'lat': 25.0 + i * 0.5 + np.random.randn() * 0.5,
                    'lon': 125.0 + i * 0.3 + np.random.randn() * 0.5,
                    'grade': np.random.choice(['TD', 'TS', 'STS', 'TY'], p=[0.3, 0.3, 0.25, 0.15]),
                    'r34_ne': 150 + np.random.randint(-50, 50),
                    'r34_se': 150 + np.random.randint(-50, 50),
                    'r34_sw': 150 + np.random.randint(-50, 50),
                    'r34_nw': 150 + np.random.randint(-50, 50)
                })
            historical_tracks.append({
                'year': year,
                'storm_id': f'{year}_{t+1}',
                'tracks': tracks
            })

    site_location = {'lon': DAEJEON_LON, 'lat': DAEJEON_LAT}

    # Baseline 초기화
    agent.initialize_baseline(historical_tracks, site_location, baseline_temp=14.2)

    # SSP 시나리오별 연평균 기온 로드
    ta_yearly = load_yearly_data_by_scenario('TA')

    results = {}
    for scenario in SSP_SCENARIOS:
        if not ta_yearly.get(scenario):
            continue

        # 해당 기간 기온 추출
        yearly_temps = {y: ta_yearly[scenario].get(y, 14.2) for y in years}

        collected_data = {
            'future_scenario': {
                'scenario': scenario,
                'target_years': years,
                'yearly_temps': yearly_temps,
                'site_location': site_location
            }
        }

        result = agent.calculate_probability(collected_data)
        results[scenario] = result

        avg_temp = np.mean(list(yearly_temps.values()))
        print(f"\n  [{scenario}] {len(years)}년, 평균기온: {avg_temp:.1f}°C")
        for bin_info in result['calculation_details']['bins']:
            print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")

    return results


def test_coastal_flood(period_name: str, years: list):
    """해수면상승 (ZOS) 테스트"""
    print(f"\n{'='*60}")
    print(f"9. 해수면상승 (ZOS) - {period_name}")
    print(f"{'='*60}")

    # ZOS 데이터는 별도 CMIP6 파일에서 로드
    # 여기서는 SSP126 데이터만 있다고 가정
    agent = CoastalFloodProbabilityAgent()

    # 실제 ZOS 데이터 로드 시도
    zos_file = KMA_DATA_DIR / "cmip6_ssp126_zos_yearly_2015-2100.nc"

    results = {}

    if zos_file.exists():
        ds = nc.Dataset(zos_file)
        lat_arr = ds.variables['lat'][:]
        lon_arr = ds.variables['lon'][:]

        # 가장 가까운 해양 격자점 찾기 (내륙이면 해안 근처)
        coastal_lat, coastal_lon = 36.45, 126.50  # 서해안 근처
        lat_idx = np.argmin(np.abs(lat_arr - coastal_lat))
        lon_idx = np.argmin(np.abs(lon_arr - coastal_lon))

        zos_data = ds.variables['zos'][:, lat_idx, lon_idx]
        years_in_file = ds.variables['time'][:]  # 2015-2100
        ds.close()

        # 연도별 데이터 구성
        zos_dict = {}
        start_year = 2015
        for i, val in enumerate(zos_data):
            if hasattr(val, 'data'):
                val = val.data
            zos_dict[start_year + i] = float(val)

        # 기간별 데이터 추출
        period_zos_data = []
        for year in years:
            if year in zos_dict:
                period_zos_data.append({
                    'year': year,
                    'zos_values': [zos_dict[year]]  # 연 단위이므로 단일 값
                })

        if period_zos_data:
            collected_data = {
                'ocean_data': {
                    'zos_data': period_zos_data,
                    'ground_level': 0.5  # 해안가 지반고 0.5m 가정
                }
            }

            result = agent.calculate_probability(collected_data)
            results['SSP126'] = result

            zos_values = [d['zos_values'][0] for d in period_zos_data]
            print(f"\n  [SSP126] {len(period_zos_data)}년, ZOS 범위: {min(zos_values):.2f} ~ {max(zos_values):.2f} cm")
            for bin_info in result['calculation_details']['bins']:
                print(f"    bin{bin_info['bin']}: {bin_info['probability']*100:.1f}% ({bin_info['range']})")
    else:
        print("  [WARN] ZOS 데이터 파일 없음")

    return results


def print_summary_table(all_results: dict, period_name: str):
    """결과 요약 테이블 출력"""
    print(f"\n\n{'='*80}")
    print(f"결과 요약: {period_name}")
    print(f"{'='*80}")

    risks = ['heat', 'cold', 'drought', 'inland_flood', 'urban_flood', 'wildfire', 'water_scarcity', 'typhoon', 'coastal_flood']
    risk_names = ['폭염', '한파', '가뭄', '하천홍수', '도시홍수', '산불', '물부족', '태풍', '해수면상승']

    # 헤더
    print(f"\n{'리스크':<12}", end='')
    for scenario in SSP_SCENARIOS:
        print(f"{scenario:>15}", end='')
    print()
    print("-" * 72)

    # 각 리스크별 최고 위험 bin 확률
    for risk, risk_name in zip(risks, risk_names):
        print(f"{risk_name:<12}", end='')

        for scenario in SSP_SCENARIOS:
            if risk in all_results and scenario in all_results[risk]:
                bins = all_results[risk][scenario]['calculation_details']['bins']
                # bin4 (또는 마지막 고위험 bin) 확률
                high_risk_prob = bins[-1]['probability'] * 100 if bins else 0
                # bin3 + bin4 합산
                if len(bins) >= 2:
                    high_risk_prob = (bins[-1]['probability'] + bins[-2]['probability']) * 100
                print(f"{high_risk_prob:>14.1f}%", end='')
            else:
                print(f"{'N/A':>15}", end='')
        print()

    print("=" * 72)
    print("* 고위험 확률: 상위 2개 bin의 합산 확률")


def main():
    print("=" * 60)
    print("미래 시나리오 기반 리스크 발생확률 테스트")
    print("위치: 대덕 데이터센터 (대전광역시 유성구)")
    print(f"좌표: ({DAEJEON_LAT}, {DAEJEON_LON})")
    print("=" * 60)

    all_results = {}

    # 중기 (2026-2030)
    print("\n\n" + "#" * 80)
    print("# 중기 전망 (2026-2030)")
    print("#" * 80)

    mid_years = PERIODS['mid_term']

    all_results_mid = {}
    all_results_mid['heat'] = test_heat_wave('중기 (2026-2030)', mid_years)
    all_results_mid['cold'] = test_cold_wave('중기 (2026-2030)', mid_years)
    all_results_mid['drought'] = test_drought('중기 (2026-2030)', mid_years)
    all_results_mid['inland_flood'] = test_inland_flood('중기 (2026-2030)', mid_years)
    all_results_mid['urban_flood'] = test_urban_flood('중기 (2026-2030)', mid_years)
    all_results_mid['wildfire'] = test_wildfire('중기 (2026-2030)', mid_years)
    all_results_mid['water_scarcity'] = test_water_scarcity('중기 (2026-2030)', mid_years)
    all_results_mid['typhoon'] = test_typhoon('중기 (2026-2030)', mid_years)
    all_results_mid['coastal_flood'] = test_coastal_flood('중기 (2026-2030)', mid_years)

    print_summary_table(all_results_mid, '중기 (2026-2030)')

    # 장기 (2031-2050)
    print("\n\n" + "#" * 80)
    print("# 장기 전망 (2031-2050)")
    print("#" * 80)

    long_years = PERIODS['long_term']

    all_results_long = {}
    all_results_long['heat'] = test_heat_wave('장기 (2031-2050)', long_years)
    all_results_long['cold'] = test_cold_wave('장기 (2031-2050)', long_years)
    all_results_long['drought'] = test_drought('장기 (2031-2050)', long_years)
    all_results_long['inland_flood'] = test_inland_flood('장기 (2031-2050)', long_years)
    all_results_long['urban_flood'] = test_urban_flood('장기 (2031-2050)', long_years)
    all_results_long['wildfire'] = test_wildfire('장기 (2031-2050)', long_years)
    all_results_long['water_scarcity'] = test_water_scarcity('장기 (2031-2050)', long_years)
    all_results_long['typhoon'] = test_typhoon('장기 (2031-2050)', long_years)
    all_results_long['coastal_flood'] = test_coastal_flood('장기 (2031-2050)', long_years)

    print_summary_table(all_results_long, '장기 (2031-2050)')

    # JSON 저장
    output = {
        'mid_term': {
            'period': '2026-2030',
            'results': {}
        },
        'long_term': {
            'period': '2031-2050',
            'results': {}
        }
    }

    # 결과 정리 (numpy array를 list로 변환)
    def convert_result(result_dict):
        converted = {}
        for scenario, result in result_dict.items():
            if result:
                converted[scenario] = {
                    'bin_probabilities': [float(p) for p in result['bin_probabilities']],
                    'bins': result['calculation_details']['bins']
                }
        return converted

    for risk in all_results_mid:
        if all_results_mid[risk]:
            output['mid_term']['results'][risk] = convert_result(all_results_mid[risk])

    for risk in all_results_long:
        if all_results_long[risk]:
            output['long_term']['results'][risk] = convert_result(all_results_long[risk])

    output_path = Path(__file__).parent / 'future_probability_results.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n\n결과 저장: {output_path}")


if __name__ == '__main__':
    main()
