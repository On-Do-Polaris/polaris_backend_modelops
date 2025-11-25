#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Spatial Data Loader
공간 데이터 로드: 토지피복도, NDVI, 토양수분, 행정경계
"""

import os
import warnings
from typing import Dict, Tuple, Optional
import numpy as np

# 공간 데이터 처리 라이브러리
try:
    import rasterio
    from rasterio.transform import rowcol
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    warnings.warn("rasterio not available. Install with: pip install rasterio")

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False
    warnings.warn("h5py not available. Install with: pip install h5py")

try:
    from pyhdf.SD import SD, SDC
    PYHDF_AVAILABLE = True
except ImportError:
    PYHDF_AVAILABLE = False
    warnings.warn("pyhdf not available. Install with: pip install python-hdf4")

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    warnings.warn("geopandas not available. Install with: pip install geopandas")


class SpatialDataLoader:
    """
    공간 데이터 로더

    - 토지피복도: GeoTIFF (.tif)
    - NDVI: MODIS HDF (.hdf)
    - 토양수분: SMAP HDF5 (.h5)
    - 행정경계: Shapefile (.shp)
    """

    def __init__(self, base_dir: str = None):
        """
        Args:
            base_dir: 데이터 기본 경로
        """
        if base_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.join(current_dir, '..', 'data')

        self.base_dir = base_dir
        self.landcover_dir = os.path.join(base_dir, 'landcover', 'ME_GROUNDCOVERAGE_50000')
        self.drought_dir = os.path.join(base_dir, 'drought')
        self.geodata_dir = os.path.join(base_dir, 'geodata')

        # 캐시
        self._landcover_cache = {}
        self._admin_boundary = None

    def get_landcover_data(self, lat: float, lon: float) -> Dict:
        """
        토지피복도 데이터 추출

        Returns:
            {
                'landcover_type': str,           # 토지 유형
                'impervious_ratio': float,       # 불투수면 비율 (0-1)
                'vegetation_ratio': float,       # 식생 비율 (0-1)
                'urban_intensity': str,          # 도시화 정도 (low/medium/high)
                'data_source': str
            }
        """
        try:
            if not RASTERIO_AVAILABLE:
                return self._fallback_landcover()

            # 토지피복도 파일들 중 해당 위치를 포함하는 타일 찾기
            tif_files = [f for f in os.listdir(self.landcover_dir) if f.endswith('.tif')]

            value = None
            for tif_file in tif_files:
                filepath = os.path.join(self.landcover_dir, tif_file)
                try:
                    with rasterio.open(filepath) as src:
                        # 좌표가 이 타일 범위 내에 있는지 확인
                        bounds = src.bounds
                        if bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top:
                            # 래스터 값 추출
                            row, col = rowcol(src.transform, lon, lat)
                            if 0 <= row < src.height and 0 <= col < src.width:
                                value = src.read(1)[row, col]
                                break
                except:
                    continue

            if value is None:
                return self._fallback_landcover()

            # 토지피복 분류 (환경부 중분류 기준 가정)
            # 1-10: 시가화건조지역 (불투수면)
            # 11-30: 농업지역
            # 31-50: 산림지역
            # 51-60: 초지
            # 61-70: 습지
            # 71-80: 나지
            # 81-90: 수역

            landcover_type = 'unknown'
            impervious = 0.0
            vegetation = 0.0
            urban = 'low'

            if 1 <= value <= 10:
                landcover_type = 'urban'
                impervious = 0.7  # 도시 불투수면 70%
                vegetation = 0.1
                urban = 'high'
            elif 11 <= value <= 30:
                landcover_type = 'agricultural'
                impervious = 0.1
                vegetation = 0.6
                urban = 'low'
            elif 31 <= value <= 50:
                landcover_type = 'forest'
                impervious = 0.0
                vegetation = 0.9
                urban = 'low'
            elif 51 <= value <= 60:
                landcover_type = 'grassland'
                impervious = 0.0
                vegetation = 0.8
                urban = 'low'
            elif 61 <= value <= 70:
                landcover_type = 'wetland'
                impervious = 0.0
                vegetation = 0.7
                urban = 'low'
            elif 71 <= value <= 80:
                landcover_type = 'barren'
                impervious = 0.2
                vegetation = 0.1
                urban = 'medium'
            elif 81 <= value <= 90:
                landcover_type = 'water'
                impervious = 0.0
                vegetation = 0.0
                urban = 'low'

            return {
                'landcover_type': landcover_type,
                'impervious_ratio': impervious,
                'vegetation_ratio': vegetation,
                'urban_intensity': urban,
                'raw_value': int(value),
                'data_source': 'ME_GROUNDCOVERAGE_50000'
            }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 토지피복도 로드 실패: {e}")
            return self._fallback_landcover()

    def get_ndvi_data(self, lat: float, lon: float) -> Dict:
        """
        NDVI (식생지수) 데이터 추출

        Returns:
            {
                'ndvi': float,                   # NDVI 값 (-1 to 1)
                'vegetation_health': str,        # 식생 건강도 (poor/fair/good/excellent)
                'wildfire_fuel': str,            # 산불 연료 (low/medium/high)
                'data_source': str
            }
        """
        try:
            if not PYHDF_AVAILABLE:
                return self._fallback_ndvi()

            # MODIS HDF 파일 찾기
            hdf_files = [f for f in os.listdir(self.drought_dir)
                        if f.startswith('MOD13Q1') and f.endswith('.hdf')]

            if not hdf_files:
                return self._fallback_ndvi()

            filepath = os.path.join(self.drought_dir, hdf_files[0])

            # HDF 파일 열기
            hdf = SD(filepath, SDC.READ)

            # NDVI 데이터셋 추출 (일반적으로 '250m 16 days NDVI')
            ndvi_dataset = None
            for dataset_name in hdf.datasets().keys():
                if 'NDVI' in dataset_name.upper():
                    ndvi_dataset = hdf.select(dataset_name)
                    break

            if ndvi_dataset is None:
                return self._fallback_ndvi()

            # 데이터 읽기
            ndvi_data = ndvi_dataset.get()

            # 좌표를 픽셀 인덱스로 변환 (MODIS 타일 좌표계)
            # 주의: 실제로는 타일 범위와 해상도를 고려해야 함
            # 여기서는 간단히 중심값 사용
            center_row = ndvi_data.shape[0] // 2
            center_col = ndvi_data.shape[1] // 2

            ndvi_value = ndvi_data[center_row, center_col]

            # NDVI 스케일링 (MODIS는 보통 -2000 ~ 10000 범위)
            ndvi = ndvi_value / 10000.0

            # 식생 건강도 판단
            if ndvi < 0.2:
                veg_health = 'poor'
                fuel = 'low'
            elif ndvi < 0.4:
                veg_health = 'fair'
                fuel = 'low'
            elif ndvi < 0.6:
                veg_health = 'good'
                fuel = 'medium'
            else:
                veg_health = 'excellent'
                fuel = 'high'

            hdf.end()

            return {
                'ndvi': float(ndvi),
                'vegetation_health': veg_health,
                'wildfire_fuel': fuel,
                'data_source': 'MOD13Q1'
            }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] NDVI 로드 실패: {e}")
            return self._fallback_ndvi()

    def get_soil_moisture_data(self, lat: float, lon: float) -> Dict:
        """
        토양수분 데이터 추출 (SMAP)

        Returns:
            {
                'soil_moisture': float,          # 토양 수분 (m³/m³)
                'drought_indicator': str,        # 가뭄 지표 (normal/dry/very_dry)
                'data_source': str
            }
        """
        try:
            if not H5PY_AVAILABLE:
                return self._fallback_soil_moisture()

            # SMAP HDF5 파일 찾기
            h5_files = [f for f in os.listdir(self.drought_dir)
                       if f.startswith('SMAP') and f.endswith('.h5')]

            if not h5_files:
                return self._fallback_soil_moisture()

            filepath = os.path.join(self.drought_dir, h5_files[0])

            # HDF5 파일 열기
            with h5py.File(filepath, 'r') as f:
                # SMAP L4 구조: /Analysis_Data/sm_surface_analysis
                sm_data = None
                for key in f.keys():
                    if 'sm' in key.lower() or 'soil' in key.lower():
                        sm_data = f[key]
                        break

                if sm_data is None:
                    # 일반적인 경로 시도
                    try:
                        sm_data = f['Analysis_Data']['sm_surface_analysis'][:]
                    except:
                        return self._fallback_soil_moisture()
                else:
                    sm_data = sm_data[:]

                # 중심값 사용 (실제로는 좌표 변환 필요)
                if len(sm_data.shape) >= 2:
                    center_row = sm_data.shape[0] // 2
                    center_col = sm_data.shape[1] // 2
                    soil_moisture = sm_data[center_row, center_col]
                else:
                    soil_moisture = np.mean(sm_data)

                # 가뭄 지표 판단 (일반적으로 0.1-0.4 m³/m³ 범위)
                if soil_moisture < 0.1:
                    drought = 'very_dry'
                elif soil_moisture < 0.2:
                    drought = 'dry'
                else:
                    drought = 'normal'

                return {
                    'soil_moisture': float(soil_moisture),
                    'drought_indicator': drought,
                    'data_source': 'SMAP_L4'
                }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 토양수분 로드 실패: {e}")
            return self._fallback_soil_moisture()

    def get_administrative_area(self, lat: float, lon: float) -> Dict:
        """
        행정구역 정보 추출

        Returns:
            {
                'sido': str,           # 시도
                'sigungu': str,        # 시군구
                'dong': str,           # 읍면동
                'adm_code': str,       # 행정구역 코드
                'data_source': str
            }
        """
        try:
            if not GEOPANDAS_AVAILABLE:
                return self._fallback_admin()

            # 캐시 확인
            if self._admin_boundary is None:
                shp_file = os.path.join(self.geodata_dir, 'N3A_G0110000.shp')
                if os.path.exists(shp_file):
                    self._admin_boundary = gpd.read_file(shp_file)

            if self._admin_boundary is None:
                return self._fallback_admin()

            # 포인트 생성
            from shapely.geometry import Point
            point = Point(lon, lat)

            # 해당 행정구역 찾기
            matches = self._admin_boundary[self._admin_boundary.contains(point)]

            if len(matches) > 0:
                match = matches.iloc[0]
                return {
                    'sido': match.get('CTP_KOR_NM', 'unknown'),
                    'sigungu': match.get('SIG_KOR_NM', 'unknown'),
                    'dong': match.get('EMD_KOR_NM', 'unknown'),
                    'adm_code': match.get('ADM_DR_CD', 'unknown'),
                    'data_source': 'N3A_G0110000'
                }

            return self._fallback_admin()

        except Exception as e:
            print(f"⚠️ [TCFD 경고] 행정구역 로드 실패: {e}")
            return self._fallback_admin()

    # Fallback 함수들
    def _fallback_landcover(self) -> Dict:
        return {
            'landcover_type': 'mixed',
            'impervious_ratio': 0.5,
            'vegetation_ratio': 0.3,
            'urban_intensity': 'medium',
            'data_source': 'fallback'
        }

    def _fallback_ndvi(self) -> Dict:
        return {
            'ndvi': 0.4,
            'vegetation_health': 'fair',
            'wildfire_fuel': 'medium',
            'data_source': 'fallback'
        }

    def _fallback_soil_moisture(self) -> Dict:
        return {
            'soil_moisture': 0.2,
            'drought_indicator': 'normal',
            'data_source': 'fallback'
        }

    def _fallback_admin(self) -> Dict:
        return {
            'sido': 'unknown',
            'sigungu': 'unknown',
            'dong': 'unknown',
            'adm_code': 'unknown',
            'data_source': 'fallback'
        }


# 테스트 코드
if __name__ == '__main__':
    loader = SpatialDataLoader()

    # 대전 유성구
    lat, lon = 36.383, 127.395

    print(f"\n{'='*80}")
    print(f"공간 데이터 로드 테스트")
    print(f"{'='*80}")
    print(f"위치: ({lat}, {lon})")

    print(f"\n1. 토지피복도:")
    landcover = loader.get_landcover_data(lat, lon)
    for k, v in landcover.items():
        print(f"   {k}: {v}")

    print(f"\n2. NDVI:")
    ndvi = loader.get_ndvi_data(lat, lon)
    for k, v in ndvi.items():
        print(f"   {k}: {v}")

    print(f"\n3. 토양수분:")
    soil = loader.get_soil_moisture_data(lat, lon)
    for k, v in soil.items():
        print(f"   {k}: {v}")

    print(f"\n4. 행정구역:")
    admin = loader.get_administrative_area(lat, lon)
    for k, v in admin.items():
        print(f"   {k}: {v}")
