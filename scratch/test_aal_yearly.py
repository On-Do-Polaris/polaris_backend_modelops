#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
연도별 AAL 계산 테스트 스크립트
SSP126 시나리오 데이터를 사용하여 9개 리스크 항목의 연도별 AAL 계산
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import netCDF4 as nc
import pandas as pd
from math import radians, cos, sin, asin, sqrt

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Probability Agents 임포트
from modelops.agents.probability_calculate.extreme_heat_probability_agent import ExtremeHeatProbabilityAgent
from modelops.agents.probability_calculate.extreme_cold_probability_agent import ExtremeColdProbabilityAgent
from modelops.agents.probability_calculate.drought_probability_agent import DroughtProbabilityAgent
from modelops.agents.probability_calculate.urban_flood_probability_agent import UrbanFloodProbabilityAgent
from modelops.agents.probability_calculate.river_flood_probability_agent import RiverFloodProbabilityAgent
from modelops.agents.probability_calculate.wildfire_probability_agent import WildfireProbabilityAgent
from modelops.agents.probability_calculate.sea_level_rise_probability_agent import SeaLevelRiseProbabilityAgent
from modelops.agents.probability_calculate.typhoon_probability_agent import TyphoonProbabilityAgent
from modelops.agents.probability_calculate.water_stress_probability_agent import WaterStressProbabilityAgent


