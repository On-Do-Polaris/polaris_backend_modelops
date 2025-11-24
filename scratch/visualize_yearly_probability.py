"""
9개 리스크별 연도별 발생확률 변화 시각화 (꺾은선 그래프)
대덕 데이터센터 (대전광역시 유성구) 기준

각 리스크의 연도별 강도지표를 계산하고, bin 분류 결과를 시각화
"""
import sys
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import netCDF4 as nc
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 대덕 데이터센터 좌표
DAEJEON_LAT = 36.35
DAEJEON_LON = 127.38
KMA_DATA_DIR = Path(__file__).parent / "KMA"
WAMIS_DATA_DIR = Path(__file__).parent / "wamis"
TYPHOON_DATA_DIR = Path(__file__).parent / "typhoon"
CMIP6_ZOS_FILE = Path(__file__).parent / "zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc"


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


def classify_heat(wsdi_values):
    """폭염 bin 분류: [0,3), [3,8), [8,20), [20,inf)"""
    bins = [(0, 3), (3, 8), (8, 20), (20, float('inf'))]
    return classify_values(wsdi_values, bins)


def classify_cold(csdi_values):
    """한파 bin 분류: [0,3), [3,7), [7,15), [15,inf)"""
    bins = [(0, 3), (3, 7), (7, 15), (15, float('inf'))]
    return classify_values(csdi_values, bins)


def classify_drought(spei_values):
    """가뭄 bin 분류 (음수가 심각): (-inf,-2), [-2,-1.5), [-1.5,-1), [-1,inf)"""
    results = []
    for val in spei_values:
        if val < -2:
            results.append(3)  # 극심
        elif val < -1.5:
            results.append(2)  # 심각
        elif val < -1:
            results.append(1)  # 중간
        else:
            results.append(0)  # 정상
    return results


def classify_inland_flood(rx1day_values):
    """내륙홍수 bin 분류: [0,80), [80,110), [110,150), [150,inf)"""
    bins = [(0, 80), (80, 110), (110, 150), (150, float('inf'))]
    return classify_values(rx1day_values, bins)


def classify_urban_flood(rain80_values, urban_ratio=0.75, slope=0.02):
    """도시홍수 bin 분류 (침수심 기반)"""
    results = []
    for rain80 in rain80_values:
        # 침수심 계산 (간략화)
        runoff_coef = 0.3 + 0.6 * urban_ratio
        drainage = 30 * (1 + slope * 10)
        excess = max(rain80 * runoff_coef - drainage, 0)
        flood_depth = excess * 0.01

        if flood_depth <= 0:
            results.append(0)
        elif flood_depth < 0.3:
            results.append(1)
        elif flood_depth < 1.0:
            results.append(2)
        else:
            results.append(3)
    return results


def classify_wildfire(ta_monthly, rhm_monthly, ws_monthly, rn_monthly):
    """산불 연도별 최대 FWI 기반 bin 분류"""
    n_months = min(len(ta_monthly), len(rhm_monthly), len(ws_monthly), len(rn_monthly))
    n_years = n_months // 12

    results = []
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

        max_fwi = max(year_fwi)
        # FWI bin: [0,11.2), [11.2,21.3), [21.3,38), [38,inf)
        if max_fwi < 11.2:
            results.append(0)
        elif max_fwi < 21.3:
            results.append(1)
        elif max_fwi < 38:
            results.append(2)
        else:
            results.append(3)

    return results


def classify_coastal_flood():
    """해수면 상승 연도별 bin 분류"""
    if not CMIP6_ZOS_FILE.exists():
        return None, None

    ds = nc.Dataset(CMIP6_ZOS_FILE)
    lat_2d = ds.variables['latitude'][:]
    lon_2d = ds.variables['longitude'][:]
    zos_data = ds.variables['zos'][:]

    target_lat = 36.35
    target_lon = 126.5  # 서해안

    lat_diff = np.abs(lat_2d - target_lat)
    lon_diff = np.abs(lon_2d - target_lon)
    dist = np.sqrt(lat_diff**2 + lon_diff**2)
    min_idx = np.unravel_index(np.argmin(dist), dist.shape)
    j_idx, i_idx = min_idx

    zos_timeseries = zos_data[:, j_idx, i_idx]
    if hasattr(zos_timeseries, 'data'):
        zos_timeseries = zos_timeseries.data

    ds.close()

    n_months = len(zos_timeseries)
    n_years = n_months // 12
    ground_level = 0.5  # 지반고도 0.5m

    results = []
    years = []
    for year_idx in range(n_years):
        year = 2015 + year_idx
        start_month = year_idx * 12
        end_month = start_month + 12
        monthly_zos = zos_timeseries[start_month:end_month]

        # 연도별 최대 침수심 계산
        max_inundation = 0
        for zos_m in monthly_zos:
            inundation = max(zos_m - ground_level, 0)
            max_inundation = max(max_inundation, inundation)

        # bin 분류: 0, [0,0.3), [0.3,1), [1,inf)
        if max_inundation == 0:
            results.append(0)
        elif max_inundation < 0.3:
            results.append(1)
        elif max_inundation < 1.0:
            results.append(2)
        else:
            results.append(3)

        years.append(year)

    return years, results


