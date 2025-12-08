'''
파일명: exposure_agent.py
설명: 노출도(Exposure) 계산 Agent
업데이트: ExposureCalculator 로직 통합 (건물 및 환경 정보 기반)
'''
from typing import Dict, Any, Optional, Tuple
import logging
try:
    from modelops.config import hazard_config as config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class ExposureAgent:
    """
    노출도 (Exposure) 계산 Agent
    
    역할:
    - 건물 정보(Building Data)와 공간 정보(Spatial Data)를 결합하여
    - 각 리스크 유형별 노출도를 평가하고 구조화된 데이터 생성
    - VulnerabilityAgent의 입력값으로 사용됨
    """

    def __init__(self):
        pass

    def calculate_exposure(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        노출도 계산

        Args:
            collected_data: 수집된 데이터 딕셔너리
                - building_data: 건물 정보
                - spatial_data: 토지피복 등 공간 정보
                - latitude, longitude: 위치

        Returns:
            Exposure 데이터 딕셔너리 (VulnerabilityAgent 입력용)
        """
        building_data = collected_data.get('building_data', {})
        spatial_data = collected_data.get('spatial_data', {})
        lat = collected_data.get('latitude', 0.0)
        lon = collected_data.get('longitude', 0.0)

        if not config:
            logger.warning("Config module not loaded. Using hardcoded defaults.")
            defaults = {}
            dist_defaults = {'distance_to_river_m': 1000, 'distance_to_coast_m': 50000}
            hydro_defaults = {'watershed_area_km2': 2500, 'stream_order': 3, 'annual_rainfall_mm': 1200}
        else:
            defaults = config.DEFAULT_BUILDING_PROPERTIES
            dist_defaults = config.DEFAULT_DISTANCE_VALUES
            hydro_defaults = config.DEFAULT_HYDROLOGICAL_VALUES

        land_use = spatial_data.get('landcover_type', 'urban')

        # Exposure 구조화
        exposure = {
            'location': {
                'latitude': lat,
                'longitude': lon,
                'elevation_m': building_data.get('elevation_m', defaults.get('elevation_m', 0)),
                'land_use': land_use,
            },
            'building': {
                'floors_above': building_data.get('ground_floors', defaults.get('ground_floors', 3)),
                'floors_below': building_data.get('basement_floors', defaults.get('basement_floors', 0)),
                'ground_floors': building_data.get('ground_floors', defaults.get('ground_floors', 3)),
                'total_area_m2': building_data.get('total_area_m2', defaults.get('total_area_m2', 0)),
                'building_type': building_data.get('building_type', defaults.get('building_type', '주택')),
                'main_purpose': building_data.get('main_purpose', defaults.get('main_purpose', '단독주택')),
                'structure': building_data.get('structure', defaults.get('structure', '철근콘크리트조')),
                'build_year': building_data.get('build_year', defaults.get('build_year', 1995)),
                'building_age': building_data.get('building_age', defaults.get('building_age', 30)),
                'has_piloti': building_data.get('has_piloti', defaults.get('has_piloti', False)),
                'has_water_tank': building_data.get('has_water_tank'),
                'water_tank_method': building_data.get('water_tank_method'),
            },
            'flood_exposure': {
                'distance_to_river_m': building_data.get('distance_to_river_m', dist_defaults['distance_to_river_m']),
                'proximity_category': self._calculate_river_flood_exposure_score(building_data.get('distance_to_river_m', dist_defaults['distance_to_river_m']))[0],
                'score': self._calculate_river_flood_exposure_score(building_data.get('distance_to_river_m', dist_defaults['distance_to_river_m']))[1],
                'distance_to_coast_m': building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']),
                'watershed_area_km2': building_data.get('watershed_area_km2', hydro_defaults['watershed_area_km2']),
                'stream_order': building_data.get('stream_order', hydro_defaults['stream_order']),
                'in_flood_zone': self._is_in_flood_zone(building_data),
            },
            'heat_exposure': {
                'urban_heat_island': self._estimate_uhi_intensity(building_data),
                'green_space_nearby': self._estimate_green_space_proximity(spatial_data),
                'building_orientation': self._estimate_building_orientation(lat, lon),
                'uhi_risk': self._classify_uhi_risk(spatial_data),
            },
            'urban_flood_exposure': {
                'urban_intensity': self._calculate_urban_flood_exposure_score(building_data)[0],
                'score': self._calculate_urban_flood_exposure_score(building_data)[1],
                'imperviousness_percent': self._calculate_urban_flood_exposure_score(building_data)[2],
                'impervious_surface_ratio': self._estimate_impervious_surface_ratio(spatial_data),
                'drainage_capacity': self._estimate_drainage_capacity(building_data),
                'urban_area': land_use in ['urban', 'commercial', 'residential', 'mixed-use', 'industrial'],
            },
            'drought_exposure': {
                'annual_rainfall_mm': building_data.get('annual_rainfall_mm', hydro_defaults['annual_rainfall_mm']),
                'water_dependency': self._classify_water_dependency(building_data),
                'score': self._calculate_drought_exposure_score(self._classify_water_dependency(building_data), building_data.get('annual_rainfall_mm', hydro_defaults['annual_rainfall_mm'])),
                'water_storage_capacity': self._estimate_water_storage(building_data),
                'backup_water_supply': building_data.get('backup_water_supply', False),
            },
            'typhoon_exposure': {
                'distance_to_coast_m': building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']),
                'coastal_exposure': building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']) < 10000,
                'coastal_distance_score': self._calculate_typhoon_distance_score(building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
                'exposure_level': self._classify_typhoon_exposure_level(building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
            },
            'sea_level_rise_exposure': {
                'distance_to_coast_m': building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m']),
                'coastal_distance_score': self._calculate_coastal_distance_score(building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
                'exposure_level': self._classify_coastal_exposure_level(building_data.get('distance_to_coast_m', dist_defaults['distance_to_coast_m'])),
            },
            'wildfire_exposure': {
                'distance_to_forest_m': self._calculate_forest_distance(spatial_data),
                'proximity_category': self._calculate_wildfire_exposure_score(self._calculate_forest_distance(spatial_data))[0],
                'score': self._calculate_wildfire_exposure_score(self._calculate_forest_distance(spatial_data))[1],
                'vegetation_type': self._get_vegetation_type(spatial_data),
                'slope_degree': self._calculate_slope_from_dem(building_data),
            },
            'metadata': {
                'data_source': 'building_data_fetcher, spatial_data_loader',
                'data_quality': self._assess_data_quality(building_data),
                'tcfd_warnings': building_data.get('tcfd_warnings', []),
            }
        }
        
        return exposure

    # --- Helper Methods ---

    def _is_in_flood_zone(self, data: Dict) -> bool:
        distance_to_river = data.get('distance_to_river_m', 1000)
        elevation = data.get('elevation_m', 50)
        return distance_to_river < 100 and elevation < 50

    def _estimate_uhi_intensity(self, data: Dict) -> str:
        building_type = data.get('building_type', '주택')
        if '업무' in building_type or '상업' in building_type: return 'high'
        elif '주택' in building_type: return 'medium'
        else: return 'low'

    def _estimate_green_space_proximity(self, landcover_data: Dict) -> bool:
        land_use = landcover_data.get('landcover_type', 'urban')
        vegetation_ratio = landcover_data.get('vegetation_ratio', 0.0)
        return vegetation_ratio > 0.3 or land_use in ['agricultural', 'grassland', 'forest']

    def _estimate_building_orientation(self, lat: float, lon: float) -> str:
        if lat > 37.5: return 'north'
        elif lat > 35: return 'mixed'
        else: return 'south'

    def _classify_uhi_risk(self, landcover_data: Dict) -> str:
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use in ['commercial', 'industrial']: return 'high'
        elif land_use == 'residential': return 'medium'
        else: return 'low'

    def _calculate_forest_distance(self, landcover_data: Dict) -> float:
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use == 'forest': return 0
        elif land_use == 'agricultural': return 300
        elif land_use == 'grassland': return 500
        elif land_use == 'residential': return 1500
        else: return 2000

    def _get_vegetation_type(self, landcover_data: Dict) -> str:
        land_use = landcover_data.get('landcover_type', 'urban')
        if land_use == 'forest': return 'dense_forest'
        elif land_use == 'grassland': return 'grassland'
        elif land_use == 'agricultural': return 'cultivated'
        else: return 'urban'

    def _calculate_slope_from_dem(self, data: Dict) -> float:
        elevation = data.get('elevation_m', 0)
        if elevation < 100: return 2
        elif elevation < 300: return 8
        elif elevation < 500: return 15
        else: return 25

    def _classify_water_dependency(self, data: Dict) -> str:
        building_purpose = data.get('main_purpose', '주택')
        if any(keyword in building_purpose for keyword in ['공장', '제조', '냉각', '세차', '목욕', '발전']): return 'high'
        elif any(keyword in building_purpose for keyword in ['업무', '상업', '판매']): return 'medium'
        else: return 'low'

    def _estimate_water_storage(self, data: Dict) -> str:
        ground_floors = data.get('ground_floors', 3)
        if ground_floors > 10: return 'large'
        elif ground_floors > 5: return 'medium'
        else: return 'limited'

    def _calculate_coastal_distance_score(self, distance_m: float) -> int:
        if not config: return 10
        thresholds = config.SEA_LEVEL_RISE_EXPOSURE_SCORES
        if distance_m < thresholds['critical']['distance_m']: return thresholds['critical']['score']
        elif distance_m < thresholds['high']['distance_m']: return thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return thresholds['medium']['score']
        else: return thresholds['low']['score']

    def _classify_coastal_exposure_level(self, distance_m: float) -> str:
        if not config: return 'low'
        thresholds = config.SEA_LEVEL_RISE_EXPOSURE_SCORES
        if distance_m < thresholds['critical']['distance_m']: return 'critical'
        elif distance_m < thresholds['high']['distance_m']: return 'high'
        elif distance_m < thresholds['medium']['distance_m']: return 'medium'
        else: return 'low'

    def _estimate_impervious_surface_ratio(self, landcover_data: Dict) -> float:
        return landcover_data.get('impervious_ratio', 0.6)

    def _estimate_drainage_capacity(self, data: Dict) -> str:
        build_year = data.get('build_year')
        current_year = 2025
        if build_year is None: return 'standard'
        building_age = current_year - build_year
        if building_age < 10: return 'good'
        elif building_age < 30: return 'standard'
        else: return 'poor'

    def _calculate_urban_flood_exposure_score(self, data: Dict) -> tuple:
        # (risk_level, score, percent)
        if not config: return 'low', 20, 35
        building_type = data.get('building_type', '주택')
        if '업무' in building_type or '상업' in building_type: return 'high', 80, 85
        elif '주택' in building_type or '아파트' in building_type: return 'medium', 50, 65
        else: return 'low', 20, 35

    def _calculate_wildfire_exposure_score(self, distance_m: float) -> tuple:
        if not config: return 'low', 10
        thresholds = config.WILDFIRE_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return 'very_high', thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']: return 'high', thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return 'medium', thresholds['medium']['score']
        else: return 'low', thresholds['low']['score']

    def _calculate_river_flood_exposure_score(self, distance_m: float) -> tuple:
        if not config: return 'low', 10
        thresholds = config.RIVER_FLOOD_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return 'very_high', thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']: return 'high', thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return 'medium', thresholds['medium']['score']
        else: return 'low', thresholds['low']['score']

    def _calculate_drought_exposure_score(self, water_dependency: str, annual_rainfall_mm: float) -> int:
        if water_dependency == 'high': score = 80
        elif water_dependency == 'medium': score = 50
        else: score = 30
        if annual_rainfall_mm < 1000: score += 10
        return score

    def _calculate_typhoon_distance_score(self, distance_m: float) -> int:
        if not config: return 10
        thresholds = config.TYPHOON_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return thresholds['very_high']['score']
        elif distance_m < thresholds['high']['distance_m']: return thresholds['high']['score']
        elif distance_m < thresholds['medium']['distance_m']: return thresholds['medium']['score']
        else: return thresholds['low']['score']

    def _classify_typhoon_exposure_level(self, distance_m: float) -> str:
        if not config: return 'low'
        thresholds = config.TYPHOON_EXPOSURE_SCORES
        if distance_m < thresholds['very_high']['distance_m']: return 'critical'
        elif distance_m < thresholds['high']['distance_m']: return 'high'
        elif distance_m < thresholds['medium']['distance_m']: return 'medium'
        else: return 'low'

    def _assess_data_quality(self, data: Dict) -> str:
        required_fields = ['ground_floors', 'building_type', 'distance_to_river_m', 'distance_to_coast_m', 'elevation_m']
        available = sum(1 for field in required_fields if field in data and data[field] is not None)
        ratio = available / len(required_fields)
        if ratio >= 0.9: return 'high'
        elif ratio >= 0.7: return 'medium'
        else: return 'low'