class YearlyAALDataLoader:
    """연도별 AAL 계산을 위한 데이터 로더"""

    def __init__(self, scratch_dir: str):
        self.scratch_dir = Path(scratch_dir)
        self.kma_dir = self.scratch_dir / "kma" / "ssp126"
        self.typhoon_dir = self.scratch_dir / "typhoon"

        # Aqueduct 물 스트레스 데이터 로드 (한 번만)
        self.aqueduct_data = None
        self._load_aqueduct_data()

    def _load_aqueduct_data(self):
        """Aqueduct 물 스트레스 데이터 로드"""
        try:
            aqueduct_file = self.scratch_dir / "Aqueduct40_rankings_download_Y2023M07D05.xlsx"
            # province_baseline 시트 사용
            df = pd.read_excel(aqueduct_file, sheet_name='province_baseline')
            self.aqueduct_data = df
            logger.info(f"Aqueduct 데이터 로드 성공: {len(df)} 행")
        except Exception as e:
            logger.warning(f"Aqueduct 데이터 로드 실패: {e}")
            self.aqueduct_data = None

    def get_water_stress_from_aqueduct(self, lat: float, lon: float) -> float:
        """위도/경도에서 가장 가까운 지역의 물 스트레스 지수 반환"""
        if self.aqueduct_data is None:
            return 1.5  # 기본값 (중간 수준)

        try:
            # BWS (Baseline Water Stress) 데이터만 필터링
            bws_data = self.aqueduct_data[self.aqueduct_data['indicator_name'] == 'bws'].copy()

            if len(bws_data) == 0:
                logger.warning("BWS 데이터를 찾을 수 없습니다.")
                return 1.5

            # 한국 데이터만 필터링
            korea_data = bws_data[bws_data['name_0'].str.contains('Korea', case=False, na=False)]

            if len(korea_data) == 0:
                logger.warning("한국 BWS 데이터를 찾을 수 없습니다. 전체 데이터 사용.")
                korea_data = bws_data

            # score 컬럼 사용 (물 스트레스 점수 0-5)
            # 한국의 평균 물 스트레스 사용 (위경도 매칭 없이)
            avg_score = korea_data['score'].mean()

            logger.info(f"물 스트레스 지수 (BWS): {avg_score:.2f} (한국 평균)")
            return float(avg_score)

        except Exception as e:
            logger.warning(f"물 스트레스 계산 실패: {e}")
            return 1.5

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 지점 간의 거리 계산 (km)"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    def load_typhoon_data(self, year: int, lat: float, lon: float) -> list:
        """특정 연도의 태풍 데이터 로드"""
        typhoons = []

        # 역사적 데이터 (2015-2024)
        for hist_year in range(2015, 2025):
            typhoon_file = self.typhoon_dir / f"typhoon_{hist_year}.csv"

            if not typhoon_file.exists():
                continue

            try:
                # # 주석 줄 건너뛰고 읽기
                with open(typhoon_file, 'r', encoding='utf-8') as f:
                    lines = [line for line in f if not line.startswith('#')]

                from io import StringIO
                df = pd.read_csv(StringIO(''.join(lines)), delim_whitespace=True)

                # 컬럼 정리
                if len(df.columns) >= 17:
                    df.columns = ['GRADE', 'TCID', 'YEAR', 'MONTH', 'DAY', 'HOUR', 'LON', 'LAT',
                                  'MAX_WS', 'PS', 'GALE_LONG', 'GALE_SHORT', 'GALE_DIR',
                                  'STORM_LONG', 'STORM_SHORT', 'STORM_DIR', 'NAME']

                    # 각 태풍별로 그룹화
                    for tcid, group in df.groupby('TCID'):
                        typhoon_track = []

                        for _, row in group.iterrows():
                            # 에이전트가 요구하는 모든 필드 포함
                            typhoon_track.append({
                                'lat': float(row['LAT']),
                                'lon': float(row['LON']),
                                'grade': str(row['GRADE']),
                                # 강풍 반경 타원 (GALE - Beaufort scale 7-9, 34-47 knots)
                                'gale_long': float(row['GALE_LONG']) if row['GALE_LONG'] > 0 else 0.0,
                                'gale_short': float(row['GALE_SHORT']) if row['GALE_SHORT'] > 0 else 0.0,
                                'gale_dir': float(row['GALE_DIR']) if row['GALE_DIR'] >= 0 else 0.0,
                                # 폭풍 반경 타원 (STORM - Beaufort scale 10+, 48+ knots)
                                'storm_long': float(row['STORM_LONG']) if row['STORM_LONG'] > 0 else 0.0,
                                'storm_short': float(row['STORM_SHORT']) if row['STORM_SHORT'] > 0 else 0.0,
                                'storm_dir': float(row['STORM_DIR']) if row['STORM_DIR'] >= 0 else 0.0,
                            })

                        if typhoon_track:
                            typhoons.append({
                                'storm_id': str(tcid),  # 'id' → 'storm_id'
                                'name': str(group.iloc[0]['NAME']) if 'NAME' in group.columns else 'UNKNOWN',
                                'year': hist_year,
                                'tracks': typhoon_track  # 'track' → 'tracks' (복수형)
                            })

                logger.info(f"태풍 데이터 로드: {hist_year}년, {len(df.groupby('TCID'))}개 태풍")

            except Exception as e:
                logger.warning(f"태풍 데이터 ({hist_year}) 로드 실패: {e}")

        logger.info(f"✓ 총 {len(typhoons)}개 태풍 로드됨 (2015-2024)")
        return typhoons

    def load_sea_level_rise(self, lat: float, lon: float, year: int) -> dict:
        """해수면 상승 데이터 로드"""
        zos_file = self.scratch_dir / "zos_Omon_ACCESS-CM2_ssp126_r1i1p1f1_gn_20150116-21001216.nc"

        if not zos_file.exists():
            logger.warning(f"ZOS 파일을 찾을 수 없습니다: {zos_file}")
            return {'sea_level_rise_m': 0.0, 'coastal_surge_m': 0.0}

        try:
            with nc.Dataset(zos_file, 'r') as dataset:
                logger.info(f"ZOS 데이터셋 변수: {list(dataset.variables.keys())}")
                logger.info(f"ZOS 데이터셋 차원: {list(dataset.dimensions.keys())}")

                # 좌표 찾기 (2D 배열)
                lats = dataset.variables['latitude'][:]
                lons = dataset.variables['longitude'][:]

                logger.info(f"좌표 형태: lats.shape={lats.shape}, lons.shape={lons.shape}")
                logger.info(f"좌표 범위: lat=[{lats.min():.2f}, {lats.max():.2f}], lon=[{lons.min():.2f}, {lons.max():.2f}]")

                # 2D 좌표에서 가장 가까운 그리드 찾기
                if lats.ndim == 2:
                    # Calculate distance for each grid point
                    dist = np.sqrt((lats - lat)**2 + (lons - lon)**2)
                    idx = np.unravel_index(np.argmin(dist), lats.shape)
                    lat_idx, lon_idx = idx
                    logger.info(f"2D 좌표 인덱스: lat_idx={lat_idx}, lon_idx={lon_idx}")
                    logger.info(f"선택된 좌표: lat={lats[lat_idx, lon_idx]:.2f}, lon={lons[lat_idx, lon_idx]:.2f}")
                else:
                    # 1D 좌표
                    lat_idx = np.argmin(np.abs(lats - lat))
                    lon_idx = np.argmin(np.abs(lons - lon))
                    logger.info(f"1D 좌표 인덱스: lat_idx={lat_idx}, lon_idx={lon_idx}")

                # 시간 인덱스 계산 (2015년 1월부터 월별 데이터)
                # 2015 = 0, 2021 = 72 (6년 * 12개월)
                if year < 2015:
                    year = 2015
                elif year > 2100:
                    year = 2100

                month_idx = (year - 2015) * 12
                time_len = len(dataset.variables['time'])

                logger.info(f"시간 인덱스: month_idx={month_idx}, time_len={time_len}")

                if month_idx >= time_len:
                    month_idx = time_len - 1
                    logger.warning(f"시간 인덱스 범위 초과, 마지막 인덱스 사용: {month_idx}")

                # ZOS 데이터 형태 확인
                zos_var = dataset.variables['zos']
                logger.info(f"ZOS 변수 형태: {zos_var.shape}")

                # ZOS (Sea Surface Height) 데이터 추출
                if lats.ndim == 2:
                    # 2D 좌표 (time, j, i)
                    zos = zos_var[month_idx, lat_idx, lon_idx]
                else:
                    # 1D 좌표
                    zos = zos_var[month_idx, lat_idx, lon_idx]

                sea_level_rise = float(zos)

                logger.info(f"✓ 해수면 상승 데이터: {year}년, {sea_level_rise:.3f}m")

                return {
                    'sea_level_rise_m': sea_level_rise,
                    'coastal_surge_m': sea_level_rise * 0.2  # 폭풍해일은 해수면 상승의 20%로 근사
                }

        except Exception as e:
            logger.error(f"✗ 해수면 상승 데이터 로드 실패: {e}", exc_info=True)
            return {'sea_level_rise_m': 0.0, 'coastal_surge_m': 0.0}

    def load_netcdf_multi_year(self, filename: str, variable_name: str, lat: float, lon: float, start_year: int, end_year: int) -> list:
        """
        NetCDF 파일에서 여러 연도의 데이터 추출

        Args:
            filename: NetCDF 파일명
            variable_name: 변수명
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (2021-2100)
            end_year: 종료 연도 (2021-2100)

        Returns:
            해당 기간의 데이터 값 리스트
        """
        filepath = self.kma_dir / filename

        if not filepath.exists():
            logger.warning(f"파일을 찾을 수 없습니다: {filepath}")
            return []

        try:
            with nc.Dataset(filepath, 'r') as dataset:
                # 좌표 찾기
                if 'latitude' in dataset.variables:
                    lats = dataset.variables['latitude'][:]
                    lons = dataset.variables['longitude'][:]
                elif 'lat' in dataset.variables:
                    lats = dataset.variables['lat'][:]
                    lons = dataset.variables['lon'][:]
                else:
                    logger.error(f"좌표 변수를 찾을 수 없습니다: {list(dataset.variables.keys())}")
                    return []

                lat_idx = np.argmin(np.abs(lats - lat))
                lon_idx = np.argmin(np.abs(lons - lon))

                # 연도 인덱스 범위
                start_idx = start_year - 2021
                end_idx = end_year - 2021 + 1

                if 'time' in dataset.variables:
                    times = dataset.variables['time'][:]

                    if start_idx < 0:
                        start_idx = 0
                    if end_idx > len(times):
                        end_idx = len(times)
                else:
                    logger.error(f"time 변수를 찾을 수 없습니다.")
                    return []

                # 데이터 추출
                if variable_name in dataset.variables:
                    values = []
                    for year_idx in range(start_idx, end_idx):
                        value = float(dataset.variables[variable_name][year_idx, lat_idx, lon_idx])
                        values.append(value)
                    return values
                else:
                    logger.warning(f"변수 '{variable_name}'를 찾을 수 없습니다.")
                    return []

        except Exception as e:
            logger.error(f"NetCDF 로드 실패 ({filename}, {start_year}-{end_year}): {e}")
            return []

    def load_netcdf_single_year(self, filename: str, variable_name: str, lat: float, lon: float, year: int) -> float:
        """
        NetCDF 파일에서 특정 연도의 데이터 추출

        Args:
            filename: NetCDF 파일명
            variable_name: 변수명
            lat: 위도
            lon: 경도
            year: 연도 (2021-2100)

        Returns:
            해당 연도의 데이터 값
        """
        filepath = self.kma_dir / filename

        if not filepath.exists():
            logger.warning(f"파일을 찾을 수 없습니다: {filepath}")
            return 0.0

        try:
            with nc.Dataset(filepath, 'r') as dataset:
                # 좌표 찾기
                if 'latitude' in dataset.variables:
                    lats = dataset.variables['latitude'][:]
                    lons = dataset.variables['longitude'][:]
                elif 'lat' in dataset.variables:
                    lats = dataset.variables['lat'][:]
                    lons = dataset.variables['lon'][:]
                else:
                    logger.error(f"좌표 변수를 찾을 수 없습니다: {list(dataset.variables.keys())}")
                    return 0.0

                lat_idx = np.argmin(np.abs(lats - lat))
                lon_idx = np.argmin(np.abs(lons - lon))

                # 연도 인덱스 찾기
                if 'time' in dataset.variables:
                    times = dataset.variables['time'][:]
                    # 2021년이 인덱스 0이라고 가정
                    year_idx = year - 2021

                    if year_idx < 0 or year_idx >= len(times):
                        logger.warning(f"연도 {year}이 범위를 벗어났습니다.")
                        return 0.0
                else:
                    logger.error(f"time 변수를 찾을 수 없습니다.")
                    return 0.0

                # 데이터 추출
                if variable_name in dataset.variables:
                    value = float(dataset.variables[variable_name][year_idx, lat_idx, lon_idx])
                    return value
                else:
                    logger.warning(f"변수 '{variable_name}'를 찾을 수 없습니다.")
                    return 0.0

        except Exception as e:
            logger.error(f"NetCDF 로드 실패 ({filename}, {year}): {e}")
            return 0.0

    def load_netcdf_monthly_multi_year(self, filename: str, variable_name: str, lat: float, lon: float, start_year: int, end_year: int) -> list:
        """
        월별 NetCDF 파일에서 여러 연도의 데이터 추출 (flat list)

        Args:
            filename: NetCDF 파일명
            variable_name: 변수명
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (2021-2100)
            end_year: 종료 연도 (2021-2100)

        Returns:
            전체 기간의 월별 데이터 flat list
        """
        filepath = self.kma_dir / filename

        if not filepath.exists():
            logger.warning(f"파일을 찾을 수 없습니다: {filepath}")
            return []

        try:
            with nc.Dataset(filepath, 'r') as dataset:
                # 좌표 찾기
                if 'latitude' in dataset.variables:
                    lats = dataset.variables['latitude'][:]
                    lons = dataset.variables['longitude'][:]
                elif 'lat' in dataset.variables:
                    lats = dataset.variables['lat'][:]
                    lons = dataset.variables['lon'][:]
                else:
                    logger.error(f"좌표 변수를 찾을 수 없습니다: {list(dataset.variables.keys())}")
                    return []

                lat_idx = np.argmin(np.abs(lats - lat))
                lon_idx = np.argmin(np.abs(lons - lon))

                # 월별 인덱스 계산 (2021년 1월 = 인덱스 0)
                start_month_idx = (start_year - 2021) * 12
                end_month_idx = (end_year - 2021 + 1) * 12

                # 데이터 추출
                if variable_name in dataset.variables:
                    data = dataset.variables[variable_name]
                    monthly_values = []

                    for month_idx in range(start_month_idx, end_month_idx):
                        if month_idx < len(data):
                            value = float(data[month_idx, lat_idx, lon_idx])
                            monthly_values.append(value)
                        else:
                            break

                    return monthly_values
                else:
                    logger.warning(f"변수 '{variable_name}'를 찾을 수 없습니다.")
                    return []

        except Exception as e:
            logger.error(f"NetCDF 월별 로드 실패 ({filename}, {start_year}-{end_year}): {e}")
            return []

    def load_netcdf_monthly_single_year(self, filename: str, variable_name: str, lat: float, lon: float, year: int) -> list:
        """
        월별 NetCDF 파일에서 특정 연도의 12개월 데이터 추출

        Args:
            filename: NetCDF 파일명
            variable_name: 변수명
            lat: 위도
            lon: 경도
            year: 연도 (2021-2100)

        Returns:
            12개월 데이터 리스트
        """
        filepath = self.kma_dir / filename

        if not filepath.exists():
            logger.warning(f"파일을 찾을 수 없습니다: {filepath}")
            return [0.0] * 12

        try:
            with nc.Dataset(filepath, 'r') as dataset:
                # 좌표 찾기
                if 'latitude' in dataset.variables:
                    lats = dataset.variables['latitude'][:]
                    lons = dataset.variables['longitude'][:]
                elif 'lat' in dataset.variables:
                    lats = dataset.variables['lat'][:]
                    lons = dataset.variables['lon'][:]
                else:
                    logger.error(f"좌표 변수를 찾을 수 없습니다: {list(dataset.variables.keys())}")
                    return [0.0] * 12

                lat_idx = np.argmin(np.abs(lats - lat))
                lon_idx = np.argmin(np.abs(lons - lon))

                # 월별 인덱스 계산 (2021년 1월 = 인덱스 0)
                year_offset = (year - 2021) * 12
                month_indices = range(year_offset, year_offset + 12)

                # 데이터 추출
                if variable_name in dataset.variables:
                    data = dataset.variables[variable_name]
                    monthly_values = []

                    for month_idx in month_indices:
                        if month_idx < len(data):
                            value = float(data[month_idx, lat_idx, lon_idx])
                            monthly_values.append(value)
                        else:
                            monthly_values.append(0.0)

                    return monthly_values
                else:
                    logger.warning(f"변수 '{variable_name}'를 찾을 수 없습니다.")
                    return [0.0] * 12

        except Exception as e:
            logger.error(f"NetCDF 월별 로드 실패 ({filename}, {year}): {e}")
            return [0.0] * 12

    def get_baseline_data(self, filename: str, variable_name: str, lat: float, lon: float, start_year: int = 1991, end_year: int = 2020) -> np.ndarray:
        """기준기간 데이터 로드 (현재는 2021-2050 사용)"""
        filepath = self.kma_dir / filename

        if not filepath.exists():
            return np.array([])

        try:
            with nc.Dataset(filepath, 'r') as dataset:
                if 'latitude' in dataset.variables:
                    lats = dataset.variables['latitude'][:]
                    lons = dataset.variables['longitude'][:]
                elif 'lat' in dataset.variables:
                    lats = dataset.variables['lat'][:]
                    lons = dataset.variables['lon'][:]
                else:
                    return np.array([])

                lat_idx = np.argmin(np.abs(lats - lat))
                lon_idx = np.argmin(np.abs(lons - lon))

                # 기준기간: 2021-2050 (처음 30년)
                if variable_name in dataset.variables:
                    data = dataset.variables[variable_name][:30, lat_idx, lon_idx]
                    return data
                else:
                    return np.array([])

        except Exception as e:
            logger.error(f"기준기간 데이터 로드 실패: {e}")
            return np.array([])


