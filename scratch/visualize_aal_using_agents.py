"""
SSP 시나리오별 연도별 리스크 발생확률 및 AAL 시각화
probability_calculate 에이전트 로직만 사용

V_score = 1.0, IR = 0.0 고정
AAL = Σ P[i] × DR[i] × (1 - IR)
"""
import sys
from pathlib import Path
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 설정
KMA_DATA_DIR = Path(__file__).parent / 'KMA'
OUTPUT_DIR = Path(__file__).parent / 'scenario_comparison'
OUTPUT_DIR.mkdir(exist_ok=True)

SSP_SCENARIOS = ['SSP126', 'SSP585']
SCENARIO_COLORS = {'SSP126': '#2ecc71', 'SSP585': '#e74c3c'}
SCENARIO_LABELS = {'SSP126': 'SSP1-2.6 (저탄소)', 'SSP585': 'SSP5-8.5 (고탄소)'}
YEARS = list(range(2021, 2101))
WINDOW_SIZE = 5

# 대전 유성구 좌표
TARGET_LAT, TARGET_LON = 36.35, 127.38


def get_nearest_idx(lat_arr, lon_arr, target_lat, target_lon):
    """가장 가까운 격자점 인덱스 반환"""
    lat_idx = np.argmin(np.abs(lat_arr - target_lat))
    lon_idx = np.argmin(np.abs(lon_arr - target_lon))
    return lat_idx, lon_idx


def load_yearly_data(var_name, scenario):
    """NetCDF 연간 데이터 로드"""
    patterns = [
        f'{scenario}_{var_name}_gridraw_yearly_2021-2100.nc',
        f'AR6_{scenario}_5ENSMN_skorea_{var_name}_gridraw_yearly_2021_2100.nc'
    ]

    for pattern in patterns:
        filepath = KMA_DATA_DIR / pattern
        if filepath.exists():
            ds = nc.Dataset(filepath)
            lat_arr = ds.variables['latitude'][:]
            lon_arr = ds.variables['longitude'][:]
            lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, TARGET_LAT, TARGET_LON)
            data = ds.variables[var_name][:, lat_idx, lon_idx]
            ds.close()
            if hasattr(data, 'data'):
                data = data.data
            return {2021 + i: float(data[i]) for i in range(len(data))}
    return None


def load_monthly_data(var_name, scenario):
    """NetCDF 월간 데이터 로드"""
    patterns = [
        f'{scenario}_{var_name}_gridraw_monthly_2021-2100.nc',
        f'AR6_{scenario}_5ENSMN_skorea_{var_name}_gridraw_monthly_2021_2100.nc'
    ]

    for pattern in patterns:
        filepath = KMA_DATA_DIR / pattern
        if filepath.exists():
            ds = nc.Dataset(filepath)
            lat_arr = ds.variables['latitude'][:]
            lon_arr = ds.variables['longitude'][:]
            lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, TARGET_LAT, TARGET_LON)
            data = ds.variables[var_name][:, lat_idx, lon_idx]
            ds.close()
            if hasattr(data, 'data'):
                data = data.data
            return list(data)
    return None


def calculate_aal(bin_probs, dr_intensity):
    """AAL 계산: AAL = Σ P[i] × DR[i]"""
    return sum(p * dr for p, dr in zip(bin_probs, dr_intensity))


def process_yearly_risk(agent, yearly_data, years, window_size=5):
    """
    연간 데이터 기반 리스크 처리
    에이전트의 calculate_probability 메서드 직접 사용
    """
    results = {'years': [], 'aal': [], 'bin_probs': []}

    if not yearly_data:
        return results

    all_years = sorted(yearly_data.keys())

    # 분위수 기반 에이전트는 baseline 설정
    if hasattr(agent, 'set_baseline_percentiles') and agent.percentile_thresholds is None:
        all_values = np.array(list(yearly_data.values()))
        agent.set_baseline_percentiles(all_values)

    for year in years:
        if year not in yearly_data:
            continue

        # 윈도우 데이터 추출
        window_data = [
            yearly_data[y] for y in all_years
            if abs(y - year) <= window_size // 2 and y in yearly_data
        ]

        if len(window_data) < 3:
            continue

        # 데이터 키 결정
        data_key = get_data_key(agent)
        collected_data = {'climate_data': {data_key: window_data}}

        # 에이전트로 확률 계산
        result = agent.calculate_probability(collected_data)
        bin_probs = result['bin_probabilities']

        # AAL 계산
        aal = calculate_aal(bin_probs, agent.dr_intensity)

        results['years'].append(year)
        results['aal'].append(aal * 100)  # 퍼센트
        results['bin_probs'].append(bin_probs)

    return results


