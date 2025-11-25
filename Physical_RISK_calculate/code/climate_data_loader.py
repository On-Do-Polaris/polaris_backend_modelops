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
            base_dir: 데이터 기본 경로 (기본값: 현재 파일 기준 ../data)
            scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
        """
        if base_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.join(current_dir, '..', 'data')

        self.base_dir = base_dir
        self.scenario = scenario
        self.kma_dir = os.path.join(base_dir, 'KMA', 'gridraw', scenario, 'yearly')

        # 캐시: 한 번 로드한 데이터는 메모리에 저장
        self._cache = {}

        if not NETCDF_AVAILABLE:
            print("⚠️ [경고] netCDF4 라이브러리가 없습니다. pip install netCDF4")

    def get_extreme_heat_data(self, lat: float, lon: float, year: int = 2030) -> Dict:
        """
        극한 고온 데이터 추출

        Args:
            lat: 위도
            lon: 경도
            year: 분석 연도 (2021-2100)

        Returns:
            {
                'annual_max_temp_celsius': float,  # TXx: 연간 최고기온
                'heatwave_days_per_year': int,      # SU25: 폭염일수 (일최고기온 >= 25°C)
                'tropical_nights': int,             # TR25: 열대야일수 (일최저기온 >= 25°C)
                'heat_wave_duration': float,        # WSDI: 폭염 지속 일수
                'data_source': str
            }
        """
        try:
            # TXx: 연간 최고기온
            txx = self._extract_value('TXx', lat, lon, year)

            # SU25: 폭염일수
            su25 = self._extract_value('SU25', lat, lon, year)

            # TR25: 열대야일수
            tr25 = self._extract_value('TR25', lat, lon, year)

            # WSDIx: 폭염 지속일수
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
            print(f"⚠️ [TCFD 경고] 극한 고온 데이터 로드 실패: {e}")
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
        극한 한파 데이터 추출

        Returns:
            {
                'annual_min_temp_celsius': float,  # TNn: 연간 최저기온
                'coldwave_days_per_year': int,     # FD0: 결빙일수 (일최저기온 < 0°C)
                'ice_days': int,                   # ID0: 얼음일수 (일최고기온 < 0°C)
                'cold_wave_duration': float,       # CSDI: 한파 지속일수
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

            # CSDIx: 한파 지속일수
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
            print(f"⚠️ [TCFD 경고] 극한 한파 데이터 로드 실패: {e}")
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
                'annual_rainfall_mm': float,        # 연간 총 강수량
                'consecutive_dry_days': int,        # CDD: 최대 연속 무강수일수
                'rainfall_intensity': float,        # SDII: 강수일 평균 강수강도
                'extreme_dry_ratio': float,         # 가뭄 비율
                'data_source': str
            }
        """
        try:
            # RN: 연간 총 강수량
            rn = self._extract_value('RN', lat, lon, year)

            # CDD: 최대 연속 무강수일수
            cdd = self._extract_value('CDD', lat, lon, year)

            # SDII: 강수일 평균 강수강도
            sdii = self._extract_value('SDII', lat, lon, year)

            return {
                'annual_rainfall_mm': float(rn) if rn is not None else 1200.0,
                'consecutive_dry_days': int(cdd) if cdd is not None else 15,
                'rainfall_intensity': float(sdii) if sdii is not None else 10.0,
                'climate_scenario': self.scenario,
                'year': year,
                'data_source': 'KMA_SSP_gridraw' if rn is not None else 'fallback'
            }
        except Exception as e:
            print(f"⚠️ [TCFD 경고] 가뭄 데이터 로드 실패: {e}")
            return {
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
                    # gzip 파일을 메모리에서 압축 해제
                    import io
                    with gzip.open(filepath, 'rb') as gz_file:
                        nc_data = gz_file.read()

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

    print(f"\n1. 극한 고온:")
    heat = loader.get_extreme_heat_data(lat, lon, year)
    for k, v in heat.items():
        print(f"   {k}: {v}")

    print(f"\n2. 극한 한파:")
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