def calculate_yearly_aal(agent_class, data_loader: YearlyAALDataLoader, lat: float, lon: float,
                         year: int, risk_name: str, data_getter_func) -> dict:
    """
    특정 연도의 AAL 계산

    Args:
        agent_class: Probability Agent 클래스
        data_loader: 데이터 로더
        lat: 위도
        lon: 경도
        year: 계산할 연도
        risk_name: 리스크 이름
        data_getter_func: 데이터 수집 함수

    Returns:
        AAL 계산 결과 딕셔너리
    """
    try:
        agent = agent_class()
        collected_data = data_getter_func(data_loader, lat, lon, year)

        result = agent.calculate_probability(collected_data)

        if result['status'] == 'completed':
            return {
                'year': year,
                'risk': risk_name,
                'aal': result['aal'],
                'aal_percent': result['aal'] * 100,
                'method': result['calculation_details'].get('method', 'unknown'),
                'status': 'success'
            }
        else:
            return {
                'year': year,
                'risk': risk_name,
                'aal': 0.0,
                'aal_percent': 0.0,
                'error': result.get('error', 'Unknown error'),
                'status': 'failed'
            }

    except Exception as e:
        logger.error(f"{risk_name} {year}년 계산 중 오류: {e}")
        return {
            'year': year,
            'risk': risk_name,
            'aal': 0.0,
            'aal_percent': 0.0,
            'error': str(e),
            'status': 'error'
        }


