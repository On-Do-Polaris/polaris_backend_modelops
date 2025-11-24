"""
Probability Agent 테스트 스크립트
대덕 데이터센터 (대전광역시 유성구) 좌표 기준으로 각 리스크별 발생확률 계산 테스트
"""
import sys
import json
from pathlib import Path
import numpy as np
import netCDF4 as nc

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aiops.agents.probability_calculate.high_temperature_probability_agent import HighTemperatureProbabilityAgent
from aiops.agents.probability_calculate.cold_wave_probability_agent import ColdWaveProbabilityAgent
from aiops.agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent
from aiops.agents.probability_calculate.inland_flood_probability_agent import InlandFloodProbabilityAgent
from aiops.agents.probability_calculate.urban_flood_probability_agent import UrbanFloodProbabilityAgent
from aiops.agents.probability_calculate.wildfire_probability_agent import WildfireProbabilityAgent
from aiops.agents.probability_calculate.water_scarcity_probability_agent import WaterScarcityProbabilityAgent
from aiops.agents.probability_calculate.typhoon_probability_agent import TyphoonProbabilityAgent
from aiops.agents.probability_calculate.coastal_flood_probability_agent import CoastalFloodProbabilityAgent

# 대덕 데이터센터 좌표 (대전광역시 유성구 엑스포로 325)
DAEJEON_LAT = 36.35
DAEJEON_LON = 127.38

KMA_DATA_DIR = Path(__file__).parent / "KMA"
WAMIS_DATA_DIR = Path(__file__).parent / "wamis"
TYPHOON_DATA_DIR = Path(__file__).parent / "typhoon"
CMIP6_ZOS_FILE = Path(__file__).parent / "zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc"


def get_nearest_idx(lat_arr, lon_arr, target_lat, target_lon):
    """가장 가까운 격자점 인덱스 찾기"""
    lat_idx = np.argmin(np.abs(lat_arr - target_lat))
    lon_idx = np.argmin(np.abs(lon_arr - target_lon))
    return lat_idx, lon_idx


def load_yearly_data(filename: str, var_name: str) -> list:
    """연도별 NC 데이터 로드 (대전 좌표)"""
    filepath = KMA_DATA_DIR / filename
    if not filepath.exists():
        print(f"  [WARN] 파일 없음: {filename}")
        return []

    ds = nc.Dataset(filepath)
    lat_arr = ds.variables['latitude'][:]
    lon_arr = ds.variables['longitude'][:]
    lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    ds.close()

    # masked array 처리
    if hasattr(data, 'data'):
        data = data.data

    return list(data)


def load_monthly_data(filename: str, var_name: str) -> list:
    """월별 NC 데이터 로드 (대전 좌표) - flatten하여 반환"""
    filepath = KMA_DATA_DIR / filename
    if not filepath.exists():
        print(f"  [WARN] 파일 없음: {filename}")
        return []

    ds = nc.Dataset(filepath)
    lat_arr = ds.variables['latitude'][:]
    lon_arr = ds.variables['longitude'][:]
    lat_idx, lon_idx = get_nearest_idx(lat_arr, lon_arr, DAEJEON_LAT, DAEJEON_LON)

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    ds.close()

    if hasattr(data, 'data'):
        data = data.data

    return list(data)