def classify_values(values, bins):
    """일반적인 bin 분류"""
    results = []
    for val in values:
        for i, (low, high) in enumerate(bins):
            if low <= val < high:
                results.append(i)
                break
        else:
            results.append(len(bins) - 1)
    return results


def get_risk_probability(bin_indices, target_bin=None):
    """bin 인덱스에서 위험 발생 확률 계산 (bin1 이상)"""
    if target_bin is not None:
        return [1 if b >= target_bin else 0 for b in bin_indices]
    else:
        # bin1 이상이면 위험
        return [1 if b >= 1 else 0 for b in bin_indices]


def main():
    print("=" * 70)
    print("9개 리스크별 연도별 발생확률 시각화")
    print("대상: 대덕 데이터센터 (대전광역시 유성구)")
    print("=" * 70)

    print("\n데이터 로드 및 확률 계산 중...")

    # 1. 폭염 (WSDI)
    print("  1/9 폭염...")
    heat_years, heat_data = load_yearly_data("SSP126_WSDI_gridraw_yearly_2021-2100.nc", "WSDI")
    heat_bins = classify_heat(heat_data) if heat_data else None

    # 2. 한파 (CSDI)
    print("  2/9 한파...")
    cold_years, cold_data = load_yearly_data("SSP126_CSDI_gridraw_yearly_2021-2100.nc", "CSDI")
    cold_bins = classify_cold(cold_data) if cold_data else None

    # 3. 가뭄 (SPEI12) - 연도별 최소값
    print("  3/9 가뭄...")
    spei_monthly = load_monthly_data("SSP126_SPEI12_gridraw_monthly_2021-2100.nc", "SPEI12")
    if spei_monthly:
        n_years = len(spei_monthly) // 12
        drought_years = list(range(2021, 2021 + n_years))
        yearly_min_spei = []
        for y in range(n_years):
            yearly_min_spei.append(min(spei_monthly[y*12:(y+1)*12]))
        drought_bins = classify_drought(yearly_min_spei)
    else:
        drought_years, drought_bins = None, None

    # 4. 내륙홍수 (RX1DAY)
    print("  4/9 내륙홍수...")
    flood_years, flood_data = load_yearly_data("SSP126_RX1DAY_gridraw_yearly_2021-2100.nc", "RX1DAY")
    flood_bins = classify_inland_flood(flood_data) if flood_data else None

    # 5. 도시홍수 (RAIN80)
    print("  5/9 도시홍수...")
    urban_years, urban_data = load_yearly_data("SSP126_RAIN80_gridraw_yearly_2021-2100.nc", "RAIN80")
    urban_bins = classify_urban_flood(urban_data) if urban_data else None

    # 6. 산불 (FWI)
    print("  6/9 산불...")
    ta_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc", "TA")
    rhm_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RHM_gridraw_monthly_2021_2100.nc", "RHM")
    ws_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_WS_gridraw_monthly_2021_2100.nc", "WS")
    rn_monthly = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc", "RN")
    if ta_monthly and rhm_monthly and ws_monthly and rn_monthly:
        n_years = len(ta_monthly) // 12
        fire_years = list(range(2021, 2021 + n_years))
        fire_bins = classify_wildfire(ta_monthly, rhm_monthly, ws_monthly, rn_monthly)
    else:
        fire_years, fire_bins = None, None

    # 7. 물부족 (단일 값이므로 수평선)
    print("  7/9 물부족...")
    water_years = list(range(2021, 2101))
    water_bins = [0] * len(water_years)  # 기본값 (데이터 부족)

    # 8. 태풍 (단일 값이므로 수평선)
    print("  8/9 태풍...")
    typhoon_years = list(range(2021, 2101))
    typhoon_bins = [1] * len(typhoon_years)  # 60% 영향권 (bin1)

    # 9. 해수면 상승 (ZOS)
    print("  9/9 해수면 상승...")
    coastal_years, coastal_bins = classify_coastal_flood()

    print("\n시각화 생성 중...")

    # 그래프 생성 (3x3)
    fig, axes = plt.subplots(3, 3, figsize=(16, 12))
    fig.suptitle('대덕 데이터센터 9개 리스크별 연도별 위험등급 변화 (SSP126)', fontsize=14, fontweight='bold')

    configs = [
        ('폭염 (WSDI)', heat_years, heat_bins, '#FF6B6B', ['정상', '주의', '경계', '심각']),
        ('한파 (CSDI)', cold_years, cold_bins, '#4ECDC4', ['정상', '주의', '경계', '심각']),
        ('가뭄 (SPEI12)', drought_years, drought_bins, '#FFE66D', ['정상', '중간', '심각', '극심']),
        ('내륙홍수 (RX1DAY)', flood_years, flood_bins, '#4A90D9', ['정상', '주의', '경계', '심각']),
        ('도시홍수 (RAIN80)', urban_years, urban_bins, '#7B68EE', ['없음', '경미', '중간', '심각']),
        ('산불 (FWI)', fire_years, fire_bins, '#FF8C00', ['낮음', '보통', '높음', '매우높음']),
        ('물부족 (WSI)', water_years, water_bins, '#2ECC71', ['정상', '주의', '경계', '심각']),
        ('태풍 (S_tc)', typhoon_years, typhoon_bins, '#9B59B6', ['무영향', '강풍권', '폭풍권', '직접영향']),
        ('해수면상승 (ZOS)', coastal_years, coastal_bins, '#1ABC9C', ['없음', '0-0.3m', '0.3-1m', '≥1m'])
    ]

    for idx, (title, years, bins, color, labels) in enumerate(configs):
        ax = axes[idx // 3, idx % 3]

        if years and bins:
            # 꺾은선 그래프
            ax.plot(years, bins, color=color, linewidth=1.5, alpha=0.7)
            ax.fill_between(years, bins, alpha=0.3, color=color)

            # 10년 이동평균
            if len(bins) >= 10:
                window = 10
                moving_avg = np.convolve(bins, np.ones(window)/window, mode='valid')
                ma_years = years[window-1:]
                ax.plot(ma_years, moving_avg, color='black', linewidth=2, linestyle='--', label='10년 이동평균')
                ax.legend(loc='upper right', fontsize=8)

            ax.set_xlim(min(years), max(years))
            ax.set_ylim(-0.2, 3.5)

            # Y축 라벨
            ax.set_yticks([0, 1, 2, 3])
            ax.set_yticklabels(labels, fontsize=8)

            # 위험 등급 배경색
            ax.axhspan(-0.2, 0.5, alpha=0.1, color='green')
            ax.axhspan(0.5, 1.5, alpha=0.1, color='yellow')
            ax.axhspan(1.5, 2.5, alpha=0.1, color='orange')
            ax.axhspan(2.5, 3.5, alpha=0.1, color='red')
        else:
            ax.text(0.5, 0.5, '데이터 없음', ha='center', va='center', transform=ax.transAxes, fontsize=12)

        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('연도')
        ax.set_ylabel('위험등급')
        ax.grid(True, alpha=0.3, axis='x')
        ax.set_xticks(range(2020, 2101, 20))

    plt.tight_layout()
    output_path = Path(__file__).parent / 'yearly_probability_all_risks.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\n시각화 완료: {output_path}")

    # 통계 요약
    print("\n" + "=" * 70)
    print("리스크별 위험등급 통계 요약")
    print("=" * 70)
    print(f"{'리스크':<15} {'평균등급':<10} {'최대등급':<10} {'위험발생률':<15}")
    print("-" * 70)

    for title, years, bins, _, labels in configs:
        if years and bins:
            bins_arr = np.array(bins)
            mean_bin = bins_arr.mean()
            max_bin = bins_arr.max()
            risk_rate = np.sum(bins_arr >= 1) / len(bins_arr) * 100

            print(f"{title:<15} {mean_bin:<10.2f} {int(max_bin):<10} {risk_rate:<15.1f}%")
        else:
            print(f"{title:<15} 데이터 없음")

    print("=" * 70)


if __name__ == "__main__":
    main()