# 각 리스크별 데이터 수집 함수
def get_heat_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """극심한 고온 데이터 - 40년치 데이터 입력"""
    # 현재 연도 기준 앞뒤 20년씩 총 40년 데이터 (KDE 확률 계산용, MIN_SAMPLES=30)
    start_year = max(2021, year - 20)
    end_year = min(2100, year + 20)

    wsdi_values = loader.load_netcdf_multi_year('SSP126_WSDI_gridraw_yearly_2021-2100.nc', 'WSDI', lat, lon, start_year, end_year)
    baseline_wsdi = loader.get_baseline_data('SSP126_WSDI_gridraw_yearly_2021-2100.nc', 'WSDI', lat, lon)

    return {
        'climate_data': {'wsdi': wsdi_values},
        'baseline_wsdi': baseline_wsdi.tolist() if len(baseline_wsdi) > 0 else []
    }


def get_cold_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """극심한 한파 데이터 - 40년치 데이터 입력"""
    start_year = max(2021, year - 20)
    end_year = min(2100, year + 20)

    csdi_values = loader.load_netcdf_multi_year('SSP126_CSDI_gridraw_yearly_2021-2100.nc', 'CSDI', lat, lon, start_year, end_year)
    baseline_csdi = loader.get_baseline_data('SSP126_CSDI_gridraw_yearly_2021-2100.nc', 'CSDI', lat, lon)

    return {
        'climate_data': {'csdi': csdi_values},
        'baseline_csdi': baseline_csdi.tolist() if len(baseline_csdi) > 0 else []
    }


