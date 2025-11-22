"""
리스크별 연도별 강도지표 변화 시각화 (꺾은선 그래프)
대덕 데이터센터 (대전광역시 유성구) 기준
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

print("시각화 생성 중...")

# 그래프 생성
fig, axes = plt.subplots(3, 2, figsize=(14, 12))
fig.suptitle('대덕 데이터센터 리스크별 연도별 강도지표 변화 (SSP126, 2021-2100)', fontsize=14, fontweight='bold')

# 색상 및 설정
configs = [
    ('폭염 (WSDI)', heat_years, heat_data, '#FF6B6B', 'WSDI (일)', [(0,3,'Low'), (3,8,'Mod'), (8,20,'High'), (20,100,'Extreme')]),
    ('한파 (CSDI)', cold_years, cold_data, '#4ECDC4', 'CSDI (일)', [(0,3,'Low'), (3,7,'Mod'), (7,15,'High'), (15,50,'Extreme')]),
    ('가뭄 (SPEI12 최소)', drought_years, drought_data, '#FFE66D', 'SPEI12', [(-1,2,'정상'), (-1.5,-1,'중간'), (-2,-1.5,'심각'), (-3,-2,'극심')]),
    ('하천홍수 (RX1DAY)', flood_years, flood_data, '#4A90D9', 'RX1DAY (mm)', [(0,150,'Low'), (150,180,'Mod'), (180,200,'High'), (200,250,'Extreme')]),
    ('도시홍수 (RAIN80)', urban_years, urban_data, '#7B68EE', 'RAIN80 (mm/h)', [(0,1,'Low'), (1,3,'Mod'), (3,5,'High'), (5,10,'Extreme')]),
    ('산불 (FWI 최대)', fire_years, fire_data, '#FF8C00', 'FWI', [(0,11.2,'Low'), (11.2,21.3,'Mod'), (21.3,38,'High'), (38,60,'V.High')])
]

for idx, (title, years, data, color, ylabel, thresholds) in enumerate(configs):
    ax = axes[idx // 2, idx % 2]

    if years and data:
        # 메인 라인
        ax.plot(years, data, color=color, linewidth=1.5, alpha=0.8)

        # 10년 이동평균
        if len(data) >= 10:
            window = 10
            moving_avg = np.convolve(data, np.ones(window)/window, mode='valid')
            ma_years = years[window-1:]
            ax.plot(ma_years, moving_avg, color='black', linewidth=2, linestyle='--', label='10년 이동평균')

        # 임계값 라인
        for i, (low, high, label) in enumerate(thresholds):
            if i > 0:  # 첫 번째는 스킵
                ax.axhline(y=low, color='gray', linestyle=':', alpha=0.5)

        # 배경 영역 (bin별)
        y_min, y_max = min(data), max(data)
        margin = (y_max - y_min) * 0.1

        ax.set_xlim(min(years), max(years))
        ax.set_ylim(y_min - margin, y_max + margin)
        ax.legend(loc='upper right', fontsize=8)

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('연도')
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)

    # x축 간격 조정
    ax.set_xticks(range(2020, 2101, 20))

plt.tight_layout()
output_path = Path(__file__).parent / 'yearly_trends_visualization.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"시각화 완료: {output_path}")

# 통계 요약 출력
print("\n" + "="*70)
print("연도별 강도지표 통계 요약")
print("="*70)
print(f"{'리스크':<15} {'최소값':<12} {'최대값':<12} {'평균':<12} {'추세':<12}")
print("-"*70)

for title, years, data, color, ylabel, _ in configs:
    if years and data:
        data_arr = np.array(data)
        min_val = data_arr.min()
        max_val = data_arr.max()
        mean_val = data_arr.mean()

        # 선형 추세 계산
        z = np.polyfit(years, data, 1)
        trend = "증가 ↑" if z[0] > 0 else "감소 ↓"
        trend_val = abs(z[0] * 10)  # 10년당 변화량

        print(f"{title:<15} {min_val:<12.2f} {max_val:<12.2f} {mean_val:<12.2f} {trend} ({trend_val:.2f}/10년)")
    else:
        print(f"{title:<15} 데이터 없음")

print("="*70)