def process_monthly_risk(agent, monthly_data, years, start_year=2021):
    """
    월간 데이터 기반 리스크 처리 (가뭄, 산불)
    에이전트의 calculate_probability 메서드 직접 사용
    """
    results = {'years': [], 'aal': [], 'bin_probs': []}

    if not monthly_data:
        return results

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

        # 에이전트로 확률 계산
        result = agent.calculate_probability(collected_data)
        bin_probs = result['bin_probabilities']

        # AAL 계산
        aal = calculate_aal(bin_probs, agent.dr_intensity)

        results['years'].append(year)
        results['aal'].append(aal * 100)
        results['bin_probs'].append(bin_probs)

    return results


def process_wildfire(agent, scenario, years):
    """산불 처리 (TA, RHM, WS, RN 4개 변수 필요)"""
    results = {'years': [], 'aal': [], 'bin_probs': []}

    ta_data = load_monthly_data('TA', scenario)
    rhm_data = load_monthly_data('RHM', scenario)
    ws_data = load_monthly_data('WS', scenario)
    rn_data = load_monthly_data('RN', scenario)

    if not all([ta_data, rhm_data, ws_data, rn_data]):
        return results

    for year in years:
        year_offset = year - 2021
        start_idx = year_offset * 12
        end_idx = start_idx + 12

        if start_idx < 0 or end_idx > len(ta_data):
            continue

        collected_data = {
            'climate_data': {
                'ta': ta_data[start_idx:end_idx],
                'rhm': rhm_data[start_idx:end_idx],
                'ws': ws_data[start_idx:end_idx],
                'rn': rn_data[start_idx:end_idx]
            }
        }

        # 에이전트로 확률 계산
        result = agent.calculate_probability(collected_data)
        bin_probs = result['bin_probabilities']

        # AAL 계산
        aal = calculate_aal(bin_probs, agent.dr_intensity)

        results['years'].append(year)
        results['aal'].append(aal * 100)
        results['bin_probs'].append(bin_probs)

    return results


def get_data_key(agent):
    """에이전트 타입에 따른 데이터 키 반환"""
    key_map = {
        '극심한 고온': 'wsdi',
        '극심한 한파': 'csdi',
        '가뭄': 'spei12',
        '하천 홍수': 'rx1day',
        '도시 홍수': 'rain80',
        '산불': 'fwi',
        '물부족': 'wsi'
    }
    return key_map.get(agent.risk_type, 'data')


def get_bin_labels_safe(agent):
    """에이전트에서 bin 레이블 가져오기 (fallback 포함)"""
    if hasattr(agent, 'get_bin_labels'):
        return agent.get_bin_labels()

    # fallback: bins에서 레이블 생성
    labels = []
    for i, (low, high) in enumerate(agent.bins):
        if high == float('inf'):
            labels.append(f'bin{i+1} (≥{low})')
        else:
            labels.append(f'bin{i+1} ({low}-{high})')
    return labels