def test_high_temperature():
    """폭염 (WSDI) 테스트"""
    print("\n" + "=" * 60)
    print("1. 폭염 (Extreme Heat) - WSDI")
    print("=" * 60)

    wsdi_data = load_yearly_data("SSP126_WSDI_gridraw_yearly_2021-2100.nc", "WSDI")
    if not wsdi_data:
        return None

    print(f"  데이터: {len(wsdi_data)}년, 범위: {min(wsdi_data):.1f} ~ {max(wsdi_data):.1f}")

    agent = HighTemperatureProbabilityAgent()
    collected_data = {
        'climate_data': {
            'wsdi': wsdi_data
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_cold_wave():
    """한파 (CSDI) 테스트"""
    print("\n" + "=" * 60)
    print("2. 한파 (Extreme Cold) - CSDI")
    print("=" * 60)

    csdi_data = load_yearly_data("SSP126_CSDI_gridraw_yearly_2021-2100.nc", "CSDI")
    if not csdi_data:
        return None

    print(f"  데이터: {len(csdi_data)}년, 범위: {min(csdi_data):.1f} ~ {max(csdi_data):.1f}")

    agent = ColdWaveProbabilityAgent()
    collected_data = {
        'climate_data': {
            'csdi': csdi_data
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_drought():
    """가뭄 (SPEI12) 테스트"""
    print("\n" + "=" * 60)
    print("3. 가뭄 (Drought) - SPEI12")
    print("=" * 60)

    spei12_data = load_monthly_data("SSP126_SPEI12_gridraw_monthly_2021-2100.nc", "SPEI12")
    if not spei12_data:
        return None

    print(f"  데이터: {len(spei12_data)}개월, 범위: {min(spei12_data):.2f} ~ {max(spei12_data):.2f}")

    agent = DroughtProbabilityAgent()
    collected_data = {
        'climate_data': {
            'spei12': spei12_data
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_inland_flood():
    """내륙홍수 (RX1DAY) 테스트"""
    print("\n" + "=" * 60)
    print("4. 내륙홍수 (Inland Flood) - RX1DAY")
    print("=" * 60)

    rx1day_data = load_yearly_data("SSP126_RX1DAY_gridraw_yearly_2021-2100.nc", "RX1DAY")
    if not rx1day_data:
        return None

    print(f"  데이터: {len(rx1day_data)}년, 범위: {min(rx1day_data):.1f} ~ {max(rx1day_data):.1f} mm")

    agent = InlandFloodProbabilityAgent()
    collected_data = {
        'climate_data': {
            'rx1day': rx1day_data
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_urban_flood():
    """도시홍수 (RAIN80 + 지형데이터) 테스트"""
    print("\n" + "=" * 60)
    print("5. 도시홍수 (Urban Flood) - RAIN80 + DEM/토지피복도")
    print("=" * 60)

    rain80_data = load_yearly_data("SSP126_RAIN80_gridraw_yearly_2021-2100.nc", "RAIN80")
    if not rain80_data:
        return None

    print(f"  데이터: {len(rain80_data)}년, 범위: {min(rain80_data):.1f} ~ {max(rain80_data):.1f} mm/h")

    agent = UrbanFloodProbabilityAgent()

    # 대덕 데이터센터: 고도 도시화 지역, 완만한 경사
    collected_data = {
        'climate_data': {
            'rain80': rain80_data
        },
        'terrain_data': {
            'urban_ratio': 0.75,  # 유성구 - 고도 도시화
            'slope': 0.02        # 2% 경사
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_wildfire():
    """산불 (FWI) 테스트"""
    print("\n" + "=" * 60)
    print("6. 산불 (Wildfire) - FWI")
    print("=" * 60)

    # 실제 월별 NC 파일에서 데이터 로드 (AR6 형식)
    ta_data = load_monthly_data("AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc", "TA")
    rhm_data = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RHM_gridraw_monthly_2021_2100.nc", "RHM")
    ws_data = load_monthly_data("AR6_SSP126_5ENSMN_skorea_WS_gridraw_monthly_2021_2100.nc", "WS")
    rn_data = load_monthly_data("AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc", "RN")

    if not ta_data or not rhm_data or not ws_data or not rn_data:
        print("  [WARN] 월별 데이터 파일 로드 실패, 더미 데이터로 테스트")
        np.random.seed(42)
        n_months = 960
        ta_data = list(np.random.uniform(5, 30, n_months))
        rhm_data = list(np.random.uniform(40, 90, n_months))
        ws_data = list(np.random.uniform(1, 8, n_months))
        rn_data = list(np.random.uniform(0, 200, n_months))

    print(f"  데이터: {len(ta_data)}개월")
    print(f"    TA: {min(ta_data):.1f} ~ {max(ta_data):.1f} °C")
    print(f"    RHM: {min(rhm_data):.1f} ~ {max(rhm_data):.1f} %")
    print(f"    WS: {min(ws_data):.1f} ~ {max(ws_data):.1f} m/s")
    print(f"    RN: {min(rn_data):.1f} ~ {max(rn_data):.1f} mm")

    try:
        agent = WildfireProbabilityAgent()

        collected_data = {
            'climate_data': {
                'ta': ta_data,
                'rhm': rhm_data,
                'ws': ws_data,
                'rn': rn_data
            }
        }

        result = agent.calculate_probability(collected_data)
        print_result(result)
        return result
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def test_water_scarcity():
    """물부족 (WSI) 테스트"""
    print("\n" + "=" * 60)
    print("7. 물부족 (Water Scarcity) - WSI")
    print("=" * 60)

    # WAMIS 용수이용량 데이터 로드
    water_usage_file = WAMIS_DATA_DIR / "daejeon_water_usage.json"
    flow_data_file = WAMIS_DATA_DIR / "daily_flow_gapcheon_3008680_2014_2024.json"

    if not water_usage_file.exists():
        print(f"  [WARN] 파일 없음: {water_usage_file}")
        return None

    with open(water_usage_file, 'r', encoding='utf-8') as f:
        water_usage_raw = json.load(f)

    # water_data 형식으로 변환
    water_data = []
    for item in water_usage_raw.get('list', []):
        year = int(item['year'])
        # total은 천톤 단위 -> m³로 변환 (× 1000)
        withdrawal = float(item['total']) * 1000  # 천톤 → 톤 → m³
        water_data.append({'year': year, 'withdrawal': withdrawal})

    # 최근 데이터만 사용 (1991-2023)
    water_data = [w for w in water_data if 1991 <= w['year'] <= 2023]
    water_data.sort(key=lambda x: x['year'])

    print(f"  용수이용량: {len(water_data)}년 ({water_data[0]['year']}-{water_data[-1]['year']})")

    # 유량 데이터 로드
    flow_data = []
    if flow_data_file.exists():
        with open(flow_data_file, 'r', encoding='utf-8') as f:
            flow_raw = json.load(f)

        # 연도별 일유량 데이터 정리
        daily_by_year = {}
        for item in flow_raw.get('data', []):
            year = item.get('year')
            fw = float(item.get('fw', 0))  # m³/s
            if year not in daily_by_year:
                daily_by_year[year] = []
            daily_by_year[year].append(fw)

        for year, daily_flows in daily_by_year.items():
            flow_data.append({'year': year, 'daily_flows': daily_flows})

        print(f"  유량 데이터: {len(flow_data)}년")
    else:
        print("  [WARN] 유량 데이터 없음, 기본값 사용")

    # 기후 데이터 (스케일링용) - 간략화: 기준기간만 설정
    baseline_years = list(range(1991, 2021))

    agent = WaterScarcityProbabilityAgent()
    collected_data = {
        'water_data': water_data,
        'flow_data': flow_data,
        'climate_data': {},  # 스케일링 없이 기본값 사용
        'baseline_years': baseline_years
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_typhoon():
    """태풍 (S_tc) 테스트"""
    print("\n" + "=" * 60)
    print("8. 태풍 (Typhoon) - S_tc")
    print("=" * 60)

    # 태풍 Best Track CSV 파일 로드
    typhoon_tracks = []

    # 2015-2024년 데이터 로드
    for year in range(2015, 2025):
        csv_file = TYPHOON_DATA_DIR / f"typhoon_{year}.csv"
        if not csv_file.exists():
            continue

        with open(csv_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 헤더 라인 스킵 (#으로 시작하는 라인)
        data_lines = [l for l in lines if not l.strip().startswith('#') and l.strip()]

        for line in data_lines:
            parts = line.split()
            if len(parts) < 17:
                continue

            try:
                grade = parts[0]
                tcid = parts[1]
                yr = int(parts[2])
                lon = float(parts[6])
                lat = float(parts[7])

                # 강풍/폭풍 반경
                gale_long = float(parts[10]) if parts[10] != '-999' else 0
                gale_short = float(parts[11]) if parts[11] != '-999' else 0
                gale_dir = float(parts[12]) if parts[12] != '-999.9' else 0
                storm_long = float(parts[13]) if parts[13] != '-999' else 0
                storm_short = float(parts[14]) if parts[14] != '-999' else 0
                storm_dir = float(parts[15]) if parts[15] != '-999.9' else 0

                track_point = {
                    'lon': lon,
                    'lat': lat,
                    'grade': grade,
                    'gale_long': gale_long,
                    'gale_short': gale_short,
                    'gale_dir': gale_dir,
                    'storm_long': storm_long,
                    'storm_short': storm_short,
                    'storm_dir': storm_dir
                }

                # 같은 연도/태풍 ID로 그룹핑
                found = False
                for storm in typhoon_tracks:
                    if storm['year'] == yr and storm['storm_id'] == tcid:
                        storm['tracks'].append(track_point)
                        found = True
                        break

                if not found:
                    typhoon_tracks.append({
                        'year': yr,
                        'storm_id': tcid,
                        'tracks': [track_point]
                    })

            except (ValueError, IndexError):
                continue

    if not typhoon_tracks:
        print("  [WARN] 태풍 데이터 없음")
        return None

    print(f"  태풍 데이터: {len(typhoon_tracks)}개 태풍 (2015-2024)")

    agent = TyphoonProbabilityAgent()
    collected_data = {
        'typhoon_data': {
            'typhoon_tracks': typhoon_tracks,
            'site_location': {'lon': DAEJEON_LON, 'lat': DAEJEON_LAT}
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def test_coastal_flood():
    """해수면 상승 (ZOS) 테스트"""
    print("\n" + "=" * 60)
    print("9. 해수면 상승 (Coastal Flood / Sea Level Rise) - ZOS")
    print("=" * 60)

    if not CMIP6_ZOS_FILE.exists():
        print(f"  [WARN] 파일 없음: {CMIP6_ZOS_FILE}")
        return None

    # CMIP6 ZOS 데이터 로드
    ds = nc.Dataset(CMIP6_ZOS_FILE)
    lat_2d = ds.variables['latitude'][:]
    lon_2d = ds.variables['longitude'][:]
    zos_data = ds.variables['zos'][:]  # (time, j, i), m 단위
    time_data = ds.variables['time'][:]

    # 2D 격자에서 가장 가까운 점 찾기
    # 대전은 내륙이므로 가장 가까운 해안 격자점 사용
    # 서해안 쪽 격자점 선택 (예: 인천/서산 해역)
    target_lat = 36.35  # 대전과 비슷한 위도
    target_lon = 126.5  # 서해안

    # 2D 격자에서 최근접점 찾기
    lat_diff = np.abs(lat_2d - target_lat)
    lon_diff = np.abs(lon_2d - target_lon)
    dist = np.sqrt(lat_diff**2 + lon_diff**2)
    min_idx = np.unravel_index(np.argmin(dist), dist.shape)
    j_idx, i_idx = min_idx

    print(f"  가장 가까운 격자점: lat={lat_2d[j_idx, i_idx]:.2f}, lon={lon_2d[j_idx, i_idx]:.2f}")

    # 해당 격자점의 ZOS 시계열 추출
    zos_timeseries = zos_data[:, j_idx, i_idx]  # (time,), m 단위

    # masked array 처리
    if hasattr(zos_timeseries, 'data'):
        zos_timeseries = zos_timeseries.data

    ds.close()

    # 월별 데이터를 연도별로 그룹핑 (2015-2100)
    # 1032개월 = 86년 (2015.01 ~ 2100.12)
    n_months = len(zos_timeseries)
    n_years = n_months // 12

    zos_yearly_data = []
    for year_idx in range(n_years):
        year = 2015 + year_idx
        start_month = year_idx * 12
        end_month = start_month + 12
        monthly_values = zos_timeseries[start_month:end_month]

        # m → cm 변환 (Agent에서 cm으로 기대)
        monthly_values_cm = [v * 100 for v in monthly_values]

        zos_yearly_data.append({
            'year': year,
            'zos_values': monthly_values_cm  # cm 단위
        })

    print(f"  데이터: {len(zos_yearly_data)}년 (2015-2100)")
    all_zos_cm = [v for d in zos_yearly_data for v in d['zos_values']]
    print(f"  ZOS 범위: {min(all_zos_cm):.2f} ~ {max(all_zos_cm):.2f} cm")

    # 해안 지역 시나리오: 지반고도 설정
    # 실제 해안가 저지대 (예: 부산, 인천 항만 지역)는 지반고도가 1-3m 정도
    # 테스트를 위해 지반고도를 ZOS와 비슷하게 설정하여 침수 발생하도록 함
    ground_level = 0.5  # 0.5m (해안 저지대)

    print(f"  지반고도: {ground_level}m (해안 저지대 가정)")

    agent = CoastalFloodProbabilityAgent()
    collected_data = {
        'ocean_data': {
            'zos_data': zos_yearly_data,
            'ground_level': ground_level
        }
    }

    result = agent.calculate_probability(collected_data)
    print_result(result)
    return result


def print_result(result: dict):
    """결과 출력"""
    if result.get('status') == 'failed':
        print(f"  [ERROR] {result.get('error', 'Unknown error')}")
        return

    print(f"\n  리스크 타입: {result['risk_type']}")
    print(f"  상태: {result['status']}")
    print("\n  Bin별 확률 및 손상률:")
    print("  " + "-" * 50)

    probs = result['bin_probabilities']
    drs = result['bin_base_damage_rates']
    details = result.get('calculation_details', {})
    bins_info = details.get('bins', [])

    for i, (p, dr) in enumerate(zip(probs, drs)):
        bin_range = bins_info[i]['range'] if bins_info else f"bin{i+1}"
        print(f"  bin{i+1}: P={p:.4f} ({p*100:.1f}%), DR={dr:.4f} ({dr*100:.1f}%)")
        print(f"         범위: {bin_range}")

    print("  " + "-" * 50)
    print(f"  총 기간: {details.get('total_years', 'N/A')}년/개월")


def main():
    print("=" * 60)
    print("Probability Agent 테스트")
    print("대상: 대덕 데이터센터 (대전광역시 유성구)")
    print(f"좌표: ({DAEJEON_LAT}, {DAEJEON_LON})")
    print("=" * 60)

    results = {}

    # 1. 폭염
    results['heat'] = test_high_temperature()

    # 2. 한파
    results['cold'] = test_cold_wave()

    # 3. 가뭄
    results['drought'] = test_drought()

    # 4. 내륙홍수
    results['inland_flood'] = test_inland_flood()

    # 5. 도시홍수
    results['urban_flood'] = test_urban_flood()

    # 6. 산불
    results['wildfire'] = test_wildfire()

    # 7. 물부족
    results['water_scarcity'] = test_water_scarcity()

    # 8. 태풍
    results['typhoon'] = test_typhoon()

    # 9. 해수면 상승
    results['coastal_flood'] = test_coastal_flood()

    # 결과 저장
    output_file = Path(__file__).parent / "probability_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"테스트 완료! 결과 저장: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