def get_drought_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """가뭄 데이터 - 40년치 월별 데이터 입력"""
    start_year = max(2021, year - 20)
    end_year = min(2100, year + 20)

    spei12_monthly = loader.load_netcdf_monthly_multi_year('SSP126_SPEI12_gridraw_monthly_2021-2100.nc', 'SPEI12', lat, lon, start_year, end_year)

    return {
        'climate_data': {'spei12': spei12_monthly}
    }


def get_urban_flood_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """도시홍수 데이터 - 40년치 데이터 입력"""
    start_year = max(2021, year - 20)
    end_year = min(2100, year + 20)

    rain80_values = loader.load_netcdf_multi_year('SSP126_RAIN80_gridraw_yearly_2021-2100.nc', 'RAIN80', lat, lon, start_year, end_year)

    return {
        'climate_data': {'rain80': rain80_values}
    }


def get_river_flood_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """내륙홍수 데이터 - 40년치 데이터 입력"""
    start_year = max(2021, year - 20)
    end_year = min(2100, year + 20)

    rx1day_values = loader.load_netcdf_multi_year('SSP126_RX1DAY_gridraw_yearly_2021-2100.nc', 'RX1DAY', lat, lon, start_year, end_year)
    baseline_rx1day = loader.get_baseline_data('SSP126_RX1DAY_gridraw_yearly_2021-2100.nc', 'RX1DAY', lat, lon)

    return {
        'climate_data': {
            'rx1day': rx1day_values,
            'baseline_rx1day': baseline_rx1day.tolist() if len(baseline_rx1day) > 0 else []
        }
    }


