"""
리스크별 연도별 강도지표 변화 시각화 (꺾은선 그래프)
대덕 데이터센터 (대전광역시 유성구) 기준
- 기후 리스크 (2021-2100): 폭염, 한파, 가뭄, 하천홍수, 도시홍수, 산불
- 과거 데이터 리스크: 물부족 (1991-2023), 태풍 (2015-2024)
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import netCDF4 as nc
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 대덕 데이터센터 좌표
DAEJEON_LAT = 36.35
DAEJEON_LON = 127.38
KMA_DATA_DIR = Path(__file__).parent / "KMA"
WAMIS_DATA_DIR = Path(__file__).parent / "wamis"
TYPHOON_DATA_DIR = Path(__file__).parent / "typhoon"

def get_nearest_idx(lat_arr, lon_arr, target_lat, target_lon):
    lat_idx = np.argmin(np.abs(lat_arr - target_lat))
    lon_idx = np.argmin(np.abs(lon_arr - target_lon))
    return lat_idx, lon_idx

def load_yearly_data(filename: str, var_name: str):
    filepath = KMA_DATA_DIR / filename
    if not filepath.exists():
        return None, None

    ds = nc.Dataset(filepath)
    lat_arr = ds.variables['latitude'][:]
    lon_arr = ds.variables['longitude'][:]
    lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    ds.close()

    if hasattr(data, 'data'):
        data = data.data

    years = list(range(2021, 2021 + len(data)))
    return years, list(data)

def load_monthly_data(filename: str, var_name: str):
    filepath = KMA_DATA_DIR / filename
    if not filepath.exists():
        return None, None

    ds = nc.Dataset(filepath)
    lat_arr = ds.variables['latitude'][:]
    lon_arr = ds.variables['longitude'][:]
    lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    ds.close()

    if hasattr(data, 'data'):
        data = data.data

    return list(data)

def calculate_yearly_fwi(ta_monthly, rhm_monthly, ws_monthly, rn_monthly):
    """월별 데이터에서 연도별 최대 FWI 계산"""
    n_months = min(len(ta_monthly), len(rhm_monthly), len(ws_monthly), len(rn_monthly))
    n_years = n_months // 12

    yearly_max_fwi = []
    for y in range(n_years):
        start_idx = y * 12
        end_idx = start_idx + 12

        year_fwi = []
        for m in range(start_idx, end_idx):
            ta, rhm, ws, rn = ta_monthly[m], rhm_monthly[m], ws_monthly[m], rn_monthly[m]
            humidity_factor = 1 - (rhm / 100.0)
            wind_factor = 0.5 * (ws + 1)
            temp_factor = np.exp(0.05 * (ta - 10))
            rain_factor = np.exp(-0.001 * rn)
            fwi = max(humidity_factor * wind_factor * temp_factor * rain_factor, 0)
            year_fwi.append(fwi)

        yearly_max_fwi.append(max(year_fwi))

    years = list(range(2021, 2021 + n_years))
    return years, yearly_max_fwi

def calculate_yearly_min_spei(spei_monthly):
    """월별 SPEI에서 연도별 최소값 계산 (가뭄은 음수가 심각)"""
    n_years = len(spei_monthly) // 12

    yearly_min_spei = []
    for y in range(n_years):
        start_idx = y * 12
        end_idx = start_idx + 12
        yearly_min_spei.append(min(spei_monthly[start_idx:end_idx]))

    years = list(range(2021, 2021 + n_years))
    return years, yearly_min_spei

def load_water_scarcity_data():
    """
    물부족 (WSI) 데이터 로드 - 과거 데이터 + SSP 시나리오 기반 미래 추정

    로직:
    1. 과거 용수이용량 데이터에서 최근 평균 withdrawal 계산
    2. 과거 유량 데이터에서 TRWR baseline 계산
    3. SSP126 기후 시나리오(TA, RHM, RN)로 유효강수량 스케일링 → 미래 TRWR 추정
    4. WSI = Withdrawal / ARWR_future (2021-2100)
    """
    water_usage_file = WAMIS_DATA_DIR / "daejeon_water_usage.json"
    flow_data_file = WAMIS_DATA_DIR / "daily_flow_3012612_2019_2024.json"

    if not water_usage_file.exists():
        return None, None

    with open(water_usage_file, 'r', encoding='utf-8') as f:
        water_usage_raw = json.load(f)

    # 1. 최근 용수이용량 평균 (2019-2023)
    recent_withdrawals = []
    for item in water_usage_raw.get('list', []):
        year = int(item['year'])
        if 2019 <= year <= 2023:
            withdrawal = float(item['total']) * 1000  # 천톤 → m³
            recent_withdrawals.append(withdrawal)

    avg_withdrawal = np.mean(recent_withdrawals) if recent_withdrawals else 200000 * 1000

    # 2. TRWR baseline 계산
    trwr_baseline = 1.0e10
    if flow_data_file.exists():
        with open(flow_data_file, 'r', encoding='utf-8') as f:
            flow_raw = json.load(f)

        daily_by_year = {}
        for item in flow_raw.get('data', []):
            year = item.get('year')
            fw = float(item.get('fw', 0))
            if year not in daily_by_year:
                daily_by_year[year] = []
            daily_by_year[year].append(fw)

        annual_volumes = []
        for year, flows in daily_by_year.items():
            valid_flows = [f for f in flows if f > 0]
            if valid_flows:
                avg_daily = np.mean(valid_flows)
                volume = avg_daily * 365 * 86400
                annual_volumes.append(volume)

        if annual_volumes:
            trwr_baseline = np.mean(annual_volumes)

    # 3. SSP126 기후 데이터로 미래 스케일링 (유효강수량 P - ET0 기반)
    ta_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc", "TA")
    rn_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc", "RN")

    if not ta_monthly or not rn_monthly:
        return None, None

    n_years = min(len(ta_monthly), len(rn_monthly)) // 12

    # 기준기간 유효강수량 (간단히 RN - 온도 기반 ET0 근사)
    # ET0 ≈ 0.0023 × (T + 17.8) × R_a^0.5 × (T_max - T_min)^0.5 (Hargreaves 간략화)
    # 여기서는 간단히 ET0 ≈ 3 × T (월 기준 근사)

    baseline_p_eff = []
    for y in range(min(10, n_years)):  # 2021-2030 기준
        start_idx = y * 12
        annual_p_eff = 0
        for m in range(12):
            ta = ta_monthly[start_idx + m]
            rn = rn_monthly[start_idx + m]
            et0_approx = max(3 * ta, 0)  # 간단 근사
            annual_p_eff += (rn - et0_approx)
        baseline_p_eff.append(annual_p_eff)

    p_eff_baseline_mean = np.mean(baseline_p_eff) if baseline_p_eff else 500

    # 4. 연도별 WSI 계산 (2021-2100)
    years = []
    wsi_values = []

    for y in range(n_years):
        year = 2021 + y
        start_idx = y * 12

        # 연간 유효강수량 계산
        annual_p_eff = 0
        for m in range(12):
            ta = ta_monthly[start_idx + m]
            rn = rn_monthly[start_idx + m]
            et0_approx = max(3 * ta, 0)
            annual_p_eff += (rn - et0_approx)

        # 스케일링 계수
        scale_factor = annual_p_eff / p_eff_baseline_mean if p_eff_baseline_mean != 0 else 1.0
        scale_factor = max(scale_factor, 0.1)  # 극단값 방지

        # 미래 TRWR 및 ARWR
        trwr_future = trwr_baseline * scale_factor
        arwr_future = trwr_future * 0.63

        # WSI 계산
        wsi = avg_withdrawal / arwr_future if arwr_future > 0 else 0

        years.append(year)
        wsi_values.append(wsi)

    return years, wsi_values

def load_typhoon_data():
    """
    태풍 노출 지수 데이터 로드 - 과거 데이터 + SSP 시나리오 기반 미래 추정

    로직:
    1. 과거 태풍 데이터(2015-2024)에서 연평균 노출 지수 계산
    2. SSP126 기후 시나리오의 기온 상승에 따른 태풍 강도 스케일링
       - 해수면 온도 1°C 상승 당 태풍 강도 약 3-5% 증가 (IPCC)
       - 여기서는 기온 상승분 × 1.03 스케일링 적용
    3. 2021-2100년 태풍 노출 지수 추정
    """
    import math

    site_lon, site_lat = DAEJEON_LON, DAEJEON_LAT

    def is_inside_ellipse(dx_km, dy_km, semi_major, semi_minor, direction):
        if semi_major == 0 or semi_minor == 0:
            return False
        theta = math.radians(direction)
        x_rot = dx_km * math.cos(theta) + dy_km * math.sin(theta)
        y_rot = -dx_km * math.sin(theta) + dy_km * math.cos(theta)
        ellipse_value = (x_rot / semi_major) ** 2 + (y_rot / semi_minor) ** 2
        return ellipse_value <= 1.0

    w_tc = [0, 1, 3, 6]  # bin 가중치

    # 1. 과거 태풍 데이터에서 연평균 노출 지수 계산
    historical_exposure = []

    for year in range(2015, 2025):
        csv_file = TYPHOON_DATA_DIR / f"typhoon_{year}.csv"
        if not csv_file.exists():
            continue

        year_exposure = 0.0

        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        data_lines = [l for l in lines if not l.strip().startswith('#') and l.strip()]

        for line in data_lines:
            parts = line.split()
            if len(parts) < 17:
                continue

            try:
                grade = parts[0]
                typhoon_lon = float(parts[6])
                typhoon_lat = float(parts[7])

                avg_lat = (site_lat + typhoon_lat) / 2
                km_per_deg_lon = 111.0 * math.cos(math.radians(avg_lat))
                km_per_deg_lat = 111.0
                dx_km = (site_lon - typhoon_lon) * km_per_deg_lon
                dy_km = (site_lat - typhoon_lat) * km_per_deg_lat

                gale_long = float(parts[10]) if parts[10] != '-999' else 0
                gale_short = float(parts[11]) if parts[11] != '-999' else 0
                gale_dir = float(parts[12]) if parts[12] != '-999.9' else 0
                storm_long = float(parts[13]) if parts[13] != '-999' else 0
                storm_short = float(parts[14]) if parts[14] != '-999' else 0
                storm_dir = float(parts[15]) if parts[15] != '-999.9' else 0

                bin_inst = 0
                if is_inside_ellipse(dx_km, dy_km, storm_long, storm_short, storm_dir):
                    bin_inst = 3 if grade == 'TY' else 2
                elif is_inside_ellipse(dx_km, dy_km, gale_long, gale_short, gale_dir):
                    bin_inst = 1 if grade in ['TS', 'STS', 'TY'] else 0

                year_exposure += w_tc[bin_inst]

            except (ValueError, IndexError):
                continue

        historical_exposure.append(year_exposure)

    if not historical_exposure:
        return None, None

    # 과거 평균 및 표준편차
    avg_exposure = np.mean(historical_exposure)
    std_exposure = np.std(historical_exposure)

    # 2. SSP126 기온 데이터로 미래 스케일링
    ta_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc", "TA")

    if not ta_monthly:
        return None, None

    n_years = len(ta_monthly) // 12

    # 기준기간 평균 기온 (2021-2030)
    baseline_temps = []
    for y in range(min(10, n_years)):
        start_idx = y * 12
        year_avg = np.mean(ta_monthly[start_idx:start_idx + 12])
        baseline_temps.append(year_avg)
    baseline_temp_mean = np.mean(baseline_temps) if baseline_temps else 15.0

    # 3. 연도별 태풍 노출 지수 추정 (2021-2100)
    years = []
    typhoon_values = []

    np.random.seed(42)  # 재현성

    for y in range(n_years):
        year = 2021 + y
        start_idx = y * 12

        # 해당 연도 평균 기온
        year_avg_temp = np.mean(ta_monthly[start_idx:start_idx + 12])

        # 기온 상승분 기반 스케일링 (1°C 상승 → 3% 강도 증가)
        temp_increase = year_avg_temp - baseline_temp_mean
        intensity_scale = 1.0 + 0.03 * temp_increase

        # 과거 평균에 스케일링 적용 + 랜덤 변동 (표준편차 기반)
        expected_exposure = avg_exposure * intensity_scale
        random_factor = np.random.normal(1.0, std_exposure / avg_exposure if avg_exposure > 0 else 0.3)
        random_factor = max(0.5, min(1.5, random_factor))  # 극단값 방지

        typhoon_exposure = max(0, expected_exposure * random_factor)

        years.append(year)
        typhoon_values.append(typhoon_exposure)

    return years, typhoon_values

# 데이터 로드
print("데이터 로드 중...")

# 1. 폭염 (WSDI)
heat_years, heat_data = load_yearly_data("SSP126_WSDI_gridraw_yearly_2021-2100.nc", "WSDI")

# 2. 한파 (CSDI)
cold_years, cold_data = load_yearly_data("SSP126_CSDI_gridraw_yearly_2021-2100.nc", "CSDI")

# 3. 가뭄 (SPEI12) - 월별 → 연도별 최소값
spei_monthly = load_monthly_data("SSP126_SPEI12_gridraw_monthly_2021-2100.nc", "SPEI12")
if spei_monthly:
    drought_years, drought_data = calculate_yearly_min_spei(spei_monthly)
else:
    drought_years, drought_data = None, None

# 4. 내륙홍수 (RX1DAY)
flood_years, flood_data = load_yearly_data("SSP126_RX1DAY_gridraw_yearly_2021-2100.nc", "RX1DAY")

# 5. 도시홍수 (RAIN80)
urban_years, urban_data = load_yearly_data("SSP126_RAIN80_gridraw_yearly_2021-2100.nc", "RAIN80")

# 6. 산불 (FWI) - 월별 데이터로 연도별 최대 FWI 계산
ta_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc", "TA")
rhm_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RHM_gridraw_monthly_2021_2100.nc", "RHM")
ws_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_WS_gridraw_monthly_2021_2100.nc", "WS")
rn_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc", "RN")

if ta_monthly and rhm_monthly and ws_monthly and rn_monthly:
    fire_years, fire_data = calculate_yearly_fwi(ta_monthly, rhm_monthly, ws_monthly, rn_monthly)
else:
    fire_years, fire_data = None, None

# 7. 물부족 (WSI) - 과거 데이터
water_years, water_data = load_water_scarcity_data()

# 8. 태풍 (S_tc) - 과거 데이터
typhoon_years, typhoon_data = load_typhoon_data()

print("시각화 생성 중...")

# 그래프 생성 (2x4 = 8개 리스크)
fig, axes = plt.subplots(2, 4, figsize=(18, 10))
fig.suptitle('대덕 데이터센터 리스크별 연도별 강도지표 변화', fontsize=14, fontweight='bold')

# 색상 및 설정
configs = [
    ('폭염 (WSDI)', heat_years, heat_data, '#FF6B6B', 'WSDI (일)'),
    ('한파 (CSDI)', cold_years, cold_data, '#4ECDC4', 'CSDI (일)'),
    ('가뭄 (SPEI12 최소)', drought_years, drought_data, '#FFE66D', 'SPEI12'),
    ('하천홍수 (RX1DAY)', flood_years, flood_data, '#4A90D9', 'RX1DAY (mm)'),
    ('도시홍수 (RAIN80)', urban_years, urban_data, '#7B68EE', 'RAIN80 (mm/h)'),
    ('산불 (FWI 최대)', fire_years, fire_data, '#FF8C00', 'FWI'),
    ('물부족 (WSI)', water_years, water_data, '#87CEEB', 'WSI'),
    ('태풍 (S_tc)', typhoon_years, typhoon_data, '#9370DB', 'S_tc (노출지수)'),
]

for idx, (title, years, data, color, ylabel) in enumerate(configs):
    ax = axes[idx // 4, idx % 4]

    if years and data:
        # 메인 라인
        ax.plot(years, data, color=color, linewidth=1.5, alpha=0.8)

        # 이동평균 (데이터가 충분할 때)
        window = min(10, len(data) // 3) if len(data) > 10 else 3
        if len(data) >= window:
            moving_avg = np.convolve(data, np.ones(window)/window, mode='valid')
            ma_years = years[window-1:]
            ax.plot(ma_years, moving_avg, color='black', linewidth=2, linestyle='--',
                   label=f'{window}년 이동평균')
            ax.legend(loc='upper right', fontsize=8)

        # y축 범위 설정
        y_min, y_max = min(data), max(data)
        margin = (y_max - y_min) * 0.1 if y_max != y_min else 0.1
        ax.set_ylim(y_min - margin, y_max + margin)
        ax.set_xlim(min(years), max(years))

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('연도')
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
output_path = Path(__file__).parent / 'yearly_trends_all_risks.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"시각화 완료: {output_path}")

# 통계 요약 출력
print("\n" + "=" * 80)
print("연도별 강도지표 통계 요약")
print("=" * 80)
print(f"{'리스크':<20} {'기간':<20} {'최소값':<12} {'최대값':<12} {'평균':<12}")
print("-" * 80)

for title, years, data, color, ylabel in configs:
    if years and data:
        data_arr = np.array(data)
        min_val = data_arr.min()
        max_val = data_arr.max()
        mean_val = data_arr.mean()
        period = f"{min(years)}-{max(years)}"

        print(f"{title:<20} {period:<20} {min_val:<12.2f} {max_val:<12.2f} {mean_val:<12.2f}")
    else:
        print(f"{title:<20} 데이터 없음")

print("=" * 80)
