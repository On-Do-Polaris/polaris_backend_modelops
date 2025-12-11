#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Climate Data Loader
KMA SSP 시나리오 기후 데이터 로드
"""

import os
import warnings
from typing import Dict, Tuple, Optional
import numpy as np

# NetCDF 파일 처리를 위한 라이브러리
try:
    import netCDF4 as nc
    NETCDF_AVAILABLE = True
except ImportError:
    NETCDF_AVAILABLE = False
    warnings.warn("netCDF4 not available. Install with: pip install netCDF4")


class ClimateDataLoader:
    """
    KMA SSP 시나리오 기후 데이터 로더

    데이터 경로: Physical_RISK_calculate/data/KMA/gridraw/SSP245/yearly/
    파일 형식: NetCDF (.nc)
    시나리오: SSP126, SSP245, SSP370, SSP585
    기간: 2021-2100
    """

    def __init__(self, base_dir: str = None, scenario: str = "SSP245"):
        """
        Args:
            base_dir: 데이터 기본 경로
            scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
        """
        if base_dir is None:
            # 현재 파일(modelops/data_loaders) 기준, 프로젝트 루트로 이동 후 데이터 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, '..', '..')
            base_dir = os.path.join(project_root, 'physical_risk_module_core_merge', 'Physical_RISK_calculate', 'data')

        self.base_dir = base_dir
        self.scenario = scenario
        self.kma_dir = os.path.join(self.base_dir, 'KMA', 'gridraw', scenario, 'yearly')
        self.kma_monthly_dir = os.path.join(self.base_dir, 'KMA', 'gridraw', scenario, 'monthly')
        self.slr_dir = os.path.join(self.base_dir, 'sea_level_rise')

        # 캐시: 한 번 로드한 데이터는 메모리에 저장
        self._cache = {}

        if not NETCDF_AVAILABLE:
            print("⚠️ [경고] netCDF4 라이브러리가 없습니다. pip install netCDF4")

    def get_extreme_heat_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
        """
        극심한 고온 데이터 추출

        Args:
            lat: 위도
            lon: 경도
            year: 분석 연도 (2021-2100)

        Returns:
            {
                'annual_max_temp_celsius': float,  # TXx: 연간 최고기온
                'heatwave_days_per_year': int,      # SU25: 극심한 고온일수 (일최고기온 >= 25°C)
                'tropical_nights': int,             # TR25: 열대야일수 (일최저기온 >= 25°C)
                'heat_wave_duration': float,        # WSDI: 극심한 고온 지속 일수
                'data_source': str
            }
        """
        try:
            # TXx: 연간 최고기온
            txx = self._extract_value('TXx', lat, lon, year)

            # SU25: 극심한 고온일수
            su25 = self._extract_value('SU25', lat, lon, year)

            # TR25: 열대야일수
            tr25 = self._extract_value('TR25', lat, lon, year)

            # WSDIx: 극심한 고온 지속일수
            wsdix = self._extract_value('WSDIx', lat, lon, year)

            return {
                'annual_max_temp_celsius': float(txx) if txx is not None else 38.5,
                'heatwave_days_per_year': int(su25) if su25 is not None else 25,
                'tropical_nights': int(tr25) if tr25 is not None else 15,
                'heat_wave_duration': float(wsdix) if wsdix is not None else 10,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'KMA_SSP_gridraw' if txx is not None else 'fallback'
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 극심한 고온 데이터 로드 실패: {e}")
            return {
                'annual_max_temp_celsius': 38.5,
                'heatwave_days_per_year': 25,
                'tropical_nights': 15,
                'heat_wave_duration': 10,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'fallback'
            }

    def get_extreme_cold_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
        """
        극심한 극심한 한파 데이터 추출

        Returns:
            {
                'annual_min_temp_celsius': float,  # TNn: 연간 최저기온
                'coldwave_days_per_year': int,     # FD0: 결빙일수 (일최저기온 < 0°C)
                'ice_days': int,                   # ID0: 얼음일수 (일최고기온 < 0°C)
                'cold_wave_duration': float,       # CSDI: 극심한 한파 지속일수
                'data_source': str
            }
        """
        try:
            # TNn: 연간 최저기온
            tnn = self._extract_value('TNn', lat, lon, year)

            # FD0: 결빙일수
            fd0 = self._extract_value('FD0', lat, lon, year)

            # ID0: 얼음일수
            id0 = self._extract_value('ID0', lat, lon, year)

            # CSDIx: 극심한 한파 지속일수
            csdix = self._extract_value('CSDIx', lat, lon, year)

            return {
                'annual_min_temp_celsius': float(tnn) if tnn is not None else -15.0,
                'coldwave_days_per_year': int(fd0) if fd0 is not None else 10,
                'ice_days': int(id0) if id0 is not None else 5,
                'cold_wave_duration': float(csdix) if csdix is not None else 8,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'KMA_SSP_gridraw' if tnn is not None else 'fallback'
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 극심한 극심한 한파 데이터 로드 실패: {e}")
            return {
                'annual_min_temp_celsius': -15.0,
                'coldwave_days_per_year': 10,
                'ice_days': 5,
                'cold_wave_duration': 8,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'fallback'
            }

    def get_drought_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
        """
        가뭄 데이터 추출

        Returns:
            {
                'spei12_index': float,              # SPEI-12: 12개월 표준화 강수증발산지수
                'annual_rainfall_mm': float,        # 연간 총 강수량
                'consecutive_dry_days': int,        # CDD: 최대 연속 무강수일수
                'rainfall_intensity': float,        # SDII: 강수일 평균 강수강도
                'data_source': str
            }
        """
        try:
            # SPEI-12: 12개월 표준화 강수증발산지수 (월별 데이터, 6월 기준)
            # SPEI는 강수량 + 증발산량을 고려하여 기후변화 시나리오에 적합
            spei12 = self._extract_monthly_value('SPEI12', lat, lon, year, month=6)

            # RN: 연간 총 강수량 (보조 데이터)
            rn = self._extract_value('RN', lat, lon, year)

            # CDD: 최대 연속 무강수일수 (보조 데이터)
            cdd = self._extract_value('CDD', lat, lon, year)

            # SDII: 강수일 평균 강수강도 (보조 데이터)
            sdii = self._extract_value('SDII', lat, lon, year)

            return {
                'spei12_index': float(spei12) if spei12 is not None else None,
                'annual_rainfall_mm': float(rn) if rn is not None else 1200.0,
                'consecutive_dry_days': int(cdd) if cdd is not None else 15,
                'rainfall_intensity': float(sdii) if sdii is not None else 10.0,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'KMA_SSP_SPEI12' if spei12 is not None else 'fallback'
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 가뭄 데이터 로드 실패: {e}")
            return {
                'spei12_index': None,
                'annual_rainfall_mm': 1200.0,
                'consecutive_dry_days': 15,
                'rainfall_intensity': 10.0,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'fallback'
            }

    def get_flood_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
        """
        홍수 데이터 추출

        Returns:
            {
                'max_1day_rainfall_mm': float,     # RX1DAY: 1일 최대 강수량
                'max_5day_rainfall_mm': float,     # RX5DAY: 5일 최대 강수량
                'heavy_rain_days': int,            # RAIN80: 강수량 80mm 이상 일수
                'extreme_rain_95p': float,         # RD95P: 95백분위 강수량
                'data_source': str
            }
        """
        try:
            # RX1DAY: 1일 최대 강수량
            rx1day = self._extract_value('RX1DAY', lat, lon, year)

            # RX5DAY: 5일 최대 강수량
            rx5day = self._extract_value('RX5DAY', lat, lon, year)

            # RAIN80: 강수량 80mm 이상 일수
            rain80 = self._extract_value('RAIN80', lat, lon, year)

            # RD95P: 95백분위 강수량
            rd95p = self._extract_value('RD95P', lat, lon, year)

            return {
                'max_1day_rainfall_mm': float(rx1day) if rx1day is not None else 250.0,
                'max_5day_rainfall_mm': float(rx5day) if rx5day is not None else 400.0,
                'heavy_rain_days': int(rain80) if rain80 is not None else 5,
                'extreme_rain_95p': float(rd95p) if rd95p is not None else 200.0,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'KMA_SSP_gridraw' if rx1day is not None else 'fallback'
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 홍수 데이터 로드 실패: {e}")
            return {
                'max_1day_rainfall_mm': 250.0,
                'max_5day_rainfall_mm': 400.0,
                'heavy_rain_days': 5,
                'extreme_rain_95p': 200.0,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'fallback'
            }

    def get_fwi_input_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
        """
        FWI 계산에 필요한 기상 데이터 추출

        Returns:
            {
                'temperature': float,      # 기온 (°C)
                'relative_humidity': float, # 상대습도 (%)
                'wind_speed': float,       # 풍속 (m/s -> km/h 변환 필요)
                'rainfall': float,         # 강수량 (mm)
                'data_source': str
            }
        """
        try:
            # AT or TA: 평균기온 (연평균)
            heat_data = self.get_extreme_heat_data(lat, lon, year)
            temp = heat_data['annual_max_temp_celsius'] - 5  # 연평균 추정

            # RHM: 상대습도 (연평균, %)
            rhm = self._extract_value('RHM', lat, lon, year)

            # WS: 풍속 (연평균, m/s)
            ws = self._extract_value('WS', lat, lon, year)

            # RN: 강수량 (연총량, mm)
            rn_yearly = self._extract_value('RN', lat, lon, year)
            rn_daily = rn_yearly / 365.0 if rn_yearly is not None else None

            return {
                'temperature': float(temp) if temp is not None else 25.0,
                'relative_humidity': float(rhm) if rhm is not None else 60.0,
                'wind_speed': float(ws) if ws is not None else 10.0,  # m/s
                'rainfall': float(rn_daily) if rn_daily is not None else 5.0,  # mm/day
                'data_source': 'KMA_SSP_gridraw' if rhm is not None else 'partial_fallback',
                'year': year,
                'note': 'WS는 m/s → km/h 변환 필요 (×3.6)'
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] FWI 입력 데이터 로드 실패: {e}")
            return {
                'temperature': 25.0,
                'relative_humidity': 60.0,
                'wind_speed': 10.0,
                'rainfall': 5.0,
                'data_source': 'fallback',
                'year': year
            }

    def _extract_value(self, variable: str, lat: float, lon: float, year: int) -> Optional[float]:
        """
        NetCDF 파일에서 특정 위치/연도의 값 추출

        Args:
            variable: 변수명 (TXx, SU25, RX1DAY 등)
            lat: 위도
            lon: 경도
            year: 연도 (2021-2100)

        Returns:
            추출된 값 또는 None
        """
        if not NETCDF_AVAILABLE:
            return None

        try:
            import gzip
            import tarfile
            import tempfile

            # NetCDF 파일 경로
            filename = f"{self.scenario}_{variable}_gridraw_yearly_2021-2100.nc"
            filepath = os.path.join(self.kma_dir, filename)

            if not os.path.exists(filepath):
                print(f"⚠️ [TCFD 경고] 파일 없음: {filename}")
                return None

            # 캐시 확인
            cache_key = f"{variable}"
            if cache_key in self._cache:
                dataset = self._cache[cache_key]
            else:
                # 파일이 gzip 압축되어 있는지 확인
                with open(filepath, 'rb') as f:
                    magic = f.read(2)
                    is_gzipped = (magic == b'\x1f\x8b')

                if is_gzipped:
                    # gzip 압축 해제
                    with gzip.open(filepath, 'rb') as gz_file:
                        decompressed_data = gz_file.read()

                    # TAR 아카이브인지 확인 (KMA 파일은 tar.gz 형식)
                    if decompressed_data[:100].find(b'ustar') != -1 or decompressed_data[:100].find(b'AR6_') != -1:
                        # TAR 아카이브에서 NetCDF 파일 추출
                        import io
                        tar_buffer = io.BytesIO(decompressed_data)
                        with tarfile.open(fileobj=tar_buffer, mode='r') as tar:
                            # TAR 내부의 .nc 파일 찾기
                            nc_member = None
                            for member in tar.getmembers():
                                if member.name.endswith('.nc'):
                                    nc_member = member
                                    break

                            if nc_member is None:
                                print(f"⚠️ [TCFD 경고] TAR 내부에 .nc 파일 없음: {filename}")
                                return None

                            # NetCDF 데이터 추출
                            nc_data = tar.extractfile(nc_member).read()
                    else:
                        # 일반 gzip 압축 NetCDF
                        nc_data = decompressed_data

                    # 임시 파일에 저장
                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
                    tmp_file.write(nc_data)
                    tmp_file.close()

                    # NetCDF 파일 열기
                    dataset = nc.Dataset(tmp_file.name, 'r')

                    # 임시 파일 경로 저장 (나중에 삭제용)
                    if not hasattr(self, '_tmp_files'):
                        self._tmp_files = []
                    self._tmp_files.append(tmp_file.name)
                else:
                    # 일반 NetCDF 파일 열기
                    dataset = nc.Dataset(filepath, 'r')

                self._cache[cache_key] = dataset

            # 좌표계: KMA 데이터는 격자 좌표
            # latitude/longitude를 격자 인덱스로 변환
            lats = dataset.variables['latitude'][:]
            lons = dataset.variables['longitude'][:]

            # 가장 가까운 격자점 찾기
            lat_idx = np.abs(lats - lat).argmin()
            lon_idx = np.abs(lons - lon).argmin()

            # 연도 인덱스 (2021-2100 → 0-79)
            year_idx = year - 2021
            if year_idx < 0 or year_idx >= 80:
                print(f"⚠️ [TCFD 경고] 연도 범위 초과: {year} (2021-2100 지원)")
                return None

            # 데이터 변수 찾기 (변수명과 정확히 일치)
            if variable in dataset.variables:
                data_var = variable
            else:
                print(f"⚠️ [TCFD 경고] 데이터 변수를 찾을 수 없음: {variable}")
                return None

            # 데이터 추출: (time, latitude, longitude)
            value = dataset.variables[data_var][year_idx, lat_idx, lon_idx]

            # Masked value 처리
            if hasattr(value, 'mask') and value.mask:
                return None

            return float(value)

        except Exception as e:
            print(f"⚠️ [TCFD 경고] {variable} 추출 실패: {e}")
            return None

    def _extract_monthly_value(self, variable: str, lat: float, lon: float,
                               year: int, month: int = 6) -> Optional[float]:
        """
        월별 NetCDF 파일에서 특정 위치/연도/월의 값 추출

        Args:
            variable: 변수명 (SPEI12, SPI12 등)
            lat: 위도
            lon: 경도
            year: 연도 (2021-2100)
            month: 월 (1-12), 기본값 6월 (중반기)

        Returns:
            추출된 값 또는 None
        """
        if not NETCDF_AVAILABLE:
            return None

        try:
            import gzip
            import tarfile
            import tempfile

            # 월별 NetCDF 파일 경로
            monthly_dir = os.path.join(self.base_dir, 'data', 'KMA', 'gridraw', self.scenario, 'monthly')
            filename = f"{self.scenario}_{variable}_gridraw_monthly_2021-2100.nc"
            filepath = os.path.join(monthly_dir, filename)

            if not os.path.exists(filepath):
                print(f"⚠️ [TCFD 경고] 월별 파일 없음: {filename}")
                return None

            # 캐시 확인
            cache_key = f"{variable}_monthly"
            if cache_key in self._cache:
                dataset = self._cache[cache_key]
            else:
                # 파일이 gzip 압축되어 있는지 확인
                with open(filepath, 'rb') as f:
                    magic = f.read(2)
                    is_gzipped = (magic == b'\x1f\x8b')

                if is_gzipped:
                    # gzip 압축 해제
                    with gzip.open(filepath, 'rb') as gz_file:
                        decompressed_data = gz_file.read()

                    # TAR 아카이브인지 확인
                    if decompressed_data[:100].find(b'ustar') != -1 or decompressed_data[:100].find(b'AR6_') != -1:
                        # TAR 아카이브에서 NetCDF 파일 추출
                        import io
                        tar_buffer = io.BytesIO(decompressed_data)
                        with tarfile.open(fileobj=tar_buffer, mode='r') as tar:
                            # TAR 내부의 .nc 파일 찾기
                            nc_member = None
                            for member in tar.getmembers():
                                if member.name.endswith('.nc'):
                                    nc_member = member
                                    break

                            if nc_member is None:
                                print(f"⚠️ [TCFD 경고] TAR 내부에 .nc 파일 없음: {filename}")
                                return None

                            # NetCDF 데이터 추출
                            nc_data = tar.extractfile(nc_member).read()
                    else:
                        # 일반 gzip 압축 NetCDF
                        nc_data = decompressed_data

                    # 임시 파일에 저장
                    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
                    tmp_file.write(nc_data)
                    tmp_file.close()

                    # NetCDF 파일 열기
                    dataset = nc.Dataset(tmp_file.name, 'r')

                    # 임시 파일 경로 저장 (나중에 삭제용)
                    if not hasattr(self, '_tmp_files'):
                        self._tmp_files = []
                    self._tmp_files.append(tmp_file.name)
                else:
                    # 일반 NetCDF 파일 열기
                    dataset = nc.Dataset(filepath, 'r')

                self._cache[cache_key] = dataset

            # 좌표계: KMA 데이터는 격자 좌표
            lats = dataset.variables['latitude'][:]
            lons = dataset.variables['longitude'][:]

            # 가장 가까운 격자점 찾기
            lat_idx = np.abs(lats - lat).argmin()
            lon_idx = np.abs(lons - lon).argmin()

            # 시간 인덱스 계산 (월별 데이터: 2021년 1월 = 0, 2021년 12월 = 11, 2022년 1월 = 12, ...)
            # time_idx = (year - 2021) * 12 + (month - 1)
            year_offset = year - 2021
            month_offset = month - 1
            time_idx = year_offset * 12 + month_offset

            # 범위 체크 (2021-2100: 80년 * 12개월 = 960개월)
            if time_idx < 0 or time_idx >= 960:
                print(f"⚠️ [TCFD 경고] 시간 인덱스 범위 초과: year={year}, month={month}")
                return None

            # 데이터 변수 찾기
            if variable in dataset.variables:
                data_var = variable
            else:
                print(f"⚠️ [TCFD 경고] 데이터 변수를 찾을 수 없음: {variable}")
                return None

            # 데이터 추출: (time, latitude, longitude)
            value = dataset.variables[data_var][time_idx, lat_idx, lon_idx]

            # Masked value 처리
            if hasattr(value, 'mask') and value.mask:
                return None

            return float(value)

        except Exception as e:
            print(f"⚠️ [TCFD 경고] {variable} 월별 데이터 추출 실패: {e}")
            return None

    def get_sea_level_rise_data(self, lat: float, lon: float, year: int = 2050) -> Dict:
        """
        해수면 상승 데이터 추출

        Args:
            lat: 위도
            lon: 경도
            year: 분석 연도 (2015-2100)

        Returns:
            {
                'slr_m': float,              # 해수면 상승량 (m)
                'slr_cm': float,             # 해수면 상승량 (cm)
                'baseline_year': int,        # 기준 연도 (2015)
                'target_year': int,          # 목표 연도
                'slr_rate_cm_per_year': float,  # 연간 상승률 (cm/년)
                'data_source': str
            }
        """
        # 해수면 상승 데이터 경로
        slr_dir = os.path.join(self.base_dir, 'sea_level_rise')

        # 시나리오명 변환 (SSP585 → ssp5_8_5)
        scenario_map = {
            'SSP126': 'ssp1_2_6',
            'SSP245': 'ssp2_4_5',
            'SSP370': 'ssp3_7_0',
            'SSP585': 'ssp5_8_5'
        }
        scenario_name = scenario_map.get(self.scenario, 'ssp5_8_5')

        # NetCDF 파일 경로
        nc_file = os.path.join(slr_dir, f'{scenario_name}_slr_annual_mean_2015-2100.nc')

        if not os.path.exists(nc_file):
            print(f"⚠️ [TCFD 경고] 해수면 상승 데이터 없음: {nc_file}")
            return {
                'slr_m': 0.0,
                'slr_cm': 0.0,
                'baseline_year': 2015,
                'target_year': year,
                'slr_rate_cm_per_year': 0.0,
                'data_source': 'no_data',
                'note': '해수면 상승 데이터 없음'
            }

        try:
            # NetCDF 로드
            dataset = nc.Dataset(nc_file, 'r')

            # 좌표 데이터
            lats = dataset.variables['latitude'][:]
            lons = dataset.variables['longitude'][:]

            # 시간 데이터 (days since 2015-01-01)
            time_var = dataset.variables['time']
            time_units = time_var.units  # "days since 2015-01-01 00:00:00"
            time_values = time_var[:]

            # 연도 변환 (days since 2015-01-01 → year)
            years = 2015 + (time_values / 365.25).astype(int)

            # 목표 연도 인덱스
            year_idx = np.argmin(np.abs(years - year))
            actual_year = years[year_idx]

            # 최근접 좌표 찾기
            lat_diff = np.abs(lats - lat)
            lon_diff = np.abs(lons - lon)

            # 2D 배열이므로 argmin을 2D로 적용
            min_idx = np.unravel_index(
                (lat_diff + lon_diff).argmin(),
                lat_diff.shape
            )

            # 해수면 상승량 추출 (단위: m)
            slr_data_raw = dataset.variables['slr_cm_annual_mean'][year_idx, min_idx[0], min_idx[1]]
            baseline_data_raw = dataset.variables['slr_cm_annual_mean'][0, min_idx[0], min_idx[1]]

            # NaN/Masked 값 체크 (내륙 지역)
            if np.ma.is_masked(slr_data_raw) or np.isnan(slr_data_raw):
                dataset.close()
                return {
                    'slr_m': 0.0,
                    'slr_cm': 0.0,
                    'baseline_slr_cm': 0.0,
                    'slr_increase_cm': 0.0,
                    'baseline_year': 2015,
                    'target_year': year,
                    'slr_rate_cm_per_year': 0.0,
                    'nearest_lat': float(lats[min_idx]),
                    'nearest_lon': float(lons[min_idx]),
                    'data_source': 'CMIP6 SSP (내륙 지역)',
                    'note': '내륙 지역 - 해수면 상승 영향 없음'
                }

            slr_m = float(slr_data_raw)
            slr_cm = slr_m * 100.0
            baseline_slr_m = float(baseline_data_raw)
            baseline_slr_cm = baseline_slr_m * 100.0

            # 상승률 계산 (기준 대비)
            years_elapsed = actual_year - 2015
            if years_elapsed > 0:
                slr_rate_cm_per_year = (slr_cm - baseline_slr_cm) / years_elapsed
            else:
                slr_rate_cm_per_year = 0.0

            dataset.close()

            return {
                'slr_m': round(slr_m, 3),
                'slr_cm': round(slr_cm, 1),
                'baseline_slr_cm': round(baseline_slr_cm, 1),
                'slr_increase_cm': round(slr_cm - baseline_slr_cm, 1),
                'baseline_year': 2015,
                'target_year': int(actual_year),
                'slr_rate_cm_per_year': round(slr_rate_cm_per_year, 2),
                'nearest_lat': float(lats[min_idx]),
                'nearest_lon': float(lons[min_idx]),
                'data_source': f'CMIP6 SSP {self.scenario} (NetCDF)',
                'note': '2015년 기준 상대적 해수면 상승'
            }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 해수면 상승 데이터 추출 실패: {e}")
            return {
                'slr_m': 0.0,
                'slr_cm': 0.0,
                'baseline_year': 2015,
                'target_year': year,
                'slr_rate_cm_per_year': 0.0,
                'data_source': 'error',
                'note': f'데이터 추출 실패: {e}'
            }

    def __del__(self):
        """캐시된 NetCDF 파일 닫기 및 임시 파일 삭제"""
        # NetCDF dataset 닫기
        for dataset in self._cache.values():
            try:
                if hasattr(dataset, 'close'):
                    dataset.close()
            except:
                pass

        # 임시 파일 삭제
        if hasattr(self, '_tmp_files'):
            for tmp_path in self._tmp_files:
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except:
                    pass

    # ========== Timeseries 메서드 (probability_calculate용) ==========

    def _extract_timeseries(self, variable: str, lat: float, lon: float,
                           start_year: int = 2021, end_year: int = 2100) -> np.ndarray:
        """
        NetCDF 파일에서 연도별 시계열 데이터 추출 (내부 헬퍼 메서드)

        Args:
            variable: 변수명 (TXx, SU25, WSDIx, RX1DAY 등)
            lat: 위도
            lon: 경도
            start_year: 시작 연도
            end_year: 종료 연도

        Returns:
            연도별 값 배열
        """
        if not NETCDF_AVAILABLE:
            return np.array([])

        try:
            # 캐시 확인
            cache_key = f"{variable}"
            if cache_key in self._cache:
                dataset = self._cache[cache_key]
            else:
                # NetCDF 파일 로드
                filename = f"{self.scenario}_{variable}_gridraw_yearly_2021-2100.nc"
                filepath = os.path.join(self.kma_dir, filename)

                if not os.path.exists(filepath):
                    return np.array([])

                # _extract_value에서 사용하는 로드 로직 재사용
                # 파일 로드는 _extract_value에서 캐시에 저장됨
                _ = self._extract_value(variable, lat, lon, 2021)
                dataset = self._cache.get(cache_key)

                if dataset is None:
                    return np.array([])

            # 좌표 인덱스 찾기
            lats = dataset.variables['latitude'][:]
            lons = dataset.variables['longitude'][:]
            lat_idx = np.abs(lats - lat).argmin()
            lon_idx = np.abs(lons - lon).argmin()

            # 연도 범위 계산
            start_idx = max(0, start_year - 2021)
            end_idx = min(80, end_year - 2021 + 1)

            # 시계열 데이터 추출 (time, latitude, longitude)
            if variable in dataset.variables:
                data_array = dataset.variables[variable][start_idx:end_idx, lat_idx, lon_idx]

                # Masked array 처리
                if hasattr(data_array, 'filled'):
                    data_array = data_array.filled(np.nan)

                return np.array(data_array, dtype=float)
            else:
                return np.array([])

        except Exception as e:
            print(f"⚠️ [TCFD 경고] {variable} 시계열 추출 실패: {e}")
            return np.array([])

    def _extract_monthly_timeseries(self, variable: str, lat: float, lon: float,
                                    start_year: int = 2021, end_year: int = 2100) -> np.ndarray:
        """
        월별 NetCDF 파일에서 시계열 데이터 추출 (내부 헬퍼 메서드)

        Args:
            variable: 변수명 (SPEI12, TA, RHM, WS, RN 등)
            lat: 위도
            lon: 경도
            start_year: 시작 연도
            end_year: 종료 연도

        Returns:
            월별 값 배열
        """
        if not NETCDF_AVAILABLE:
            return np.array([])

        try:
            # 캐시 확인
            cache_key = f"{variable}_monthly"
            if cache_key in self._cache:
                dataset = self._cache[cache_key]
            else:
                # 첫 호출로 캐시 로드
                _ = self._extract_monthly_value(variable, lat, lon, 2021, 1)
                dataset = self._cache.get(cache_key)

                if dataset is None:
                    return np.array([])

            # 좌표 인덱스 찾기
            lats = dataset.variables['latitude'][:]
            lons = dataset.variables['longitude'][:]
            lat_idx = np.abs(lats - lat).argmin()
            lon_idx = np.abs(lons - lon).argmin()

            # 시간 인덱스 계산
            start_month_idx = (start_year - 2021) * 12
            end_month_idx = (end_year - 2021 + 1) * 12

            start_month_idx = max(0, start_month_idx)
            end_month_idx = min(960, end_month_idx)

            # 월별 시계열 데이터 추출
            if variable in dataset.variables:
                data_array = dataset.variables[variable][start_month_idx:end_month_idx, lat_idx, lon_idx]

                # Masked array 처리
                if hasattr(data_array, 'filled'):
                    data_array = data_array.filled(np.nan)

                return np.array(data_array, dtype=float)
            else:
                return np.array([])

        except Exception as e:
            print(f"⚠️ [TCFD 경고] {variable} 월별 시계열 추출 실패: {e}")
            return np.array([])

    def get_extreme_heat_timeseries(self, lat: float, lon: float,
                                   start_year: int = 2021, end_year: int = 2100) -> Dict:
        """
        극심한 고온 시계열 데이터 추출 (probability_calculate용)

        Args:
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (기본 2021)
            end_year: 종료 연도 (기본 2100)

        Returns:
            {
                'wsdi': [연도별 WSDI 배열],
                'su25': [연도별 SU25 배열],
                'tr25': [연도별 TR25 배열],
                'txx': [연도별 TXx 배열],
                'years': [연도 리스트]
            }
        """
        wsdi_array = self._extract_timeseries('WSDIx', lat, lon, start_year, end_year)
        su25_array = self._extract_timeseries('SU25', lat, lon, start_year, end_year)
        tr25_array = self._extract_timeseries('TR25', lat, lon, start_year, end_year)
        txx_array = self._extract_timeseries('TXx', lat, lon, start_year, end_year)

        years = list(range(start_year, end_year + 1))

        return {
            'wsdi': wsdi_array.tolist() if len(wsdi_array) > 0 else [],
            'su25': su25_array.tolist() if len(su25_array) > 0 else [],
            'tr25': tr25_array.tolist() if len(tr25_array) > 0 else [],
            'txx': txx_array.tolist() if len(txx_array) > 0 else [],
            'years': years
        }

    def get_extreme_cold_timeseries(self, lat: float, lon: float,
                                   start_year: int = 2021, end_year: int = 2100) -> Dict:
        """
        극심한 한파 시계열 데이터 추출 (probability_calculate용)

        Args:
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (기본 2021)
            end_year: 종료 연도 (기본 2100)

        Returns:
            {
                'csdi': [연도별 CSDI 배열],
                'fd': [연도별 FD 배열],
                'tnn': [연도별 TNn 배열],
                'years': [연도 리스트]
            }
        """
        csdi_array = self._extract_timeseries('CSDIx', lat, lon, start_year, end_year)
        fd_array = self._extract_timeseries('FD', lat, lon, start_year, end_year)
        tnn_array = self._extract_timeseries('TNn', lat, lon, start_year, end_year)

        years = list(range(start_year, end_year + 1))

        return {
            'csdi': csdi_array.tolist() if len(csdi_array) > 0 else [],
            'fd': fd_array.tolist() if len(fd_array) > 0 else [],
            'tnn': tnn_array.tolist() if len(tnn_array) > 0 else [],
            'years': years
        }

    def get_drought_timeseries(self, lat: float, lon: float,
                              start_year: int = 2021, end_year: int = 2100) -> Dict:
        """
        가뭄 시계열 데이터 추출 (probability_calculate용)

        Args:
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (기본 2021)
            end_year: 종료 연도 (기본 2100)

        Returns:
            {
                'spei12': [월별 SPEI12 배열],
                'months_count': int,
                'years_count': int
            }
        """
        spei12_array = self._extract_monthly_timeseries('SPEI12', lat, lon, start_year, end_year)

        years_count = end_year - start_year + 1
        months_count = years_count * 12

        return {
            'spei12': spei12_array.tolist() if len(spei12_array) > 0 else [],
            'months_count': months_count,
            'years_count': years_count
        }

    def get_wildfire_timeseries(self, lat: float, lon: float,
                               start_year: int = 2021, end_year: int = 2100) -> Dict:
        """
        산불 FWI 입력 데이터 시계열 추출 (probability_calculate용)

        Args:
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (기본 2021)
            end_year: 종료 연도 (기본 2100)

        Returns:
            {
                'ta': [월별 기온 배열],
                'rhm': [월별 습도 배열],
                'ws': [월별 풍속 배열],
                'rn': [월별 강수 배열]
            }
        """
        ta_array = self._extract_monthly_timeseries('TA', lat, lon, start_year, end_year)
        rhm_array = self._extract_monthly_timeseries('RHM', lat, lon, start_year, end_year)
        ws_array = self._extract_monthly_timeseries('WS', lat, lon, start_year, end_year)
        rn_array = self._extract_monthly_timeseries('RN', lat, lon, start_year, end_year)

        return {
            'ta': ta_array.tolist() if len(ta_array) > 0 else [],
            'rhm': rhm_array.tolist() if len(rhm_array) > 0 else [],
            'ws': ws_array.tolist() if len(ws_array) > 0 else [],
            'rn': rn_array.tolist() if len(rn_array) > 0 else []
        }

    def get_flood_timeseries(self, lat: float, lon: float,
                            start_year: int = 2021, end_year: int = 2100) -> Dict:
        """
        홍수 시계열 데이터 추출 (probability_calculate용)

        Args:
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (기본 2021)
            end_year: 종료 연도 (기본 2100)

        Returns:
            {
                'rx1day': [연도별 RX1DAY 배열],
                'rx5day': [연도별 RX5DAY 배열],
                'years': [연도 리스트]
            }
        """
        rx1day_array = self._extract_timeseries('RX1DAY', lat, lon, start_year, end_year)
        rx5day_array = self._extract_timeseries('RX5DAY', lat, lon, start_year, end_year)

        years = list(range(start_year, end_year + 1))

        return {
            'rx1day': rx1day_array.tolist() if len(rx1day_array) > 0 else [],
            'rx5day': rx5day_array.tolist() if len(rx5day_array) > 0 else [],
            'years': years
        }

    def get_sea_level_rise_timeseries(self, lat: float, lon: float,
                                     start_year: int = 2021, end_year: int = 2100) -> Dict:
        """
        해수면 상승 시계열 데이터 추출 (probability_calculate용)

        Args:
            lat: 위도
            lon: 경도
            start_year: 시작 연도 (기본 2021)
            end_year: 종료 연도 (기본 2100)

        Returns:
            {
                'slr': [연도별 SLR 배열 (cm)],
                'years': [연도 리스트]
            }
        """
        # 해수면 상승은 별도 NetCDF 파일 사용
        # 각 연도별로 get_sea_level_rise_data 호출
        slr_values = []
        years = list(range(start_year, end_year + 1))

        for year in years:
            slr_data = self.get_sea_level_rise_data(lat, lon, year)
            slr_cm = slr_data.get('slr_increase_cm', 0.0)  # 기준연도 대비 증가량
            slr_values.append(slr_cm)

        return {
            'slr': slr_values,
            'years': years
        }


# 테스트 코드
if __name__ == '__main__':
    loader = ClimateDataLoader(scenario='SSP245')

    # 대전 유성구
    lat, lon = 36.383, 127.395
    year = 2030

    print(f"\n{'='*80}")
    print(f"KMA SSP 기후 데이터 로드 테스트")
    print(f"{'='*80}")
    print(f"위치: ({lat}, {lon})")
    print(f"시나리오: SSP245")
    print(f"연도: {year}")

    print(f"\n1. 극심한 고온:")
    heat = loader.get_extreme_heat_data(lat, lon, year)
    for k, v in heat.items():
        print(f"   {k}: {v}")

    print(f"\n2. 극심한 극심한 한파:")
    cold = loader.get_extreme_cold_data(lat, lon, year)
    for k, v in cold.items():
        print(f"   {k}: {v}")

    print(f"\n3. 가뭄:")
    drought = loader.get_drought_data(lat, lon, year)
    for k, v in drought.items():
        print(f"   {k}: {v}")

    print(f"\n4. 홍수:")
    flood = loader.get_flood_data(lat, lon, year)
    for k, v in flood.items():
        print(f"   {k}: {v}")
