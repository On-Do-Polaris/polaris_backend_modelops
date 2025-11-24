"""
SSP 시나리오별 연도별 리스크 발생확률 시각화 (꺾은선 그래프)
대덕 데이터센터 (대전광역시 유성구) 기준

SSP126 vs SSP585 비교
기간: 2021-2100
"""
import sys
import json
from pathlib import Path
import numpy as np
import netCDF4 as nc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

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

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 대덕 데이터센터 좌표
DAEJEON_LAT = 36.35
DAEJEON_LON = 127.38

# KMA 데이터 경로
KMA_DATA_DIR = Path(__file__).parent / "KMA"

# SSP 시나리오
SSP_SCENARIOS = ['SSP126', 'SSP585']
SCENARIO_COLORS = {'SSP126': '#2ecc71', 'SSP585': '#e74c3c'}
SCENARIO_LABELS = {'SSP126': 'SSP1-2.6 (저탄소)', 'SSP585': 'SSP5-8.5 (고탄소)'}

# 연도 범위
YEARS = list(range(2021, 2101))


def get_nearest_idx(lat_arr, lon_arr, target_lat, target_lon):
    """가장 가까운 격자점 인덱스 반환"""
    lat_idx = np.argmin(np.abs(lat_arr - target_lat))
    lon_idx = np.argmin(np.abs(lon_arr - target_lon))
    return lat_idx, lon_idx


def load_yearly_data(scenario: str, var_name: str):
    """연간 데이터 로드"""
    filename = f"{scenario}_{var_name}_gridraw_yearly_2021-2100.nc"
    filepath = KMA_DATA_DIR / filename

    if not filepath.exists():
        return None

    ds = nc.Dataset(filepath)
    lat_arr = ds.variables['latitude'][:]
    lon_arr = ds.variables['longitude'][:]
    lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    ds.close()

    if hasattr(data, 'data'):
        data = data.data

    return list(data)


def load_monthly_data(scenario: str, var_name: str):
    """월간 데이터 로드"""
    patterns = [
        f"{scenario}_{var_name}_gridraw_monthly_2021-2100.nc",
        f"AR6_{scenario}_5ENSMN_skorea_{var_name}_gridraw_monthly_2021_2100.nc"
    ]

    filepath = None
    for pattern in patterns:
        test_path = KMA_DATA_DIR / pattern
        if test_path.exists():
            filepath = test_path
            break

    if filepath is None:
        return None

    ds = nc.Dataset(filepath)
    lat_arr = ds.variables['latitude'][:]
    lon_arr = ds.variables['longitude'][:]
    lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    ds.close()

    if hasattr(data, 'data'):
        data = data.data

    return list(data)


def apply_gaussian_smoothing(prob_array, sigma=2.0):
    """
    Gaussian smoothing을 적용하여 확률 분포를 부드럽게 만듦

    Args:
        prob_array: 확률 배열 (shape: [n_years, n_bins])
        sigma: Gaussian kernel의 표준편차 (클수록 더 부드러움)

    Returns:
        smoothed 확률 배열
    """
    smoothed = np.zeros_like(prob_array)

    # 각 bin별로 독립적으로 smoothing 적용
    for b in range(prob_array.shape[1]):
        smoothed[:, b] = gaussian_filter1d(prob_array[:, b], sigma=sigma, mode='nearest')

    # 각 연도별로 확률 합이 1이 되도록 정규화
    for i in range(len(smoothed)):
        total = np.sum(smoothed[i])
        if total > 0:
            smoothed[i] = smoothed[i] / total

    return smoothed


def calculate_yearly_bin_probabilities(agent, yearly_data, window=5):
    """
    연도별 bin 확률 계산 (에이전트의 KDE 기반 연속 확률 + Gaussian smoothing)
    각 연도 주변 데이터로 에이전트의 _calculate_bin_probabilities 호출
    """
    n_years = len(yearly_data)
    n_bins = len(agent.bins)

    # 임시 배열: [n_years, n_bins]
    prob_array = np.zeros((len(YEARS), n_bins))

    for i, year in enumerate(YEARS):
        if i < n_years:
            # 5년 윈도우로 주변 데이터 포함 (KDE에 최소 샘플 필요)
            half_window = window // 2
            start_idx = max(0, i - half_window)
            end_idx = min(n_years, i + half_window + 1)
            window_data = yearly_data[start_idx:end_idx]

            if len(window_data) >= 3:
                # 에이전트의 KDE 기반 확률 계산 (연속적!)
                probs = agent._calculate_bin_probabilities(np.array(window_data))
                prob_array[i] = probs
            else:
                # 샘플 부족 시 단순 분류
                bin_indices = agent._classify_into_bins(np.array([yearly_data[i]]))
                for b in range(n_bins):
                    prob_array[i, b] = 1.0 if bin_indices[0] == b else 0.0

    # Gaussian smoothing 적용하여 더 부드럽게
    smoothed_array = apply_gaussian_smoothing(prob_array, sigma=2.0)

    # 딕셔너리 형태로 변환
    yearly_probs = {}
    for i, year in enumerate(YEARS):
        yearly_probs[year] = smoothed_array[i].tolist()

    return yearly_probs


