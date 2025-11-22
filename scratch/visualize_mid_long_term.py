"""
리스크별 중기/장기 전망 시각화
- 중기: 2026-2030년 (1년 단위)
- 장기: 2020s, 2030s, 2040s, 2050s, 2060s (10년 평균)
대덕 데이터센터 (대전광역시 유성구) 기준
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import netCDF4 as nc
import pandas as pd
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 대덕 데이터센터 좌표
DAEJEON_LAT = 36.35
DAEJEON_LON = 127.38
KMA_DATA_DIR = Path(__file__).parent / "KMA"
TYPHOON_DIR = Path(__file__).parent / "typhoon"
WAMIS_DIR = Path(__file__).parent / "wamis"

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

def calculate_yearly_min_spei(spei_monthly):
    n_years = len(spei_monthly) // 12
    yearly_min = []
    for y in range(n_years):
        start_idx = y * 12
        end_idx = start_idx + 12
        yearly_min.append(min(spei_monthly[start_idx:end_idx]))
    years = list(range(2021, 2021 + n_years))
    return years, yearly_min

def calculate_yearly_fwi(ta_monthly, rhm_monthly, ws_monthly, rn_monthly):
    n_months = min(len(ta_monthly), len(rhm_monthly), len(ws_monthly), len(rn_monthly))
    n_years = n_months // 12
    yearly_max = []
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
        yearly_max.append(max(year_fwi))
    years = list(range(2021, 2021 + n_years))
    return years, yearly_max

def load_typhoon_data():
    """태풍 데이터 로드 - 현재 미래 예측 데이터 없음"""
    # 태풍은 과거 데이터만 존재하며, SSP 시나리오 기반 미래 예측 데이터 필요
    return None, None

def get_decade_average(years, data, decade_start):
    """10년 평균 계산"""
    decade_data = [d for y, d in zip(years, data) if decade_start <= y < decade_start + 10]
    return np.mean(decade_data) if decade_data else None

print("데이터 로드 중...")

# 데이터 로드
heat_years, heat_data = load_yearly_data("SSP126_WSDI_gridraw_yearly_2021-2100.nc", "WSDI")
cold_years, cold_data = load_yearly_data("SSP126_CSDI_gridraw_yearly_2021-2100.nc", "CSDI")
flood_years, flood_data = load_yearly_data("SSP126_RX1DAY_gridraw_yearly_2021-2100.nc", "RX1DAY")
urban_years, urban_data = load_yearly_data("SSP126_RAIN80_gridraw_yearly_2021-2100.nc", "RAIN80")

spei_monthly = load_monthly_data("SSP126_SPEI12_gridraw_monthly_2021-2100.nc", "SPEI12")
if spei_monthly:
    drought_years, drought_data = calculate_yearly_min_spei(spei_monthly)
else:
    drought_years, drought_data = None, None

ta_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc", "TA")
rhm_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RHM_gridraw_monthly_2021_2100.nc", "RHM")
ws_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_WS_gridraw_monthly_2021_2100.nc", "WS")
rn_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc", "RN")

if ta_monthly and rhm_monthly and ws_monthly and rn_monthly:
    fire_years, fire_data = calculate_yearly_fwi(ta_monthly, rhm_monthly, ws_monthly, rn_monthly)
else:
    fire_years, fire_data = None, None

typhoon_years, typhoon_data = load_typhoon_data()

# 데이터 구성
datasets = {
    '폭염\n(WSDI)': (heat_years, heat_data, '#FF6B6B', 'WSDI (일)'),
    '한파\n(CSDI)': (cold_years, cold_data, '#4ECDC4', 'CSDI (일)'),
    '가뭄\n(SPEI12)': (drought_years, drought_data, '#FFE66D', 'SPEI12 최소'),
    '하천홍수\n(RX1DAY)': (flood_years, flood_data, '#4A90D9', 'RX1DAY (mm)'),
    '도시홍수\n(RAIN80)': (urban_years, urban_data, '#7B68EE', 'RAIN80 (mm/h)'),
    '산불\n(FWI)': (fire_years, fire_data, '#FF8C00', 'FWI 최대'),
}

print("그래프 생성 중...")

# ============================================================
# 1. 중기 전망 (2026-2030)
# ============================================================
fig1, axes1 = plt.subplots(2, 3, figsize=(14, 8))
fig1.suptitle('대덕 데이터센터 중기 리스크 전망 (2026-2030)', fontsize=14, fontweight='bold')

mid_years = [2026, 2027, 2028, 2029, 2030]

for idx, (title, (years, data, color, ylabel)) in enumerate(datasets.items()):
    ax = axes1[idx // 3, idx % 3]

    if years and data:
        # 중기 데이터 추출
        mid_data = [data[years.index(y)] for y in mid_years if y in years]
        mid_x = [y for y in mid_years if y in years]

        if mid_data:
            bars = ax.bar(mid_x, mid_data, color=color, edgecolor='black', alpha=0.8)

            # 값 표시
            for bar, val in zip(bars, mid_data):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       f'{val:.1f}', ha='center', va='bottom', fontsize=9)

            # 평균선
            avg = np.mean(mid_data)
            ax.axhline(y=avg, color='black', linestyle='--', alpha=0.7, label=f'평균: {avg:.1f}')
            ax.legend(loc='upper right', fontsize=8)

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('연도')
    ax.set_ylabel(ylabel)
    ax.set_xticks(mid_years)
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output1 = Path(__file__).parent / 'mid_term_forecast.png'
plt.savefig(output1, dpi=150, bbox_inches='tight')
plt.close()
print(f"중기 전망 저장: {output1}")

# ============================================================
# 2. 장기 전망 (10년 평균)
# ============================================================
fig2, axes2 = plt.subplots(2, 3, figsize=(14, 8))
fig2.suptitle('대덕 데이터센터 장기 리스크 전망 (10년 평균)', fontsize=14, fontweight='bold')

decades = [2020, 2030, 2040, 2050, 2060]
decade_labels = ['2020s\n(2021-2030)', '2030s\n(2031-2040)', '2040s\n(2041-2050)',
                 '2050s\n(2051-2060)', '2060s\n(2061-2070)']

for idx, (title, (years, data, color, ylabel)) in enumerate(datasets.items()):
    ax = axes2[idx // 3, idx % 3]

    if years and data:
        decade_avgs = []
        for decade in decades:
            avg = get_decade_average(years, data, decade + 1)  # 2021-2030 for 2020s
            decade_avgs.append(avg if avg is not None else 0)

        x_pos = range(len(decades))
        bars = ax.bar(x_pos, decade_avgs, color=color, edgecolor='black', alpha=0.8)

        # 값 표시
        for bar, val in zip(bars, decade_avgs):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                       f'{val:.1f}', ha='center', va='bottom', fontsize=9)

        # 추세선
        if all(v > 0 for v in decade_avgs):
            z = np.polyfit(range(len(decade_avgs)), decade_avgs, 1)
            trend = "↑ 증가" if z[0] > 0 else "↓ 감소"
            ax.text(0.02, 0.98, trend, transform=ax.transAxes,
                   fontsize=10, fontweight='bold', va='top', ha='left',
                   color='red' if z[0] > 0 else 'blue')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(decade_labels, fontsize=8)

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output2 = Path(__file__).parent / 'long_term_forecast.png'
plt.savefig(output2, dpi=150, bbox_inches='tight')
plt.close()
print(f"장기 전망 저장: {output2}")

# ============================================================
# 3. 통합 대시보드 (중기 + 장기)
# ============================================================
fig3, axes3 = plt.subplots(2, 6, figsize=(18, 10))
fig3.suptitle('대덕 데이터센터 리스크 전망 대시보드\n중기 (2026-2030) / 장기 (10년 평균)', fontsize=14, fontweight='bold')

for idx, (title, (years, data, color, ylabel)) in enumerate(datasets.items()):
    # 중기 (상단)
    ax_mid = axes3[0, idx]
    if years and data:
        mid_data = [data[years.index(y)] for y in mid_years if y in years]
        mid_x = [y for y in mid_years if y in years]
        if mid_data:
            ax_mid.bar(mid_x, mid_data, color=color, edgecolor='black', alpha=0.8)
            avg = np.mean(mid_data)
            ax_mid.axhline(y=avg, color='black', linestyle='--', alpha=0.7)
    ax_mid.set_title(f'{title}\n중기', fontsize=10, fontweight='bold')
    ax_mid.set_xticks([2026, 2028, 2030])
    ax_mid.tick_params(axis='x', labelsize=8)
    ax_mid.grid(True, alpha=0.3, axis='y')

    # 장기 (하단)
    ax_long = axes3[1, idx]
    if years and data:
        decade_avgs = [get_decade_average(years, data, d + 1) or 0 for d in decades]
        ax_long.bar(range(len(decades)), decade_avgs, color=color, edgecolor='black', alpha=0.8)
    ax_long.set_title('장기', fontsize=10)
    ax_long.set_xticks(range(len(decades)))
    ax_long.set_xticklabels(['20s', '30s', '40s', '50s', '60s'], fontsize=8)
    ax_long.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output3 = Path(__file__).parent / 'risk_dashboard.png'
plt.savefig(output3, dpi=150, bbox_inches='tight')
plt.close()
print(f"대시보드 저장: {output3}")

# ============================================================
# 요약 출력
# ============================================================
print("\n" + "="*80)
print("리스크 전망 요약")
print("="*80)
print(f"\n{'리스크':<15} {'2026-2030 평균':<15} {'2020s':<12} {'2040s':<12} {'2060s':<12} {'추세':<10}")
print("-"*80)

for title, (years, data, color, ylabel) in datasets.items():
    if years and data:
        # 중기 평균
        mid_data = [data[years.index(y)] for y in mid_years if y in years]
        mid_avg = np.mean(mid_data) if mid_data else 0

        # 장기 평균
        avg_2020s = get_decade_average(years, data, 2021) or 0
        avg_2040s = get_decade_average(years, data, 2041) or 0
        avg_2060s = get_decade_average(years, data, 2061) or 0

        # 추세
        if avg_2020s > 0 and avg_2060s > 0:
            change = (avg_2060s - avg_2020s) / avg_2020s * 100
            trend = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"
        else:
            trend = "N/A"

        clean_title = title.replace('\n', ' ')
        print(f"{clean_title:<15} {mid_avg:<15.2f} {avg_2020s:<12.2f} {avg_2040s:<12.2f} {avg_2060s:<12.2f} {trend:<10}")

print("="*80)
print("\n※ 물부족/태풍: 별도 데이터 필요 (WAMIS 용수이용량, KMA 태풍 Best Track)")
print("="*80)