def get_wildfire_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """산불 데이터 - 40년치 월별 데이터 입력"""
    start_year = max(2021, year - 20)
    end_year = min(2100, year + 20)

    ta_monthly = loader.load_netcdf_monthly_multi_year('AR6_SSP126_5ENSMN_skorea_TA_gridraw_monthly_2021_2100.nc', 'TA', lat, lon, start_year, end_year)
    rhm_monthly = loader.load_netcdf_monthly_multi_year('AR6_SSP126_5ENSMN_skorea_RHM_gridraw_monthly_2021_2100.nc', 'RHM', lat, lon, start_year, end_year)
    ws_monthly = loader.load_netcdf_monthly_multi_year('AR6_SSP126_5ENSMN_skorea_WS_gridraw_monthly_2021_2100.nc', 'WS', lat, lon, start_year, end_year)
    rn_monthly = loader.load_netcdf_monthly_multi_year('AR6_SSP126_5ENSMN_skorea_RN_gridraw_monthly_2021_2100.nc', 'RN', lat, lon, start_year, end_year)

    return {
        'climate_data': {
            'ta': ta_monthly,
            'rhm': rhm_monthly,
            'ws': ws_monthly,
            'rn': rn_monthly
        }
    }


def get_slr_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """해수면 상승 데이터"""
    slr_data = loader.load_sea_level_rise(lat, lon, year)

    return {
        'climate_data': slr_data,
        'extra_data': {
            'distance_to_coast_m': 10000.0,  # DEM 파일에서 추출 필요 (현재는 더미)
            'elevation_m': 50.0  # DEM 파일에서 추출 필요 (현재는 더미)
        }
    }