def calculate_yearly_bin_probs_monthly(agent, monthly_data, window_years=5):
    """
    월별 데이터에서 연도별 bin 확률 계산 (에이전트의 KDE + Gaussian smoothing)
    각 연도 주변 월별 데이터로 에이전트의 _calculate_bin_probabilities 호출
    """
    n_months = len(monthly_data)
    n_years = n_months // 12
    n_bins = len(agent.bins)

    # 임시 배열: [n_years, n_bins]
    prob_array = np.zeros((len(YEARS), n_bins))

    for i, year in enumerate(YEARS):
        if i < n_years:
            # 5년 윈도우 (중앙 정렬)
            half_window = window_years // 2
            start_year_idx = max(0, i - half_window)
            end_year_idx = min(n_years, i + half_window + 1)

            start_month = start_year_idx * 12
            end_month = end_year_idx * 12

            window_data = monthly_data[start_month:end_month]

            if len(window_data) >= 12:
                # 에이전트의 KDE 기반 확률 계산 (연속적!)
                probs = agent._calculate_bin_probabilities(np.array(window_data))
                prob_array[i] = probs
            elif len(window_data) > 0:
                # 샘플 부족 시 단순 비율
                intensity_array = np.array(window_data)
                bin_indices = agent._classify_into_bins(intensity_array)
                for b in range(n_bins):
                    prob_array[i, b] = np.sum(bin_indices == b) / len(bin_indices)

    # Gaussian smoothing 적용
    smoothed_array = apply_gaussian_smoothing(prob_array, sigma=2.0)

    # 딕셔너리 형태로 변환
    yearly_probs = {}
    for i, year in enumerate(YEARS):
        yearly_probs[year] = smoothed_array[i].tolist()

    return yearly_probs


def calculate_aal_from_probs(yearly_probs, dr_intensity, v_score=1.0, ir=0.0):
    """
    bin별 확률로부터 AAL 계산

    Args:
        yearly_probs: {year: [prob_bin1, prob_bin2, ...]}
        dr_intensity: bin별 기본 손상률 리스트
        v_score: 취약성 점수 (0~1), 기본값 1.0
        ir: 보험 보전율 (0~1), 기본값 0.0

    Returns:
        {year: aal_value}
    """
    yearly_aal = {}

    for year, probs in yearly_probs.items():
        aal = 0.0
        for i, prob in enumerate(probs):
            if i < len(dr_intensity):
                # AAL = Σ P[i] * DR[i] * (1 - IR)
                # V_score는 1로 고정하므로 F_vuln = 1.0
                aal += prob * dr_intensity[i] * (1.0 - ir)
        yearly_aal[year] = aal * 100  # 퍼센트로 변환

    return yearly_aal


def calculate_water_scarcity_yearly(years_list):
    """물부족 연도별 bin 확률 계산 (Aqueduct BWS 기반)"""
    agent = WaterScarcityProbabilityAgent()
    n_bins = len(agent.bins)

    # 가상 Aqueduct BWS 데이터
    aqueduct_data = {
        'baseline': 0.15,
        'opt': {'2030': 0.12, '2050': 0.10, '2080': 0.08},
        'bau': {'2030': 0.18, '2050': 0.22, '2080': 0.28},
        'pes': {'2030': 0.20, '2050': 0.30, '2080': 0.45}
    }

    baseline_withdrawal = 500_000_000
    water_data = [{'year': y, 'withdrawal': baseline_withdrawal} for y in range(1991, 2024)]
    flow_data = [{'year': y, 'daily_flows': [100.0] * 365} for y in range(1991, 2024)]

    results = {}

    ssp_mapping = {'SSP126': 'SSP1-2.6', 'SSP585': 'SSP5-8.5'}

    for scenario in SSP_SCENARIOS:
        yearly_probs = {year: [0.0] * n_bins for year in years_list}
        ssp_scenario = ssp_mapping[scenario]

        for year in years_list:
            # 해당 연도까지의 미래 용수이용량 계산
            target_years = [year]

            collected_data = {
                'water_data': water_data,
                'flow_data': flow_data,
                'baseline_years': list(range(1991, 2021)),
                'aqueduct_data': aqueduct_data,
                'ssp_scenario': ssp_scenario,
                'target_years': target_years
            }

            result = agent.calculate_probability(collected_data)

            for b, prob in enumerate(result['bin_probabilities']):
                yearly_probs[year][b] = prob

        results[scenario] = yearly_probs

    return results


