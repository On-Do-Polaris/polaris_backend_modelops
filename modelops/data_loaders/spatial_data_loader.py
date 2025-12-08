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

try:
    from ease_lonlat import EASE2GRID, SUPPORTED_GRIDS
    EASE_GRID_AVAILABLE = True
except ImportError:
    EASE_GRID_AVAILABLE = False
    warnings.warn("ease-lonlat not available. Install with: pip install ease-lonlat")


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
            # 현재 파일(modelops/data_loaders) 기준, 프로젝트 루트로 이동 후 데이터 경로 설정
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, '..', '..')
            base_dir = os.path.join(project_root, 'physical_risk_module_core_merge', 'Physical_RISK_calculate', 'data')

        self.base_dir = base_dir
        self.dem_dir = os.path.join(self.base_dir, 'DEM')
        self.landcover_dir = os.path.join(self.base_dir, 'landcover', 'ME_GROUNDCOVERAGE_50000')
        self.drought_dir = os.path.join(self.base_dir, 'drought')
        self.geodata_dir = os.path.join(self.base_dir, 'geodata')

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
                        # WGS84 → 파일의 좌표계로 변환
                        from pyproj import Transformer
                        transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                        x, y = transformer.transform(lon, lat)

                        # 변환된 좌표가 이 타일 범위 내에 있는지 확인
                        bounds = src.bounds
                        if bounds.left <= x <= bounds.right and bounds.bottom <= y <= bounds.top:
                            # 래스터 값 추출
                            row, col = rowcol(src.transform, x, y)
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
        사용자 제공 솔루션(ease-lonlat) 적용

        Returns:
            {
                'soil_moisture': float,          # 토양 수분 (m³/m³)
                'drought_indicator': str,        # 가뭄 지표 (normal/dry/very_dry)
                'data_source': str
            }
        """
        try:
            if not H5PY_AVAILABLE or not EASE_GRID_AVAILABLE:
                return self._fallback_soil_moisture()

            # SMAP HDF5 파일 찾기
            h5_files = [f for f in os.listdir(self.drought_dir)
                       if f.startswith('SMAP') and f.endswith('.h5')]

            if not h5_files:
                return self._fallback_soil_moisture()

            filepath = os.path.join(self.drought_dir, h5_files[0])

            # EASE-Grid 2.0 Global 9km 초기화
            grid_name = 'EASE2_G9km'
            ease_grid = EASE2GRID(name=grid_name, **SUPPORTED_GRIDS[grid_name])
            
            # 위/경도를 EASE-Grid 행/열 인덱스로 변환
            col, row = ease_grid.lonlat2rc(lon, lat)

            # HDF5 파일에서 토양수분 데이터 읽기
            with h5py.File(filepath, 'r') as f:
                # 표층 토양수분 (0-5cm)
                sm_surface = f['Analysis_Data']['sm_surface_analysis'][row, col]
                
                # 유효성 검사
                if sm_surface < 0 or sm_surface > 1:
                    print(f"Warning: Invalid soil moisture value at ({lat}, {lon})")
                    return self._fallback_soil_moisture()
            
            soil_moisture = float(sm_surface)

            # 가뭄 지표 판단
            if soil_moisture < 0.1:
                drought = 'very_dry'
            elif soil_moisture < 0.2:
                drought = 'dry'
            else:
                drought = 'normal'

            return {
                'soil_moisture': soil_moisture,
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
                    gdf = gpd.read_file(shp_file)
                    # WGS84 좌표계로 변환
                    if gdf.crs and gdf.crs.to_string() != 'EPSG:4326':
                        gdf = gdf.to_crs('EPSG:4326')
                    self._admin_boundary = gdf

            if self._admin_boundary is None:
                return self._fallback_admin()

            # 포인트 생성
            from shapely.geometry import Point
            point = Point(lon, lat)

            # 해당 행정구역 찾기
            matches = self._admin_boundary[self._admin_boundary.contains(point)]

            if len(matches) > 0:
                match = matches.iloc[0]

                # 법정동 코드에서 시도/시군구 추출 (BJCD 형식: 3020014200)
                bjcd = str(match.get('BJCD', ''))
                sido_code = bjcd[:2] if len(bjcd) >= 2 else ''
                sigungu_code = bjcd[2:5] if len(bjcd) >= 5 else ''

                # 시도명 매핑
                sido_map = {
                    '11': '서울특별시', '26': '부산광역시', '27': '대구광역시',
                    '28': '인천광역시', '29': '광주광역시', '30': '대전광역시',
                    '31': '울산광역시', '36': '세종특별자치시', '41': '경기도',
                    '42': '강원도', '43': '충청북도', '44': '충청남도',
                    '45': '전라북도', '46': '전라남도', '47': '경상북도',
                    '48': '경상남도', '50': '제주특별자치도'
                }

                sido = sido_map.get(sido_code, 'unknown')

                # 시군구명은 별도 로직 필요 (여기서는 간단히 처리)
                sigungu = 'unknown'
                if sido_code == '30':  # 대전
                    sigungu_map = {'110': '동구', '140': '중구', '170': '서구',
                                   '200': '유성구', '230': '대덕구'}
                    sigungu = sigungu_map.get(sigungu_code, 'unknown')

                return {
                    'sido': sido,
                    'sigungu': sigungu,
                    'dong': match.get('NAME', 'unknown'),
                    'adm_code': bjcd,
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

    def get_dem_data(self, lat: float, lon: float) -> Dict:
        """
        DEM 데이터에서 고도 및 경사도 추출
        """
        try:
            if not RASTERIO_AVAILABLE:
                return self._fallback_dem()

            # 1. 좌표로부터 시군구 이름 얻기
            admin_area = self.get_administrative_area(lat, lon)
            sido = admin_area.get('sido')
            sigungu = admin_area.get('sigungu')

            if not sido or not sigungu or sigungu == 'unknown':
                print(f"⚠️ DEM: 시군구 정보를 찾을 수 없습니다. ({lat}, {lon})")
                return self._fallback_dem()

            # 2. DEM 파일 경로 구성
            dem_filename = f"{sido} {sigungu}.img"
            dem_path = os.path.join(self.dem_dir, dem_filename)

            if not os.path.exists(dem_path):
                # 파일명이 '대전광역시 유성구'가 아닌 '대전광역시_유성구' 형태일 수 있음
                dem_filename = f"{sido}_{sigungu}.img"
                dem_path = os.path.join(self.dem_dir, dem_filename)
                if not os.path.exists(dem_path):
                    print(f"⚠️ DEM 파일을 찾을 수 없습니다: {dem_path}")
                    return self._fallback_dem()
            
            with rasterio.open(dem_path) as src:
                # 3. 좌표를 래스터의 행/열로 변환
                from pyproj import Transformer
                transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                x, y = transformer.transform(lon, lat)
                row, col = src.index(x, y)

                # 4. Horn's method를 사용한 경사도 계산
                # 3x3 윈도우 읽기
                window = src.read(1, window=rasterio.windows.Window(col - 1, row - 1, 3, 3))
                
                # 셀 크기 (해상도)
                cell_size_x, cell_size_y = src.res
                
                # Horn's method (dz/dx, dz/dy 계산)
                dz_dx = ((window[0, 2] + 2 * window[1, 2] + window[2, 2]) - 
                         (window[0, 0] + 2 * window[1, 0] + window[2, 0])) / (8 * cell_size_x)
                
                dz_dy = ((window[2, 0] + 2 * window[2, 1] + window[2, 2]) - 
                         (window[0, 0] + 2 * window[0, 1] + window[0, 2])) / (8 * cell_size_y)

                # 경사도(라디안) 및 변환(도)
                rise_run = np.sqrt(dz_dx**2 + dz_dy**2)
                slope_rad = np.arctan(rise_run)
                slope_deg = np.degrees(slope_rad)
                
                # 중심점의 고도값
                elevation = window[1, 1]

                return {
                    'slope_degree': float(slope_deg),
                    'elevation_m': float(elevation),
                    'data_source': 'DEM'
                }

        except Exception as e:
            print(f"⚠️ [TCFD 경고] DEM 데이터 처리 실패: {e}")
            return self._fallback_dem()

    def _fallback_dem(self) -> Dict:
        return {
            'slope_degree': 5.0, # 완만한 경사 기본값
            'elevation_m': 50.0, # 평균 고도 기본값
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