def plot_risk_aal(risk_name, indicator, scenario_results, bin_labels, output_path):
    """
    개별 리스크 AAL 시각화
    - 좌상: AAL 추이
    - 우상: Bin별 발생확률
    - 하단: Bin별 분포 (스택 차트)
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{risk_name} ({indicator}) - SSP 시나리오별 연도별 발생확률 및 AAL', fontsize=14, fontweight='bold')

    # 좌상: AAL 추이
    ax1 = axes[0, 0]
    for scenario in SSP_SCENARIOS:
        if scenario in scenario_results and scenario_results[scenario]['years']:
            ax1.plot(scenario_results[scenario]['years'],
                    scenario_results[scenario]['aal'],
                    color=SCENARIO_COLORS[scenario],
                    label=SCENARIO_LABELS[scenario],
                    linewidth=1.5)
    ax1.set_xlabel('연도')
    ax1.set_ylabel('AAL (%)')
    ax1.set_title('연평균손실률 (AAL) 추이')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 우상: Bin별 발생확률
    ax2 = axes[0, 1]
    n_bins = len(bin_labels)
    for scenario in SSP_SCENARIOS:
        if scenario in scenario_results and scenario_results[scenario]['bin_probs']:
            years = scenario_results[scenario]['years']
            bin_probs = np.array(scenario_results[scenario]['bin_probs'])

            linestyles = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]
            for i in range(n_bins):
                ax2.plot(years, bin_probs[:, i] * 100,
                        color=SCENARIO_COLORS[scenario],
                        linestyle=linestyles[i % len(linestyles)],
                        label=f'{SCENARIO_LABELS[scenario]} - {bin_labels[i]}',
                        alpha=0.7,
                        linewidth=1)
    ax2.set_xlabel('연도')
    ax2.set_ylabel('확률 (%)')
    ax2.set_title('Bin별 발생확률')
    ax2.legend(fontsize=7, loc='upper right', ncol=2)
    ax2.grid(True, alpha=0.3)

    # 하단: Bin별 분포 (스택 차트)
    colors = plt.cm.YlOrRd(np.linspace(0.2, 0.8, n_bins))

    for idx, scenario in enumerate(SSP_SCENARIOS):
        ax = axes[1, idx]
        if scenario in scenario_results and scenario_results[scenario]['bin_probs']:
            years = scenario_results[scenario]['years']
            bin_probs = np.array(scenario_results[scenario]['bin_probs']) * 100

            ax.stackplot(years, bin_probs.T, labels=bin_labels, colors=colors, alpha=0.8)
            ax.set_xlabel('연도')
            ax.set_ylabel('확률 (%)')
            ax.set_title(f'{SCENARIO_LABELS[scenario]} - Bin별 분포')
            ax.legend(fontsize=8, loc='upper left')
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'  저장: {output_path}')


def plot_all_risks_summary(all_results, output_path):
    """전체 리스크 AAL 요약 시각화"""
    n_risks = len(all_results)
    cols = 3
    rows = (n_risks + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
    axes = axes.flatten()

    for idx, (risk_key, risk_data) in enumerate(all_results.items()):
        ax = axes[idx]

        for scenario in SSP_SCENARIOS:
            if scenario in risk_data['results'] and risk_data['results'][scenario]['years']:
                ax.plot(risk_data['results'][scenario]['years'],
                       risk_data['results'][scenario]['aal'],
                       color=SCENARIO_COLORS[scenario],
                       label=SCENARIO_LABELS[scenario],
                       linewidth=1.5)

        ax.set_title(risk_data['name'])
        ax.set_xlabel('연도')
        ax.set_ylabel('AAL (%)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # 빈 축 숨기기
    for idx in range(len(all_results), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle('7대 기후 리스크 AAL 추이 (SSP126 vs SSP585)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'  저장: {output_path}')


def main():
    print("=" * 60)
    print("SSP 시나리오별 AAL 시각화 (probability_calculate 에이전트 사용)")
    print("=" * 60)

    all_results = {}

    # 1. 폭염 (WSDI)
    print("\n1. 폭염 (WSDI) 처리 중...")
    agent = HighTemperatureProbabilityAgent()
    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        wsdi_data = load_yearly_data('WSDI', scenario)
        if wsdi_data:
            # 새 에이전트 인스턴스로 baseline 재설정
            agent = HighTemperatureProbabilityAgent()
            scenario_results[scenario] = process_yearly_risk(agent, wsdi_data, YEARS, WINDOW_SIZE)
            print(f'  {scenario}: {len(scenario_results[scenario]["years"])}년 처리')

    plot_risk_aal('폭염', 'WSDI', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'heat_wave_aal_agents.png')
    all_results['heat_wave'] = {'name': '폭염', 'results': scenario_results}

    # 2. 한파 (CSDI)
    print("\n2. 한파 (CSDI) 처리 중...")
    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        csdi_data = load_yearly_data('CSDI', scenario)
        if csdi_data:
            agent = ColdWaveProbabilityAgent()
            scenario_results[scenario] = process_yearly_risk(agent, csdi_data, YEARS, WINDOW_SIZE)
            print(f'  {scenario}: {len(scenario_results[scenario]["years"])}년 처리')

    plot_risk_aal('한파', 'CSDI', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'cold_wave_aal_agents.png')
    all_results['cold_wave'] = {'name': '한파', 'results': scenario_results}

    # 3. 가뭄 (SPEI12)
    print("\n3. 가뭄 (SPEI12) 처리 중...")
    agent = DroughtProbabilityAgent()
    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        spei_data = load_monthly_data('SPEI12', scenario)
        if spei_data:
            scenario_results[scenario] = process_monthly_risk(agent, spei_data, YEARS)
            print(f'  {scenario}: {len(scenario_results[scenario]["years"])}년 처리')

    plot_risk_aal('가뭄', 'SPEI12', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'drought_aal_agents.png')
    all_results['drought'] = {'name': '가뭄', 'results': scenario_results}

    # 4. 하천홍수 (RX1DAY)
    print("\n4. 하천홍수 (RX1DAY) 처리 중...")
    agent = InlandFloodProbabilityAgent()
    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        rx1day_data = load_yearly_data('RX1DAY', scenario)
        if rx1day_data:
            scenario_results[scenario] = process_yearly_risk(agent, rx1day_data, YEARS, WINDOW_SIZE)
            print(f'  {scenario}: {len(scenario_results[scenario]["years"])}년 처리')

    plot_risk_aal('하천홍수', 'RX1DAY', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'inland_flood_aal_agents.png')
    all_results['inland_flood'] = {'name': '하천홍수', 'results': scenario_results}

    # 5. 도시홍수 (RAIN80)
    print("\n5. 도시홍수 (RAIN80) 처리 중...")
    agent = UrbanFloodProbabilityAgent()
    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        rain80_data = load_yearly_data('RAIN80', scenario)
        if rain80_data:
            scenario_results[scenario] = process_yearly_risk(agent, rain80_data, YEARS, WINDOW_SIZE)
            print(f'  {scenario}: {len(scenario_results[scenario]["years"])}년 처리')

    plot_risk_aal('도시홍수', 'RAIN80', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'urban_flood_aal_agents.png')
    all_results['urban_flood'] = {'name': '도시홍수', 'results': scenario_results}

    # 6. 산불 (FWI)
    print("\n6. 산불 (FWI) 처리 중...")
    agent = WildfireProbabilityAgent()
    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        scenario_results[scenario] = process_wildfire(agent, scenario, YEARS)
        print(f'  {scenario}: {len(scenario_results[scenario]["years"])}년 처리')

    plot_risk_aal('산불', 'FWI', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'wildfire_aal_agents.png')
    all_results['wildfire'] = {'name': '산불', 'results': scenario_results}

    # 7. 물부족 (WSI) - 가상 데이터
    print("\n7. 물부족 (WSI) 처리 중...")
    agent = WaterScarcityProbabilityAgent()
    scenario_results = {}

    # Aqueduct 가상 데이터
    aqueduct_data = {
        'baseline': 0.15,
        'opt': {'2030': 0.12, '2050': 0.10, '2080': 0.08},
        'bau': {'2030': 0.18, '2050': 0.22, '2080': 0.28},
        'pes': {'2030': 0.20, '2050': 0.30, '2080': 0.45}
    }

    baseline_withdrawal = 500_000_000
    water_data = [{'year': y, 'withdrawal': baseline_withdrawal * (1 + 0.01 * (y - 2000))}
                  for y in range(1991, 2024)]
    flow_data = [{'year': y, 'daily_flows': [100.0] * 365} for y in range(1991, 2024)]

    ssp_mapping = {'SSP126': 'SSP1-2.6', 'SSP585': 'SSP5-8.5'}

    for scenario in SSP_SCENARIOS:
        results = {'years': [], 'aal': [], 'bin_probs': []}
        ssp_scenario = ssp_mapping[scenario]

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
            bin_probs = result['bin_probabilities']
            aal = calculate_aal(bin_probs, agent.dr_intensity)

            results['years'].append(year)
            results['aal'].append(aal * 100)
            results['bin_probs'].append(bin_probs)

        scenario_results[scenario] = results
        print(f'  {scenario}: {len(results["years"])}년 처리')

    plot_risk_aal('물부족', 'WSI', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'water_scarcity_aal_agents.png')
    all_results['water_scarcity'] = {'name': '물부족', 'results': scenario_results}

    # 8. 태풍 (S_tc)
    print("\n8. 태풍 (S_tc) 처리 중...")
    agent = TyphoonProbabilityAgent()
    site_location = {'lon': TARGET_LON, 'lat': TARGET_LAT}

    # 가상 과거 데이터 (실제 Best Track 필요)
    # 태풍이 서울(126.98, 37.57) 부근을 통과하도록 트랙 설정
    np.random.seed(42)
    historical_tracks = []
    for year in range(2015, 2025):
        n_typhoons = np.random.randint(2, 5)  # 연간 2~4개 태풍
        for t in range(n_typhoons):
            tracks = []
            # 태풍이 남쪽에서 북상하여 서울 근처를 지나가는 경로
            # 시작: 약 (125, 28) → 끝: 약 (130, 40)
            for i in range(24):  # 24개 시점 (6시간 간격 = 6일)
                lat = 28.0 + i * 0.5 + np.random.randn() * 0.3  # 28 → 40
                lon = 124.0 + i * 0.25 + np.random.randn() * 0.3  # 124 → 130

                # 강도는 위도에 따라 변화 (상륙 시 약화)
                if lat < 33:
                    grade = np.random.choice(['TS', 'STS', 'TY'], p=[0.3, 0.4, 0.3])
                elif lat < 36:
                    grade = np.random.choice(['TS', 'STS', 'TY'], p=[0.4, 0.4, 0.2])
                else:
                    grade = np.random.choice(['TD', 'TS', 'STS'], p=[0.3, 0.5, 0.2])

                tracks.append({
                    'lat': lat,
                    'lon': lon,
                    'grade': grade,
                    'gale_long': 300, 'gale_short': 200, 'gale_dir': 45,  # 강풍반경 확대
                    'storm_long': 150, 'storm_short': 100, 'storm_dir': 45
                })
            historical_tracks.append({
                'year': year, 'storm_id': f'{year}_{t+1}', 'tracks': tracks
            })

    agent.initialize_baseline(historical_tracks, site_location, baseline_temp=14.2)

    # 연평균 기온 데이터 로드 (태풍 강도 스케일링용)
    ta_yearly_126 = load_yearly_data('TA', 'SSP126')
    ta_yearly_585 = load_yearly_data('TA', 'SSP585')

    scenario_results = {}
    for scenario in SSP_SCENARIOS:
        ta_yearly = ta_yearly_126 if scenario == 'SSP126' else ta_yearly_585

        if not ta_yearly:
            print(f'  {scenario}: 기온 데이터 없음')
            continue

        # 전체 연도를 한 번에 처리 (동일 seed 문제 해결)
        yearly_temps = {year: ta_yearly.get(year, 14.2) for year in YEARS}

        collected_data = {
            'future_scenario': {
                'scenario': scenario,
                'target_years': YEARS,
                'yearly_temps': yearly_temps,
                'site_location': site_location
            }
        }

        # 전체 연도에 대한 S_tc 시뮬레이션 (한 번에)
        S_tc_array = agent.calculate_intensity_indicator(collected_data)

        # 각 연도별 bin 확률 계산
        results = {'years': [], 'aal': [], 'bin_probs': []}

        for idx, year in enumerate(YEARS):
            s_tc = S_tc_array[idx]

            # 단일 값에 대한 bin 분류
            if s_tc == 0:
                bin_probs = [1.0, 0.0, 0.0, 0.0]
            elif s_tc <= 5:
                bin_probs = [0.0, 1.0, 0.0, 0.0]
            elif s_tc <= 15:
                bin_probs = [0.0, 0.0, 1.0, 0.0]
            else:
                bin_probs = [0.0, 0.0, 0.0, 1.0]

            aal = calculate_aal(bin_probs, agent.dr_intensity)

            results['years'].append(year)
            results['aal'].append(aal * 100)
            results['bin_probs'].append(bin_probs)

        scenario_results[scenario] = results
        print(f'  {scenario}: {len(results["years"])}년 처리')

    plot_risk_aal('태풍', 'S_tc', scenario_results, get_bin_labels_safe(agent),
                  OUTPUT_DIR / 'typhoon_aal_agents.png')
    all_results['typhoon'] = {'name': '태풍', 'results': scenario_results}

    # 전체 요약 그래프
    print("\n전체 AAL 요약 그래프 생성 중...")
    plot_all_risks_summary(all_results, OUTPUT_DIR / 'all_risks_aal_summary_agents.png')

    print("\n" + "=" * 60)
    print(f"완료! 결과 저장 위치: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()