def plot_risk_comparison(risk_name, risk_name_en, scenario_data, bin_labels, output_path, dr_intensity=None):
    """
    특정 리스크에 대해 SSP126 vs SSP585 bin별 확률 비교 그래프 + AAL
    """
    n_bins = len(bin_labels)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{risk_name} ({risk_name_en}) - SSP 시나리오별 연도별 발생확률', fontsize=14, fontweight='bold')

    # 4개 bin 모두를 꺾은선으로 표시 (시나리오별)
    # AAL을 추가하면 좌측 상단에 AAL, 나머지는 기존 그래프
    if dr_intensity is not None:
        # AAL 그래프
        ax_aal = axes[0, 0]

        for scenario in SSP_SCENARIOS:
            if scenario not in scenario_data:
                continue

            yearly_aal = calculate_aal_from_probs(scenario_data[scenario], dr_intensity, v_score=1.0, ir=0.0)
            years = sorted(yearly_aal.keys())
            aal_values = [yearly_aal[y] for y in years]

            ax_aal.plot(years, aal_values, color=SCENARIO_COLORS[scenario],
                       label=SCENARIO_LABELS[scenario], linewidth=2)

        ax_aal.set_xlabel('연도')
        ax_aal.set_ylabel('AAL (%)')
        ax_aal.set_title('연평균손실률 (AAL) 추이')
        ax_aal.legend()
        ax_aal.grid(True, alpha=0.3)
        ax_aal.set_xlim(2021, 2100)

        # Bin별 확률은 우측 상단으로 이동
        ax_main = axes[0, 1]
    else:
        ax_main = axes[0, 0]

    # 색상 설정 (bin별)
    bin_colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, n_bins))

    for scenario in SSP_SCENARIOS:
        if scenario not in scenario_data:
            continue

        years = sorted(scenario_data[scenario].keys())

        # 각 bin별로 꺾은선 그리기
        for b in range(n_bins):
            bin_probs = []
            for year in years:
                probs = scenario_data[scenario][year]
                prob = probs[b] if b < len(probs) else 0
                bin_probs.append(prob * 100)

            # 시나리오별로 선 스타일 구분
            linestyle = '-' if scenario == 'SSP126' else '--'
            label = f'{SCENARIO_LABELS[scenario]} - {bin_labels[b]}'

            ax_main.plot(years, bin_probs, color=bin_colors[b],
                        linestyle=linestyle, label=label, linewidth=1.5, alpha=0.8)

    ax_main.set_xlabel('연도')
    ax_main.set_ylabel('확률 (%)')
    ax_main.set_title('Bin별 발생확률 (4개 bin 모두 표시)')
    ax_main.legend(fontsize=7, ncol=2)
    ax_main.grid(True, alpha=0.3)
    ax_main.set_xlim(2021, 2100)
    ax_main.set_ylim(0, 100)

    # 각 시나리오별 bin 분포 (stacked area)
    for idx, scenario in enumerate(SSP_SCENARIOS):
        if scenario not in scenario_data:
            continue

        # AAL이 있으면 좌하, 우하. 없으면 우상, 좌하
        if dr_intensity is not None:
            ax = axes[1, 0] if idx == 0 else axes[1, 1]
        else:
            ax = axes[0, 1] if idx == 0 else axes[1, 0]

        years = sorted(scenario_data[scenario].keys())
        bin_data = {b: [] for b in range(n_bins)}

        for year in years:
            probs = scenario_data[scenario][year]
            for b in range(n_bins):
                bin_data[b].append(probs[b] * 100 if b < len(probs) else 0)

        # Stacked area plot
        bottom = np.zeros(len(years))
        colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, n_bins))

        for b in range(n_bins):
            ax.fill_between(years, bottom, bottom + np.array(bin_data[b]),
                           alpha=0.7, label=bin_labels[b], color=colors[b])
            bottom += np.array(bin_data[b])

        ax.set_xlabel('연도')
        ax.set_ylabel('확률 (%)')
        ax.set_title(f'{SCENARIO_LABELS[scenario]} - Bin별 분포')
        ax.legend(loc='upper left', fontsize=8)
        ax.set_xlim(2021, 2100)
        ax.set_ylim(0, 100)

    # 시나리오 간 차이 (SSP585 - SSP126) - AAL이 없을 때만 표시
    if dr_intensity is None:
        ax_diff = axes[1, 1]
        if 'SSP126' in scenario_data and 'SSP585' in scenario_data:
            years = sorted(scenario_data['SSP126'].keys())
            diff_probs = []

            for year in years:
                probs_126 = scenario_data['SSP126'][year]
                probs_585 = scenario_data['SSP585'][year]

                high_126 = sum(probs_126[-2:]) if len(probs_126) >= 2 else (probs_126[-1] if probs_126 else 0)
                high_585 = sum(probs_585[-2:]) if len(probs_585) >= 2 else (probs_585[-1] if probs_585 else 0)

                diff_probs.append((high_585 - high_126) * 100)

            ax_diff.fill_between(years, 0, diff_probs,
                                where=np.array(diff_probs) >= 0, color='#e74c3c', alpha=0.5, label='SSP585 > SSP126')
            ax_diff.fill_between(years, 0, diff_probs,
                                where=np.array(diff_probs) < 0, color='#2ecc71', alpha=0.5, label='SSP126 > SSP585')
            ax_diff.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax_diff.plot(years, diff_probs, color='black', linewidth=1)

        ax_diff.set_xlabel('연도')
        ax_diff.set_ylabel('확률 차이 (%p)')
        ax_diff.set_title('시나리오 간 고위험 확률 차이 (SSP585 - SSP126)')
        ax_diff.legend()
        ax_diff.grid(True, alpha=0.3)
        ax_diff.set_xlim(2021, 2100)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  저장: {output_path}")


