"""
SSP 시나리오별 연도별 리스크 발생확률 및 AAL 시각화
KDE 기반 연속적 확률을 사용하는 에이전트 로직에 맞춤

V_score = 1.0, IR = 0.0 고정
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
from aiops.agents.probability_calculate.coastal_flood_probability_agent import CoastalFloodProbabilityAgent

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 설정
KMA_DATA_DIR = Path(__file__).parent / 'KMA'
SSP_SCENARIOS = ['SSP126', 'SSP585']
SCENARIO_COLORS = {'SSP126': '#2ecc71', 'SSP585': '#e74c3c'}
SCENARIO_LABELS = {'SSP126': 'SSP1-2.6 (저탄소)', 'SSP585': 'SSP5-8.5 (고탄소)'}
YEARS = list(range(2021, 2101))

# 대전 유성구 좌표
TARGET_LAT, TARGET_LON = 36.35, 127.30


def load_yearly_nc_data(filename_pattern, var_name, scenario):
    """NetCDF 연간 데이터 로드"""
    # 파일명 패턴 시도
    patterns = [
        f'{scenario}_{var_name}_gridraw_yearly_2021-2100.nc',
        f'AR6_{scenario}_5ENSMN_skorea_{var_name}_gridraw_yearly_2021_2100.nc'
    ]

    for pattern in patterns:
        filepath = KMA_DATA_DIR / pattern
        if filepath.exists():
            try:
                ds = nc.Dataset(filepath)

                # 좌표 변수명 확인 (lat/latitude, lon/longitude)
                if 'lat' in ds.variables:
                    lat = ds.variables['lat'][:]
                    lon = ds.variables['lon'][:]
                else:
                    lat = ds.variables['latitude'][:]
                    lon = ds.variables['longitude'][:]

                lat_idx = np.argmin(np.abs(lat - TARGET_LAT))
                lon_idx = np.argmin(np.abs(lon - TARGET_LON))

                data = ds.variables[var_name][:, lat_idx, lon_idx]
                ds.close()

                if hasattr(data, 'data'):
                    data = data.data

                return list(data)
            except Exception as e:
                print(f"  [WARN] {pattern} 로드 실패: {e}")

    return None


def load_monthly_nc_data(filename_pattern, var_name, scenario):
    """NetCDF 월간 데이터 로드"""
    patterns = [
        f'{scenario}_{var_name}_gridraw_monthly_2021-2100.nc',
        f'AR6_{scenario}_5ENSMN_skorea_{var_name}_gridraw_monthly_2021_2100.nc'
    ]

    for pattern in patterns:
        filepath = KMA_DATA_DIR / pattern
        if filepath.exists():
            try:
                ds = nc.Dataset(filepath)

                # 좌표 변수명 확인 (lat/latitude, lon/longitude)
                if 'lat' in ds.variables:
                    lat = ds.variables['lat'][:]
                    lon = ds.variables['lon'][:]
                else:
                    lat = ds.variables['latitude'][:]
                    lon = ds.variables['longitude'][:]

                lat_idx = np.argmin(np.abs(lat - TARGET_LAT))
                lon_idx = np.argmin(np.abs(lon - TARGET_LON))

                data = ds.variables[var_name][:, lat_idx, lon_idx]
                ds.close()

                if hasattr(data, 'data'):
                    data = data.data

                return list(data)
            except Exception as e:
                print(f"  [WARN] {pattern} 로드 실패: {e}")

    return None


def calculate_yearly_probs_with_agent(agent, yearly_data, window=5):
    """
    에이전트의 KDE 기반 확률 계산 사용
    5년 윈도우로 주변 데이터 포함하여 계산
    """
    n_years = len(yearly_data)
    n_bins = len(agent.bins)

    yearly_probs = {}

    for i, year in enumerate(YEARS):
        if i < n_years:
            # 5년 윈도우
            half = window // 2
            start = max(0, i - half)
            end = min(n_years, i + half + 1)
            window_data = yearly_data[start:end]

            if len(window_data) >= 3:
                # 에이전트의 KDE 기반 확률 계산
                probs = agent._calculate_bin_probabilities(np.array(window_data))
                yearly_probs[year] = probs
            else:
                yearly_probs[year] = [0.0] * n_bins
        else:
            yearly_probs[year] = [0.0] * n_bins

    return yearly_probs


def calculate_yearly_probs_monthly(agent, monthly_data, window_years=5):
    """
    월간 데이터에서 에이전트의 KDE 기반 확률 계산
    """
    n_months = len(monthly_data)
    n_years = n_months // 12
    n_bins = len(agent.bins)

    yearly_probs = {}

    for i, year in enumerate(YEARS):
        if i < n_years:
            # 5년 윈도우
            half = window_years // 2
            start_year = max(0, i - half)
            end_year = min(n_years, i + half + 1)

            start_month = start_year * 12
            end_month = end_year * 12
            window_data = monthly_data[start_month:end_month]

            if len(window_data) >= 12:
                probs = agent._calculate_bin_probabilities(np.array(window_data))
                yearly_probs[year] = probs
            else:
                yearly_probs[year] = [0.0] * n_bins
        else:
            yearly_probs[year] = [0.0] * n_bins

    return yearly_probs


def calculate_aal(yearly_probs, dr_intensity):
    """
    AAL 계산: Σ P[i] * DR[i] * (1 - IR)
    V_score = 1.0, IR = 0.0 고정
    """
    yearly_aal = {}

    for year, probs in yearly_probs.items():
        aal = 0.0
        for i, prob in enumerate(probs):
            if i < len(dr_intensity):
                aal += prob * dr_intensity[i]
        yearly_aal[year] = aal * 100  # 퍼센트

    return yearly_aal


def plot_risk_aal(risk_name, risk_code, scenario_data, bin_labels, dr_intensity, output_path):
    """
    리스크별 AAL + bin 확률 시각화 (2x2 레이아웃)
    """
    n_bins = len(bin_labels)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{risk_name} ({risk_code}) - SSP 시나리오별 연도별 발생확률 및 AAL', fontsize=14, fontweight='bold')

    # 1. AAL 꺾은선 그래프 (좌상)
    ax_aal = axes[0, 0]
    for scenario in SSP_SCENARIOS:
        if scenario not in scenario_data:
            continue
        yearly_aal = calculate_aal(scenario_data[scenario], dr_intensity)
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

    # 2. Bin별 확률 꺾은선 (우상)
    ax_bin = axes[0, 1]
    bin_colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, n_bins))

    for scenario in SSP_SCENARIOS:
        if scenario not in scenario_data:
            continue

        years = sorted(scenario_data[scenario].keys())
        linestyle = '-' if scenario == 'SSP126' else '--'

        for b in range(n_bins):
            bin_probs = [scenario_data[scenario][y][b] * 100 for y in years]
            label = f'{SCENARIO_LABELS[scenario]} - {bin_labels[b]}'
            ax_bin.plot(years, bin_probs, color=bin_colors[b],
                       linestyle=linestyle, label=label, linewidth=1.5, alpha=0.8)

    ax_bin.set_xlabel('연도')
    ax_bin.set_ylabel('확률 (%)')
    ax_bin.set_title('Bin별 발생확률')
    ax_bin.legend(fontsize=6, ncol=2, loc='upper right')
    ax_bin.grid(True, alpha=0.3)
    ax_bin.set_xlim(2021, 2100)
    ax_bin.set_ylim(0, 100)

    # 3. SSP126 stacked area (좌하)
    ax_126 = axes[1, 0]
    if 'SSP126' in scenario_data:
        years = sorted(scenario_data['SSP126'].keys())
        bin_data = [[scenario_data['SSP126'][y][b] * 100 for y in years] for b in range(n_bins)]

        ax_126.stackplot(years, bin_data, labels=bin_labels,
                        colors=bin_colors, alpha=0.7)
        ax_126.set_xlabel('연도')
        ax_126.set_ylabel('확률 (%)')
        ax_126.set_title('SSP1-2.6 (저탄소) - Bin별 분포')
        ax_126.legend(loc='upper left', fontsize=8)
        ax_126.set_xlim(2021, 2100)
        ax_126.set_ylim(0, 100)

    # 4. SSP585 stacked area (우하)
    ax_585 = axes[1, 1]
    if 'SSP585' in scenario_data:
        years = sorted(scenario_data['SSP585'].keys())
        bin_data = [[scenario_data['SSP585'][y][b] * 100 for y in years] for b in range(n_bins)]

        ax_585.stackplot(years, bin_data, labels=bin_labels,
                        colors=bin_colors, alpha=0.7)
        ax_585.set_xlabel('연도')
        ax_585.set_ylabel('확률 (%)')
        ax_585.set_title('SSP5-8.5 (고탄소) - Bin별 분포')
        ax_585.legend(loc='upper left', fontsize=8)
        ax_585.set_xlim(2021, 2100)
        ax_585.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  저장: {output_path}")


def main():
    output_dir = Path(__file__).parent / 'scenario_comparison'
    output_dir.mkdir(exist_ok=True)

    all_results = {}

    # 1. 폭염 (WSDI)
    print("\n1. 폭염 (WSDI) 처리 중...")
    agent = HighTemperatureProbabilityAgent()
    bin_labels = ['bin1 (0~3일)', 'bin2 (3~8일)', 'bin3 (8~20일)', 'bin4 (20일~)']
    scenario_data = {}

    for scenario in SSP_SCENARIOS:
        data = load_yearly_nc_data('WSDI', 'WSDI', scenario)
        if data:
            scenario_data[scenario] = calculate_yearly_probs_with_agent(agent, data)
            print(f"  {scenario}: {len(data)}개 연도")

    if scenario_data:
        plot_risk_aal('폭염', 'WSDI', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'heat_wave_aal.png')
        all_results['heat'] = scenario_data

    # 2. 한파 (CSDI)
    print("\n2. 한파 (CSDI) 처리 중...")
    agent = ColdWaveProbabilityAgent()
    bin_labels = ['bin1 (0~3일)', 'bin2 (3~7일)', 'bin3 (7~15일)', 'bin4 (15일~)']
    scenario_data = {}

    for scenario in SSP_SCENARIOS:
        data = load_yearly_nc_data('CSDI', 'CSDI', scenario)
        if data:
            scenario_data[scenario] = calculate_yearly_probs_with_agent(agent, data)
            print(f"  {scenario}: {len(data)}개 연도")

    if scenario_data:
        plot_risk_aal('한파', 'CSDI', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'cold_wave_aal.png')
        all_results['cold'] = scenario_data

    # 3. 가뭄 (SPEI12) - 월간
    print("\n3. 가뭄 (SPEI12) 처리 중...")
    agent = DroughtProbabilityAgent()
    bin_labels = ['bin1 (정상)', 'bin2 (중간)', 'bin3 (심각)', 'bin4 (극심)']
    scenario_data = {}

    for scenario in SSP_SCENARIOS:
        data = load_monthly_nc_data('SPEI12', 'SPEI12', scenario)
        if data:
            scenario_data[scenario] = calculate_yearly_probs_monthly(agent, data)
            print(f"  {scenario}: {len(data)}개 월")

    if scenario_data:
        plot_risk_aal('가뭄', 'SPEI12', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'drought_aal.png')
        all_results['drought'] = scenario_data

    # 4. 하천홍수 (RX1DAY)
    print("\n4. 하천홍수 (RX1DAY) 처리 중...")
    agent = InlandFloodProbabilityAgent()
    bin_labels = ['bin1 (<Q80)', 'bin2 (Q80~Q95)', 'bin3 (Q95~Q99)', 'bin4 (>Q99)']
    scenario_data = {}

    for scenario in SSP_SCENARIOS:
        data = load_yearly_nc_data('RX1DAY', 'RX1DAY', scenario)
        if data:
            scenario_data[scenario] = calculate_yearly_probs_with_agent(agent, data)
            print(f"  {scenario}: {len(data)}개 연도")

    if scenario_data:
        plot_risk_aal('하천홍수', 'RX1DAY', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'inland_flood_aal.png')
        all_results['inland_flood'] = scenario_data

    # 5. 도시홍수 (RAIN80)
    print("\n5. 도시홍수 (RAIN80) 처리 중...")
    agent = UrbanFloodProbabilityAgent()
    bin_labels = ['bin1 (0~1일)', 'bin2 (1~3일)', 'bin3 (3~5일)', 'bin4 (5일~)']
    scenario_data = {}

    for scenario in SSP_SCENARIOS:
        data = load_yearly_nc_data('RAIN80', 'RAIN80', scenario)
        if data:
            scenario_data[scenario] = calculate_yearly_probs_with_agent(agent, data)
            print(f"  {scenario}: {len(data)}개 연도")

    if scenario_data:
        plot_risk_aal('도시홍수', 'RAIN80', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'urban_flood_aal.png')
        all_results['urban_flood'] = scenario_data

    # 6. 산불 (FWI) - 월간
    print("\n6. 산불 (FWI) 처리 중...")
    agent = WildfireProbabilityAgent()
    bin_labels = ['bin1 (Low)', 'bin2 (Mod)', 'bin3 (High)', 'bin4 (V.High)', 'bin5 (Extreme)']
    scenario_data = {}

    for scenario in SSP_SCENARIOS:
        # FWI 계산에 필요한 데이터 로드
        ta = load_monthly_nc_data('TA', 'TA', scenario)
        rhm = load_monthly_nc_data('RHM', 'RHM', scenario)
        ws = load_monthly_nc_data('WS', 'WS', scenario)
        rn = load_monthly_nc_data('RN', 'RN', scenario)

        if all([ta, rhm, ws, rn]):
            # WildfireProbabilityAgent의 _calculate_fwi 사용 (캐나다 ISI 방식 근사)
            n_months = min(len(ta), len(rhm), len(ws), len(rn))
            fwi_data = []
            for m in range(n_months):
                fwi = agent._calculate_fwi(ta[m], rhm[m], ws[m], rn[m])
                fwi_data.append(fwi)

            scenario_data[scenario] = calculate_yearly_probs_monthly(agent, fwi_data)
            print(f"  {scenario}: {n_months}개 월, FWI 범위: {min(fwi_data):.2f} ~ {max(fwi_data):.2f}")

    if scenario_data:
        plot_risk_aal('산불', 'FWI', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'wildfire_aal.png')
        all_results['wildfire'] = scenario_data

    # 7. 물부족 (WSI)
    print("\n7. 물부족 (WSI) 처리 중...")
    agent = WaterScarcityProbabilityAgent()
    bin_labels = ['bin1 (<0.2)', 'bin2 (0.2~0.4)', 'bin3 (0.4~0.8)', 'bin4 (>0.8)']

    # Aqueduct BWS 기반 가상 데이터
    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        yearly_probs = {}
        base_wsi = 0.15 if scenario == 'SSP126' else 0.18

        for i, year in enumerate(YEARS):
            # 시나리오별 WSI 증가 추세
            if scenario == 'SSP126':
                wsi = base_wsi + (year - 2021) * 0.001
            else:
                wsi = base_wsi + (year - 2021) * 0.003

            # 주변 값으로 윈도우 생성
            window_wsi = [wsi + np.random.normal(0, 0.02) for _ in range(5)]
            probs = agent._calculate_bin_probabilities(np.array(window_wsi))
            yearly_probs[year] = probs

        scenario_data[scenario] = yearly_probs
        print(f"  {scenario}: Aqueduct 기반 계산")

    if scenario_data:
        plot_risk_aal('물부족', 'WSI', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'water_scarcity_aal.png')
        all_results['water_scarcity'] = scenario_data

    # 8. 태풍 (S_tc)
    print("\n8. 태풍 (S_tc) 처리 중...")
    agent = TyphoonProbabilityAgent()
    bin_labels = ['bin1 (약)', 'bin2 (중)', 'bin3 (강)', 'bin4 (매우강)']

    # 기온 데이터 기반 태풍 강도 추정
    scenario_data = {}
    for scenario in SSP_SCENARIOS:
        ta = load_monthly_nc_data('TA', 'TA', scenario)
        if ta:
            yearly_probs = {}
            n_years = len(ta) // 12

            base_probs = [0.4, 0.5, 0.08, 0.02]  # 기본 확률
            baseline_temp = 13.0

            for i, year in enumerate(YEARS):
                if i < n_years:
                    # 연평균 기온
                    year_temp = np.mean(ta[i*12:(i+1)*12])
                    temp_increase = year_temp - baseline_temp

                    # 기온 상승에 따른 확률 조정
                    adjusted = base_probs.copy()
                    shift = 0.02 * max(0, temp_increase)
                    adjusted[0] = max(0, base_probs[0] - shift)
                    adjusted[2] = min(0.3, base_probs[2] + shift * 0.5)
                    adjusted[3] = min(0.1, base_probs[3] + shift * 0.3)

                    # 정규화
                    total = sum(adjusted)
                    yearly_probs[year] = [p / total for p in adjusted]
                else:
                    yearly_probs[year] = base_probs

            scenario_data[scenario] = yearly_probs
            print(f"  {scenario}: 기온 기반 계산")

    if scenario_data:
        plot_risk_aal('태풍', 'S_tc', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'typhoon_aal.png')
        all_results['typhoon'] = scenario_data

    # 9. 해수면상승 (ZOS)
    print("\n9. 해수면상승 (ZOS) 처리 중...")
    agent = CoastalFloodProbabilityAgent()
    bin_labels = ['bin1 (안전)', 'bin2 (저위험)', 'bin3 (중위험)', 'bin4 (고위험)']

    zos_file = Path(__file__).parent / 'zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc'
    scenario_data = {}

    if zos_file.exists():
        ds = nc.Dataset(zos_file)
        lat = ds.variables['latitude'][:]
        lon = ds.variables['longitude'][:]

        # 2D 좌표 처리
        if lat.ndim == 2:
            dist = np.sqrt((lat - 36.45)**2 + (lon - 126.50)**2)
            j, i = np.unravel_index(np.argmin(dist), dist.shape)
            zos_data = ds.variables['zos'][:, j, i]
        else:
            lat_idx = np.argmin(np.abs(lat - 36.45))
            lon_idx = np.argmin(np.abs(lon - 126.50))
            zos_data = ds.variables['zos'][:, lat_idx, lon_idx]
        ds.close()

        if hasattr(zos_data, 'data'):
            zos_data = zos_data.data

        # SSP126만 데이터 있음
        yearly_probs = {}
        ground_level = 0.5

        for i, year in enumerate(YEARS):
            zos_idx = year - 2015
            if 0 <= zos_idx < len(zos_data):
                zos_m = float(zos_data[zos_idx]) / 100.0
                depth = max(0, zos_m - ground_level)

                # 침수 깊이 기반 확률
                if depth == 0:
                    probs = [1.0, 0.0, 0.0, 0.0]
                elif depth < 0.3:
                    probs = [0.0, 1.0, 0.0, 0.0]
                elif depth < 1.0:
                    probs = [0.0, 0.0, 1.0, 0.0]
                else:
                    probs = [0.0, 0.0, 0.0, 1.0]

                yearly_probs[year] = probs
            else:
                yearly_probs[year] = [1.0, 0.0, 0.0, 0.0]

        scenario_data['SSP126'] = yearly_probs
        print(f"  SSP126: ZOS 데이터 로드")

    if scenario_data:
        plot_risk_aal('해수면상승', 'ZOS', scenario_data, bin_labels, agent.dr_intensity,
                     output_dir / 'coastal_flood_aal.png')
        all_results['coastal_flood'] = scenario_data

    # 전체 요약 그래프
    print("\n전체 AAL 요약 그래프 생성 중...")
    plot_all_risks_summary(all_results, output_dir / 'all_risks_aal_summary.png')

    print(f"\n완료! 결과 저장 위치: {output_dir}")


def plot_all_risks_summary(all_results, output_path):
    """9대 리스크 AAL 요약 그래프"""

    risk_info = {
        'heat': ('폭염', HighTemperatureProbabilityAgent().dr_intensity),
        'cold': ('한파', ColdWaveProbabilityAgent().dr_intensity),
        'drought': ('가뭄', DroughtProbabilityAgent().dr_intensity),
        'inland_flood': ('하천홍수', InlandFloodProbabilityAgent().dr_intensity),
        'urban_flood': ('도시홍수', UrbanFloodProbabilityAgent().dr_intensity),
        'wildfire': ('산불', WildfireProbabilityAgent().dr_intensity),
        'water_scarcity': ('물부족', WaterScarcityProbabilityAgent().dr_intensity),
        'typhoon': ('태풍', TyphoonProbabilityAgent().dr_intensity),
        'coastal_flood': ('해수면상승', CoastalFloodProbabilityAgent().dr_intensity)
    }

    fig, axes = plt.subplots(3, 3, figsize=(16, 12))
    fig.suptitle('9대 기후 리스크 AAL 추이 (SSP126 vs SSP585)', fontsize=16, fontweight='bold')

    for idx, (risk_key, (risk_name, dr_intensity)) in enumerate(risk_info.items()):
        ax = axes[idx // 3, idx % 3]

        if risk_key in all_results:
            scenario_data = all_results[risk_key]

            for scenario in SSP_SCENARIOS:
                if scenario in scenario_data:
                    yearly_aal = calculate_aal(scenario_data[scenario], dr_intensity)
                    years = sorted(yearly_aal.keys())
                    aal_values = [yearly_aal[y] for y in years]

                    ax.plot(years, aal_values, color=SCENARIO_COLORS[scenario],
                           label=SCENARIO_LABELS[scenario], linewidth=2)

        ax.set_title(risk_name)
        ax.set_xlabel('연도')
        ax.set_ylabel('AAL (%)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(2021, 2100)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  저장: {output_path}")


if __name__ == '__main__':
    main()
