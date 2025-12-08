#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exposure Calculator (E)
노출도 계산: 건물이 재난에 노출되어 있는가?
"""

from typing import Dict, Union, Tuple, Optional
from ..data.building_data_fetcher import BuildingDataFetcher
from ..data.spatial_data_loader import SpatialDataLoader
from ..common import config


def interpolate_population_by_cagr(target_year: int, location_admin_data: Dict) -> int:
    """
    location_admin의 5년 단위 인구 데이터(population_2020~2050)로부터
    임의 연도 인구를 구간별 CAGR(Compound Annual Growth Rate)로 계산합니다.
    """
    # ... (생략된 코드는 이전과 동일)
    years = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
    population_keys = [f'population_{year}' for year in years]
    start_year, end_year = None, None
    for i in range(len(years) - 1):
        if years[i] <= target_year < years[i + 1]:
            start_year, end_year = years[i], years[i+1]
            break
    if target_year >= 2050: return int(location_admin_data.get('population_2050', 0))
    if start_year is None: return int(location_admin_data.get('population_2020', 0))
    p_start = location_admin_data.get(f'population_{start_year}', 0)
    p_end = location_admin_data.get(f'population_{end_year}', 0)
    if p_start <= 0 or p_end <= 0: return int(p_start if p_start > 0 else p_end)
    interval_years = end_year - start_year
    cagr = (p_end / p_start) ** (1 / interval_years) - 1
    years_from_start = target_year - start_year
    p_target = p_start * ((1 + cagr) ** years_from_start)
    return int(round(p_target))


def get_sigungu_future_population(
    target_year: int,
    sigungu_location_data: Dict,
    sido_location_data: Dict
) -> int:
    """
    시도 단위 인구 데이터로부터 시군구별 미래 인구를 비례 계산합니다.
    """
    # ... (생략된 코드는 이전과 동일)
    future_sido_pop = interpolate_population_by_cagr(target_year, sido_location_data)
    current_sigungu_pop = sigungu_location_data.get('population_2020', 0)
    current_sido_pop = sido_location_data.get('population_2020', 0)
    if current_sido_pop <= 0: return int(future_sido_pop * 0.01)
    current_ratio = current_sigungu_pop / current_sido_pop
    future_sigungu_pop = future_sido_pop * current_ratio
    return int(round(future_sigungu_pop))


class ExposureCalculator:
    """
    노출도(Exposure) 계산기
    """

    def __init__(self):
        self.fetcher = BuildingDataFetcher()
        self.spatial_loader = SpatialDataLoader() # ✅ SpatialDataLoader 초기화

    def calculate(self, location: Union[str, Tuple[float, float]]) -> Dict:
        """
        위/경도 또는 주소 → 노출도 데이터
        """
        if isinstance(location, str):
            lat, lon = self._address_to_coords(location)
        else:
            lat, lon = location

        print(f"\n{'='*80}")
        print(f"[Exposure Calculator] 노출도 계산")
        print(f"{'='*80}")
        print(f"위치: ({lat}, {lon})")

        # building_data_fetcher 사용하여 모든 데이터 수집
        raw_data = self.fetcher.fetch_all_building_data(lat, lon)
        
        # ✅ landcover 데이터 실제 로드
        landcover_data = self.spatial_loader.get_landcover_data(lat, lon)

        # 노출도 구조화
        exposure = self._structure_exposure_data(raw_data, landcover_data, lat, lon)

        print(f"\n✅ 노출도 계산 완료")
        self._print_summary(exposure)

        return exposure

    def _structure_exposure_data(self, raw_data: Dict, landcover_data: Dict, lat: float, lon: float) -> Dict:
        """
        building_data_fetcher 결과 → 노출도 구조화
        """
        defaults = config.DEFAULT_BUILDING_PROPERTIES
        dist_defaults = config.DEFAULT_DISTANCE_VALUES
        hydro_defaults = config.DEFAULT_HYDROLOGICAL_VALUES
        
        # ✅ 실제 토지피복도 데이터 사용
        land_use = landcover_data.get('landcover_type', 'urban')

        return {
            'location': {
                'latitude': lat,
                'longitude': lon,
                'elevation_m': raw_data.get('elevation_m', defaults['elevation_m']),
                'land_use': land_use,
            },
            'building': {
                'floors_above': raw_data.get('ground_floors', defaults['ground_floors']),
                'floors_below': raw_data.get('basement_floors', defaults['basement_floors']),
                'ground_floors': raw_data.get('ground_floors', defaults['ground_floors']),
                'total_area_m2': raw_data.get('total_area_m2', defaults['total_area_m2']),
                'building_type': raw_data.get('building_type', defaults['building_type']),
                'main_purpose': raw_data.get('main_purpose', defaults['main_purpose']),
                'structure': raw_data.get('structure', defaults['structure']),
                'build_year': raw_data.get('build_year', defaults['build_year']),
                'building_age': raw_data.get('building_age', defaults['building_age']),
                'has_piloti': raw_data.get('has_piloti', defaults['has_piloti']),
            },
            'flood_exposure': {
                'distance_to_river_m': raw_data.get('distance_to_river_m', dist_defaults['distance_to_river_m']),
                'proximity_category': self._calculate_river_flood_exposure_score(raw_data.get('distance_to_river_m', dist_defaults['distance_to_river_m']))[0],
                'score': self._calculate_river_flood_exposure_score(raw_data.get('distance_to_river_m', dist_defaults['distance_to_river_m']))[1],
                'distance_to_coast_m': raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']),
                'watershed_area_km2': raw_data.get('watershed_area_km2', hydro_defaults['watershed_area_km2']),
                'stream_order': raw_data.get('stream_order', hydro_defaults['stream_order']),
                'in_flood_zone': self._is_in_flood_zone(raw_data),
            },
            'heat_exposure': {
                'urban_heat_island': self._estimate_uhi_intensity(raw_data),
                'green_space_nearby': self._estimate_green_space_proximity(landcover_data), # ✅ landcover 데이터 전달
                'building_orientation': self._estimate_building_orientation(lat, lon),
                'uhi_risk': self._classify_uhi_risk(landcover_data), # ✅ landcover 데이터 전달
            },
            'urban_flood_exposure': {
                'urban_intensity': self._calculate_urban_flood_exposure_score(raw_data)[0],
                'score': self._calculate_urban_flood_exposure_score(raw_data)[1],
                'imperviousness_percent': self._calculate_urban_flood_exposure_score(raw_data)[2],
                'impervious_surface_ratio': self._estimate_impervious_surface_ratio(landcover_data), # ✅ landcover 데이터 전달
                'drainage_capacity': self._estimate_drainage_capacity(raw_data),
                'urban_area': land_use in ['urban', 'commercial', 'residential', 'mixed-use', 'industrial'],
            },
            'drought_exposure': {
                'annual_rainfall_mm': raw_data.get('annual_rainfall_mm', hydro_defaults['annual_rainfall_mm']),
                'water_dependency': self._classify_water_dependency(raw_data),
                'score': self._calculate_drought_exposure_score(self._classify_water_dependency(raw_data), raw_data.get('annual_rainfall_mm', hydro_defaults['annual_rainfall_mm'])),
                'water_storage_capacity': self._estimate_water_storage(raw_data),
                'backup_water_supply': raw_data.get('backup_water_supply', False),
            },
            'typhoon_exposure': {
                'distance_to_coast_m': raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']),
                'coastal_exposure': raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']) < 10000,
                'coastal_distance_score': self._calculate_typhoon_distance_score(raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
                'exposure_level': self._classify_typhoon_exposure_level(raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
            },
            'sea_level_rise_exposure': {
                'distance_to_coast_m': raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']),
                'coastal_distance_score': self._calculate_coastal_distance_score(raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
                'exposure_level': self._classify_coastal_exposure_level(raw_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
            },
            'wildfire_exposure': {
                'distance_to_forest_m': self._calculate_forest_distance(landcover_data), # ✅ landcover 데이터 전달
                'proximity_category': self._calculate_wildfire_exposure_score(self._calculate_forest_distance(landcover_data))[0],
                'score': self._calculate_wildfire_exposure_score(self._calculate_forest_distance(landcover_data))[1],
                'vegetation_type': self._get_vegetation_type(landcover_data), # ✅ landcover 데이터 전달
                'slope_degree': self._calculate_slope_from_dem(raw_data),
            },
            'metadata': {
                'data_source': 'building_data_fetcher, spatial_data_loader',
                'data_quality': self._assess_data_quality(raw_data),
                'tcfd_warnings': raw_data.get('tcfd_warnings', []),
            }
        }

    def _address_to_coords(self, address: str) -> Tuple[float, float]:
        # ... (이전과 동일, 생략)
        import os, requests
        from dotenv import load_dotenv
        from pathlib import Path
        BASE_DIR = Path(__file__).parent.parent
        load_dotenv(BASE_DIR / ".env")
        VWORLD_KEY = os.getenv("VWORLD_API_KEY")
        url = "https://api.vworld.kr/req/address"
        for address_type in ['ROAD', 'PARCEL']:
            params = {'service': 'address', 'request': 'getcoord', 'format': 'json', 'crs': 'epsg:4326', 'address': address, 'type': address_type, 'key': VWORLD_KEY}
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data['response']['status'] == 'OK':
                    result = data['response']['result']
                    if result and 'point' in result:
                        lon = float(result['point']['x'])
                        lat = float(result['point']['y'])
                        print(f"✅ 주소 변환 성공 ({address_type}): {address} → ({lat}, {lon})")
                        return lat, lon
            except Exception as e:
                print(f"⚠️ {address_type} 타입 시도 실패: {e}")
                continue
        raise ValueError(f"주소를 좌표로 변환 실패: {address} (ROAD, PARCEL 모두 실패)")

    def _classify_land_use(self, landcover_data: Dict) -> str:
        """✅ 실제 토지피복도 데이터 기반으로 토지 이용 분류"""
        return landcover_data.get('landcover_type', 'urban')

    def _is_in_flood_zone(self, data: Dict) -> bool:
        # ... (이전과 동일, 생략)
        distance_to_river = data.get('distance_to_river_m', 1000)
        elevation = data.get('elevation_m', 50)
        return distance_to_river < 100 and elevation < 50

    def _estimate_uhi_intensity(self, data: Dict) -> str:
        # ... (이전과 동일, 생략)
        building_type = data.get('building_type', '주택')
        if '업무' in building_type or '상업' in building_type: return 'high'
        elif '주택' in building_type: return 'medium'
        else: return 'low'

    def _estimate_green_space_proximity(self, landcover_data: Dict) -> bool:
        """✅ 실제 토지피복도 데이터 기반으로 주변 녹지 여부 판단"""
        land_use = landcover_data.get('landcover_type', 'urban')
        vegetation_ratio = landcover_data.get('vegetation_ratio', 0.0)
        
        # 식생 비율이 30% 이상이거나, 토지 자체가 농지/초지/산림인 경우 녹지가 가까운 것으로 판단
        return vegetation_ratio > 0.3 or land_use in ['agricultural', 'grassland', 'forest']

    def _estimate_building_orientation(self, lat: float, lon: float) -> str:
        # ... (이전과 동일, 생략)
        if lat > 37.5: return 'north'
        elif lat > 35: return 'mixed'
        else: return 'south'

    def _classify_uhi_risk(self, landcover_data: Dict) -> str:
        """✅ 실제 토지피복도 데이터 기반으로 열섬 위험 분류"""
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use in ['commercial', 'industrial']:
            return 'high'
        elif land_use == 'residential':
            return 'medium'
        else:
            return 'low'

    def _calculate_forest_distance(self, landcover_data: Dict) -> float:
        """✅ 실제 토지피복도 데이터 기반으로 산림 거리 계산"""
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use == 'forest':
            return 0  # 산림 내부에 위치
        # 향후 shapefile 기반 실제 거리 계산으로 대체 가능
        elif land_use == 'agricultural':
            return 300
        elif land_use == 'grassland':
            return 500
        elif land_use == 'residential':
            return 1500
        else:
            return 2000

    def _get_vegetation_type(self, landcover_data: Dict) -> str:
        """✅ 실제 토지피복도 데이터 기반으로 주변 식생 유형 분류"""
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use == 'forest':
            return 'dense_forest'
        elif land_use == 'grassland':
            return 'grassland'
        elif land_use == 'agricultural':
            return 'cultivated'
        else:
            return 'urban'

    def _calculate_slope_from_dem(self, data: Dict) -> float:
        # ... (이전과 동일, DEM 고도화 전까지 유지)
        elevation = data.get('elevation_m', 0)
        if elevation < 100: return 2
        elif elevation < 300: return 8
        elif elevation < 500: return 15
        else: return 25

    def _classify_water_dependency(self, data: Dict) -> str:
        # ... (이전과 동일, 생략)
        building_purpose = data.get('main_purpose', '주택')
        if any(keyword in building_purpose for keyword in ['공장', '제조', '냉각', '세차', '목욕', '발전']): return 'high'
        elif any(keyword in building_purpose for keyword in ['업무', '상업', '판매']): return 'medium'
        else: return 'low'

    def _estimate_water_storage(self, data: Dict) -> str:
        # ... (이전과 동일, 생략)
        ground_floors = data.get('ground_floors', 3)
        if ground_floors > 10: return 'large'
        elif ground_floors > 5: return 'medium'
        else: return 'limited'

    def _calculate_coastal_distance_score(self, distance_m: float) -> int:
        # ... (이전과 동일, 생략)
        thresholds = config.SEA_LEVEL_RISE_EXPOSURE_SCORES
        if distance_m < thresholds['critical']['distance_m']: return thresholds['critical']['score']
        elif distance_m < thresholds['high']['distance_m']: return thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return thresholds['medium']['score']
        else: return thresholds['low']['score']

    def _classify_coastal_exposure_level(self, distance_m: float) -> str:
        # ... (이전과 동일, 생략)
        thresholds = config.SEA_LEVEL_RISE_EXPOSURE_SCORES
        if distance_m < thresholds['critical']['distance_m']: return 'critical'
        elif distance_m < thresholds['high']['distance_m']: return 'high'
        elif distance_m < thresholds['medium']['distance_m']: return 'medium'
        else: return 'low'

    def _estimate_impervious_surface_ratio(self, landcover_data: Dict) -> float:
        """✅ 실제 토지피복도 데이터 기반으로 불투수면 비율 추정"""
        return landcover_data.get('impervious_ratio', 0.6)

    def _estimate_drainage_capacity(self, data: Dict) -> str:
        # ... (이전과 동일, 생략)
        build_year = data.get('build_year')
        current_year = 2025
        if build_year is None: return 'standard'
        building_age = current_year - build_year
        if building_age < 10: return 'good'
        elif building_age < 30: return 'standard'
        else: return 'poor'

    def _calculate_urban_flood_exposure_score(self, data: Dict) -> tuple:
        # ... (이전과 동일, 생략)
        building_type = data.get('building_type', config.DEFAULT_BUILDING_PROPERTIES['building_type'])
        if '업무' in building_type or '상업' in building_type: return 'high', 80, 85
        elif '주택' in building_type or '아파트' in building_type: return 'medium', 50, 65
        else: return 'low', 20, 35

    def _calculate_wildfire_exposure_score(self, distance_m: float) -> tuple:
        # ... (이전과 동일, 생략)
        thresholds = config.WILDFIRE_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return 'very_high', thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']: return 'high', thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return 'medium', thresholds['medium']['score']
        else: return 'low', thresholds['low']['score']

    def _calculate_river_flood_exposure_score(self, distance_m: float) -> tuple:
        # ... (이전과 동일, 생략)
        thresholds = config.RIVER_FLOOD_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return 'very_high', thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']: return 'high', thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return 'medium', thresholds['medium']['score']
        else: return 'low', thresholds['low']['score']

    def _calculate_drought_exposure_score(self, water_dependency: str, annual_rainfall_mm: float) -> int:
        # ... (이전과 동일, 생략)
        if water_dependency == 'high': score = 80
        elif water_dependency == 'medium': score = 50
        else: score = 30
        if annual_rainfall_mm < 1000: score += 10
        return score

    def _calculate_typhoon_distance_score(self, distance_m: float) -> int:
        # ... (이전과 동일, 생략)
        thresholds = config.TYPHOON_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']: return thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return thresholds['medium']['score']
        else: return thresholds['low']['score']

    def _classify_typhoon_exposure_level(self, distance_m: float) -> str:
        # ... (이전과 동일, 생략)
        thresholds = config.TYPHOON_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return 'critical'
        elif distance_m < thresholds['high']['distance_m']: return 'high'
        elif distance_m < thresholds['medium']['distance_m']: return 'medium'
        else: return 'low'

    def _assess_data_quality(self, data: Dict) -> str:
        # ... (이전과 동일, 생략)
        required_fields = ['ground_floors', 'building_type', 'distance_to_river_m', 'distance_to_coast_m', 'elevation_m']
        available = sum(1 for field in required_fields if field in data and data[field] is not None)
        ratio = available / len(required_fields)
        if ratio >= 0.9: return 'high'
        elif ratio >= 0.7: return 'medium'
        else: return 'low'

    def _print_summary(self, exposure: Dict):
        # ... (이전과 동일, 생략)
        print(f"\n📍 위치:")
        print(f"   위경도: ({exposure['location']['latitude']}, {exposure['location']['longitude']})")
        print(f"   고도: {exposure['location']['elevation_m']}m")
        print(f"   토지이용: {exposure['location']['land_use']}")
        print(f"\n🏢 건물:")
        print(f"   용도: {exposure['building']['main_purpose']}")
        print(f"   층수: 지상{exposure['building']['floors_above']}층 / 지하{exposure['building']['floors_below']}층")
        print(f"   구조: {exposure['building']['structure']}")
        print(f"   건축연도: {exposure['building']['build_year']}년 (노후도: {exposure['building']['building_age']}년)")
        print(f"\n🌊 홍수 노출도:")
        print(f"   하천거리: {exposure['flood_exposure']['distance_to_river_m']}m")
        print(f"   해안거리: {exposure['flood_exposure']['distance_to_coast_m']}m")
        print(f"   홍수위험구역: {'예' if exposure['flood_exposure']['in_flood_zone'] else '아니오'}")
        print(f"\n📊 데이터 품질: {exposure['metadata']['data_quality']}")


if __name__ == "__main__":
    # 테스트
    calculator = ExposureCalculator()
    # ... (이후 테스트 코드는 이전과 동일, 생략)
    print("\n" + "="*80)
    print("테스트 1: 좌표 입력")
    result1 = calculator.calculate((37.5172, 127.0473))
    print("\n" + "="*80)
    print("테스트 2: 주소 입력")
    result2 = calculator.calculate("대전광역시 유성구 원촌동 140-1")