def main():
    print("=" * 60)
    print("SSP 시나리오별 연도별 리스크 발생확률 시각화")
    print("위치: 대덕 데이터센터 (대전광역시 유성구)")
    print("=" * 60)

    output_dir = Path(__file__).parent / "scenario_comparison"
    output_dir.mkdir(exist_ok=True)

    all_results = {}

    # 1. 폭염 (WSDI)
    print("\n1. 폭염 (WSDI) 처리 중...")
    agent = HighTemperatureProbabilityAgent()
    bin_labels = ['bin1 (0~3일)', 'bin2 (3~8일)', 'bin3 (8~20일)', 'bin4 (20일~)']

    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        data = load_yearly_data(scenario, 'WSDI')
        if data:
            scenario_data[scenario] = calculate_yearly_bin_probabilities(agent, data)
            print(f"  {scenario}: {len(data)}개 연도 로드")

    if scenario_data:
        plot_risk_comparison('폭염', 'WSDI', scenario_data, bin_labels,
                            output_dir / 'heat_wave_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['heat'] = scenario_data

    # 2. 한파 (CSDI)
    print("\n2. 한파 (CSDI) 처리 중...")
    agent = ColdWaveProbabilityAgent()
    bin_labels = ['bin1 (0~3일)', 'bin2 (3~7일)', 'bin3 (7~15일)', 'bin4 (15일~)']

    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        data = load_yearly_data(scenario, 'CSDI')
        if data:
            scenario_data[scenario] = calculate_yearly_bin_probabilities(agent, data)
            print(f"  {scenario}: {len(data)}개 연도 로드")

    if scenario_data:
        plot_risk_comparison('한파', 'CSDI', scenario_data, bin_labels,
                            output_dir / 'cold_wave_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['cold'] = scenario_data

    # 3. 가뭄 (SPEI12)
    print("\n3. 가뭄 (SPEI12) 처리 중...")
    agent = DroughtProbabilityAgent()
    bin_labels = ['bin1 (정상)', 'bin2 (중간)', 'bin3 (심각)', 'bin4 (극심)']

    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        data = load_monthly_data(scenario, 'SPEI12')
        if data:
            scenario_data[scenario] = calculate_yearly_bin_probs_monthly(agent, data)
            print(f"  {scenario}: {len(data)}개 월 로드")

    if scenario_data:
        plot_risk_comparison('가뭄', 'SPEI12', scenario_data, bin_labels,
                            output_dir / 'drought_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['drought'] = scenario_data

    # 4. 하천홍수 (RX1DAY)
    print("\n4. 하천홍수 (RX1DAY) 처리 중...")
    agent = InlandFloodProbabilityAgent()
    bin_labels = ['bin1 (<Q80)', 'bin2 (Q80~Q95)', 'bin3 (Q95~Q99)', 'bin4 (>Q99)']

    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        data = load_yearly_data(scenario, 'RX1DAY')
        if data:
            # baseline 설정 후 확률 계산
            agent.bins = [
                (0, np.percentile(data, 80)),
                (np.percentile(data, 80), np.percentile(data, 95)),
                (np.percentile(data, 95), np.percentile(data, 99)),
                (np.percentile(data, 99), float('inf'))
            ]
            scenario_data[scenario] = calculate_yearly_bin_probabilities(agent, data)
            print(f"  {scenario}: {len(data)}개 연도 로드")

    if scenario_data:
        plot_risk_comparison('하천홍수', 'RX1DAY', scenario_data, bin_labels,
                            output_dir / 'inland_flood_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['inland_flood'] = scenario_data

    # 5. 도시홍수 (RAIN80)
    print("\n5. 도시홍수 (RAIN80) 처리 중...")
    agent = UrbanFloodProbabilityAgent()
    bin_labels = ['bin1 (<1일)', 'bin2 (1~3일)', 'bin3 (3~5일)', 'bin4 (5일~)']

    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        data = load_yearly_data(scenario, 'RAIN80')
        if data:
            scenario_data[scenario] = calculate_yearly_bin_probabilities(agent, data)
            print(f"  {scenario}: {len(data)}개 연도 로드")

    if scenario_data:
        plot_risk_comparison('도시홍수', 'RAIN80', scenario_data, bin_labels,
                            output_dir / 'urban_flood_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['urban_flood'] = scenario_data

    # 6. 산불 (FWI)
    print("\n6. 산불 (FWI) 처리 중...")
    agent = WildfireProbabilityAgent()
    bin_labels = ['bin1 (Low)', 'bin2 (Mod)', 'bin3 (High)', 'bin4 (V.High)', 'bin5 (Extreme)']

    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        ta = load_monthly_data(scenario, 'TA')
        rhm = load_monthly_data(scenario, 'RHM')
        ws = load_monthly_data(scenario, 'WS')
        rn = load_monthly_data(scenario, 'RN')

        if all([ta, rhm, ws, rn]):
            # FWI 계산
            n_months = min(len(ta), len(rhm), len(ws), len(rn))
            fwi_data = []
            for i in range(n_months):
                fwi = agent._calculate_fwi(ta[i], rhm[i], ws[i], rn[i])
                fwi_data.append(fwi)

            scenario_data[scenario] = calculate_yearly_bin_probs_monthly(agent, fwi_data)
            print(f"  {scenario}: {n_months}개 월 로드")

    if scenario_data:
        plot_risk_comparison('산불', 'FWI', scenario_data, bin_labels,
                            output_dir / 'wildfire_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['wildfire'] = scenario_data

    # 7. 물부족 (WSI) - Aqueduct 기반
    print("\n7. 물부족 (WSI) 처리 중...")
    agent = WaterScarcityProbabilityAgent()
    bin_labels = ['bin1 (<0.2)', 'bin2 (0.2~0.4)', 'bin3 (0.4~0.8)', 'bin4 (>0.8)']

    scenario_data = calculate_water_scarcity_yearly(YEARS)
    print(f"  SSP126, SSP585: Aqueduct BWS 기반 계산")

    if scenario_data:
        plot_risk_comparison('물부족', 'WSI', scenario_data, bin_labels,
                            output_dir / 'water_scarcity_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['water_scarcity'] = scenario_data

    # 8. 태풍 (S_tc) - 가상 데이터 기반 (Best Track 없음)
    print("\n8. 태풍 (S_tc) 처리 중...")
    agent = TyphoonProbabilityAgent()
    bin_labels = ['bin1 (영향없음)', 'bin2 (0~5)', 'bin3 (5~15)', 'bin4 (15~)']

    # 태풍은 과거 Best Track 기반이므로 미래 시나리오별 시뮬레이션
    # 여기서는 기온 데이터 기반 스케일링으로 추정
    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        ta_yearly = load_yearly_data(scenario, 'TA')
        if not ta_yearly:
            ta_monthly = load_monthly_data(scenario, 'TA')
            if ta_monthly:
                # 월별 → 연평균
                ta_yearly = []
                for y in range(80):
                    yearly_avg = np.mean(ta_monthly[y*12:(y+1)*12])
                    ta_yearly.append(yearly_avg)

        if ta_yearly:
            # 기온 기반 태풍 강도 스케일링 (가상)
            # 기온 1°C 상승 → 태풍 강도 4% 증가 가정
            baseline_temp = 14.2
            yearly_probs = {year: [0.0] * 4 for year in YEARS}

            for i, year in enumerate(YEARS):
                if i < len(ta_yearly):
                    temp = ta_yearly[i]
                    temp_increase = temp - baseline_temp
                    intensity_scale = 1.0 + 0.04 * temp_increase

                    # 기본 확률 (과거 기반 가정)
                    base_probs = [0.4, 0.5, 0.08, 0.02]  # 대전 기준

                    # 고강도 확률 증가
                    adjusted_probs = base_probs.copy()
                    shift = 0.02 * temp_increase
                    adjusted_probs[0] = max(0, base_probs[0] - shift)
                    adjusted_probs[1] = base_probs[1]
                    adjusted_probs[2] = min(0.3, base_probs[2] + shift * 0.5)
                    adjusted_probs[3] = min(0.2, base_probs[3] + shift * 0.5)

                    # 정규화
                    total = sum(adjusted_probs)
                    yearly_probs[year] = [p / total for p in adjusted_probs]

            scenario_data[scenario] = yearly_probs
            print(f"  {scenario}: 기온 기반 추정")

    if scenario_data:
        plot_risk_comparison('태풍', 'S_tc', scenario_data, bin_labels,
                            output_dir / 'typhoon_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['typhoon'] = scenario_data

    # 9. 해수면상승 (ZOS)
    print("\n9. 해수면상승 (ZOS) 처리 중...")
    agent = CoastalFloodProbabilityAgent()
    bin_labels = ['bin1 (침수없음)', 'bin2 (0~0.3m)', 'bin3 (0.3~1m)', 'bin4 (1m~)']

    # ZOS 데이터 확인 (scratch 폴더에서)
    zos_file = Path(__file__).parent / "zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc"
    scenario_data = {}

    if zos_file.exists():
        ds = nc.Dataset(zos_file)
        lat_arr = ds.variables['latitude'][:]
        lon_arr = ds.variables['longitude'][:]
        coastal_lat, coastal_lon = 36.45, 126.50

        # 2D 좌표 배열인 경우 처리
        if lat_arr.ndim == 2:
            lat_diff = np.abs(lat_arr - coastal_lat)
            lon_diff = np.abs(lon_arr - coastal_lon)
            dist = np.sqrt(lat_diff**2 + lon_diff**2)
            j_idx, i_idx = np.unravel_index(np.argmin(dist), dist.shape)
            zos_data = ds.variables['zos'][:, j_idx, i_idx]
        else:
            lat_idx = np.argmin(np.abs(lat_arr - coastal_lat))
            lon_idx = np.argmin(np.abs(lon_arr - coastal_lon))
            zos_data = ds.variables['zos'][:, lat_idx, lon_idx]
        ds.close()

        if hasattr(zos_data, 'data'):
            zos_data = zos_data.data

        # SSP126 데이터
        yearly_probs = {year: [0.0] * 4 for year in YEARS}
        ground_level = 0.5  # 해안가 지반고

        for i, year in enumerate(YEARS):
            zos_idx = year - 2015
            if 0 <= zos_idx < len(zos_data):
                zos_cm = float(zos_data[zos_idx])
                zos_m = zos_cm / 100.0
                depth = max(0, zos_m - ground_level)

                if depth == 0:
                    yearly_probs[year] = [1.0, 0.0, 0.0, 0.0]
                elif depth < 0.3:
                    yearly_probs[year] = [0.0, 1.0, 0.0, 0.0]
                elif depth < 1.0:
                    yearly_probs[year] = [0.0, 0.0, 1.0, 0.0]
                else:
                    yearly_probs[year] = [0.0, 0.0, 0.0, 1.0]

        scenario_data['SSP126'] = yearly_probs
        print(f"  SSP126: ZOS 데이터 로드 (SSP585 데이터 없음)")

        plot_risk_comparison('해수면상승', 'ZOS', scenario_data, bin_labels,
                            output_dir / 'coastal_flood_comparison.png', dr_intensity=agent.dr_intensity)
        all_results['coastal_flood'] = scenario_data
    else:
        print("  [WARN] ZOS 데이터 없음")
        all_results['coastal_flood'] = {}

    # 통합 요약 그래프
    print("\n통합 요약 그래프 생성 중...")
    create_summary_plot(all_results, output_dir / 'all_risks_summary.png')

    # 데이터 가용성 출력
    print("\n" + "=" * 60)
    print("SSP126 Data Availability")
    print("=" * 60)
    data_status = check_data_availability()
    for var, status in data_status.items():
        print(f"  {var:25s} {status}")

    print(f"\nCompleted! Results saved to: {output_dir}")


def check_data_availability():
    """SSP126 데이터 가용성 확인"""
    variables = {
        'WSDI (폭염)': ('KMA', 'SSP126_WSDI_gridraw_yearly_2021-2100.nc'),
        'CSDI (한파)': ('KMA', 'SSP126_CSDI_gridraw_yearly_2021-2100.nc'),
        'SPEI12 (가뭄)': ('KMA', 'SSP126_SPEI12_gridraw_monthly_2021-2100.nc'),
        'RX1DAY (하천홍수)': ('KMA', 'SSP126_RX1DAY_gridraw_yearly_2021-2100.nc'),
        'RAIN80 (도시홍수)': ('KMA', 'SSP126_RAIN80_gridraw_yearly_2021-2100.nc'),
        'TA (기온/산불)': ('KMA', 'AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc'),
        'RHM (습도/산불)': ('KMA', 'AR6_SSP126_5ENSMN_skorea_RHM_gridraw_monthly_2021_2100.nc'),
        'WS (풍속/산불)': ('KMA', 'AR6_SSP126_5ENSMN_skorea_WS_gridraw_monthly_2021_2100.nc'),
        'RN (강수/산불)': ('KMA', 'AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc'),
        'ZOS (해수면)': ('', 'zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc')
    }

    status = {}
    for var, (subfolder, filename) in variables.items():
        if subfolder:
            filepath = KMA_DATA_DIR / filename
        else:
            filepath = Path(__file__).parent / filename
        if filepath.exists():
            status[var] = "OK"
        else:
            status[var] = "MISSING"

    return status


def create_summary_plot(all_results, output_path):
    """모든 리스크 고위험 확률 요약 그래프 (9대 리스크)"""
    risks = ['heat', 'cold', 'drought', 'inland_flood', 'urban_flood', 'wildfire', 'water_scarcity', 'typhoon', 'coastal_flood']
    risk_names = ['폭염', '한파', '가뭄', '하천홍수', '도시홍수', '산불', '물부족', '태풍', '해수면상승']

    fig, axes = plt.subplots(3, 3, figsize=(18, 15))
    fig.suptitle('대덕 데이터센터 9대 리스크 고위험 확률 추이 (SSP126 vs SSP585, 2021-2100)', fontsize=14, fontweight='bold')

    for idx, (risk, risk_name) in enumerate(zip(risks, risk_names)):
        ax = axes[idx // 3, idx % 3]

        if risk not in all_results:
            ax.text(0.5, 0.5, '데이터 없음', ha='center', va='center', fontsize=12)
            ax.set_title(risk_name)
            ax.set_xlim(2021, 2100)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            continue

        scenario_data = all_results[risk]

        for scenario in SSP_SCENARIOS:
            if scenario not in scenario_data:
                continue

            years = sorted(scenario_data[scenario].keys())
            high_risk_probs = []

            for year in years:
                probs = scenario_data[scenario][year]
                high_risk = sum(probs[-2:]) if len(probs) >= 2 else (probs[-1] if probs else 0)
                high_risk_probs.append(high_risk * 100)

            ax.plot(years, high_risk_probs, color=SCENARIO_COLORS[scenario],
                   label=SCENARIO_LABELS[scenario], linewidth=2)

        ax.set_xlabel('연도')
        ax.set_ylabel('고위험 확률 (%)')
        ax.set_title(risk_name)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(2021, 2100)
        ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  저장: {output_path}")


if __name__ == '__main__':
    main()