def get_typhoon_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """태풍 데이터"""
    # 역사적 태풍 데이터 사용 (2015-2024)
    typhoons = loader.load_typhoon_data(year, lat, lon)

    return {
        'typhoon_data': {
            'typhoon_tracks': typhoons,  # 'typhoons' → 'typhoon_tracks'
            'site_location': {'lon': lon, 'lat': lat}  # 에이전트가 요구하는 필드
        }
    }


def get_water_stress_data(loader: YearlyAALDataLoader, lat: float, lon: float, year: int) -> dict:
    """물 스트레스 데이터"""
    # Aqueduct에서 물 스트레스 지수 가져오기
    water_stress_index = loader.get_water_stress_from_aqueduct(lat, lon)

    return {
        'climate_data': {
            'annual_rainfall_mm': 1200.0,  # KMA 데이터에서 가져올 수 있음
            'consecutive_dry_days': 15
        },
        'wamis_data': {
            'water_stress_index': water_stress_index
        }
    }


def main():
    """메인 테스트 실행"""
    logger.info("="*80)
    logger.info("연도별 AAL 계산 테스트 (SSP126 시나리오)")
    logger.info("="*80)

    # 테스트 설정
    scratch_dir = Path(__file__).parent
    lat = 36.35
    lon = 127.38
    # KDE 확률 계산을 위해 중간 시점 사용 (앞뒤로 최소 20년씩 확보)
    test_years = [2050, 2055, 2060, 2065, 2070]

    logger.info(f"테스트 위치: 위도 {lat}, 경도 {lon}")
    logger.info(f"테스트 연도: {test_years}")
    logger.info(f"데이터 경로: {scratch_dir / 'kma' / 'ssp126'}\n")

    # 데이터 로더 초기화
    data_loader = YearlyAALDataLoader(str(scratch_dir))

    # 리스크 설정 (agent_class, data_getter, display_name)
    risk_configs = [
        (ExtremeHeatProbabilityAgent, get_heat_data, '극심한 고온'),
        (ExtremeColdProbabilityAgent, get_cold_data, '극심한 한파'),
        (DroughtProbabilityAgent, get_drought_data, '가뭄'),
        (UrbanFloodProbabilityAgent, get_urban_flood_data, '도시홍수'),
        (RiverFloodProbabilityAgent, get_river_flood_data, '내륙홍수'),
        (WildfireProbabilityAgent, get_wildfire_data, '산불'),
        (SeaLevelRiseProbabilityAgent, get_slr_data, '해수면상승'),
        (TyphoonProbabilityAgent, get_typhoon_data, '태풍'),
        (WaterStressProbabilityAgent, get_water_stress_data, '물스트레스'),
    ]

    # 연도별 계산
    all_results = []

    for year in test_years:
        logger.info("="*80)
        logger.info(f"{year}년 AAL 계산")
        logger.info("="*80)

        year_results = []

        for agent_class, data_getter, risk_name in risk_configs:
            result = calculate_yearly_aal(
                agent_class, data_loader, lat, lon, year, risk_name, data_getter
            )
            year_results.append(result)

            if result['status'] == 'success':
                logger.info(f"✓ {risk_name:15s}: AAL = {result['aal_percent']:7.4f}% ({result['method']})")
            else:
                logger.info(f"✗ {risk_name:15s}: 계산 실패")

        # 연도별 총 AAL
        year_total_aal = sum(r['aal_percent'] for r in year_results if r['status'] == 'success')
        logger.info(f"\n{year}년 총 AAL: {year_total_aal:.4f}%\n")

        all_results.extend(year_results)

    # 최종 요약 - 연도별 리스크별 AAL
    logger.info("\n" + "="*80)
    logger.info("연도별 리스크별 AAL (%)")
    logger.info("="*80)

    # 헤더 출력
    header = f"{'리스크':<20s}"
    for year in test_years:
        header += f"{year}년    "
    logger.info(header)
    logger.info("-" * 80)

    # 각 리스크별로 연도별 AAL 출력
    for agent_class, data_getter, risk_name in risk_configs:
        row = f"{risk_name:<20s}"
        for year in test_years:
            year_risk_data = [r for r in all_results if r['year'] == year and r['risk'] == risk_name]
            if year_risk_data and year_risk_data[0]['status'] == 'success':
                aal = year_risk_data[0]['aal_percent']
                row += f"{aal:7.4f}   "
            else:
                row += f"{'N/A':>7s}   "
        logger.info(row)

    # 연도별 총합
    logger.info("-" * 80)
    row = f"{'총 AAL':<20s}"
    for year in test_years:
        year_data = [r for r in all_results if r['year'] == year and r['status'] == 'success']
        total = sum(r['aal_percent'] for r in year_data)
        row += f"{total:7.4f}   "
    logger.info(row)

    logger.info("\n" + "="*80)
    logger.info("연도별 AAL 계산 테스트 완료")
    logger.info("="*80)


if __name__ == '__main__':
    main()
