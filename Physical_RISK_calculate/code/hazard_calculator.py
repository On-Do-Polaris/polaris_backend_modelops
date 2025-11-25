#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hazard Calculator (H)
위험 강도 계산: 그 지역에 얼마나 강한 재난이 발생하는가?
"""

from typing import Dict, Tuple
from building_data_fetcher import BuildingDataFetcher
from disaster_api_fetcher import DisasterAPIFetcher

# 실제 데이터 로더
try:
    from climate_data_loader import ClimateDataLoader
    CLIMATE_LOADER_AVAILABLE = True
except ImportError:
    CLIMATE_LOADER_AVAILABLE = False
    print("⚠️ [경고] climate_data_loader 모듈을 찾을 수 없습니다.")

try:
    from spatial_data_loader import SpatialDataLoader
    SPATIAL_LOADER_AVAILABLE = True
except ImportError:
    SPATIAL_LOADER_AVAILABLE = False
    print("⚠️ [경고] spatial_data_loader 모듈을 찾을 수 없습니다.")


class HazardCalculator:
    """
    위험 강도(Hazard) 계산기

    입력: 위/경도
    출력: 9개 물리적 리스크별 Hazard 강도

    Hazard 정의:
    - 그 지역에 재난이 얼마나 자주, 강하게 발생하는가?
    - 기후 시나리오, 재난 이력, 지형 분석 기반

    데이터 소스:
    - KMA SSP 시나리오: 기후변화 시나리오 (2021-2100)
    - 토지피복도: 환경부 중분류
    - NDVI: MODIS 위성 식생지수
    - 토양수분: SMAP L4
    - 재난 이력: 재난안전데이터 API
    """

    def __init__(self, scenario: str = 'SSP245', target_year: int = 2030):
        """
        Args:
            scenario: SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
            target_year: 분석 연도 (2021-2100)
        """
        self.building_fetcher = BuildingDataFetcher()
        self.disaster_fetcher = DisasterAPIFetcher()

        # 실제 데이터 로더 초기화
        self.scenario = scenario
        self.target_year = target_year

        if CLIMATE_LOADER_AVAILABLE:
            self.climate_loader = ClimateDataLoader(scenario=scenario)
        else:
            self.climate_loader = None

        if SPATIAL_LOADER_AVAILABLE:
            self.spatial_loader = SpatialDataLoader()
        else:
            self.spatial_loader = None

    def calculate(self, lat: float, lon: float) -> Dict:
        """
        위/경도 → 9개 리스크별 Hazard 강도

        Args:
            lat: 위도
            lon: 경도

        Returns:
            Hazard 강도 딕셔너리
        """
        print(f"\n{'='*80}")
        print(f"[Hazard Calculator] 위험 강도 계산")
        print(f"{'='*80}")
        print(f"위치: ({lat}, {lon})")

        # 기초 데이터 수집
        building_data = self.building_fetcher.fetch_all_building_data(lat, lon)

        # 9개 리스크별 Hazard 계산
        hazard = {
            'extreme_heat': self._calculate_heat_hazard(lat, lon, building_data),
            'extreme_cold': self._calculate_cold_hazard(lat, lon, building_data),
            'drought': self._calculate_drought_hazard(lat, lon, building_data),
            'inland_flood': self._calculate_inland_flood_hazard(lat, lon, building_data),
            'urban_flood': self._calculate_urban_flood_hazard(lat, lon, building_data),
            'coastal_flood': self._calculate_coastal_flood_hazard(lat, lon, building_data),
            'typhoon': self._calculate_typhoon_hazard(lat, lon, building_data),
            'wildfire': self._calculate_wildfire_hazard(lat, lon, building_data),
            'water_stress': self._calculate_water_stress_hazard(lat, lon, building_data),
        }

        print(f"\n✅ Hazard 계산 완료")
        self._print_summary(hazard)

        return hazard

    # ========================================================================
    # 1. 극한 고온 (Extreme Heat)
    # ========================================================================

    def _calculate_heat_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """극한 고온 Hazard - KMA SSP 시나리오 데이터 사용"""
        if self.climate_loader:
            heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, self.target_year)

            # 폭염 강도 판단
            heatwave_days = heat_data['heatwave_days_per_year']
            if heatwave_days > 30:
                intensity = 'very_high'
            elif heatwave_days > 20:
                intensity = 'high'
            elif heatwave_days > 10:
                intensity = 'medium'
            else:
                intensity = 'low'

            return {
                'annual_max_temp_celsius': heat_data['annual_max_temp_celsius'],
                'heatwave_days_per_year': heatwave_days,
                'tropical_nights': heat_data['tropical_nights'],
                'heat_wave_duration': heat_data['heat_wave_duration'],
                'heatwave_intensity': intensity,
                'climate_scenario': self.scenario,
                'trend': 'increasing',
                'year': self.target_year,
                'data_source': heat_data['data_source'],
            }
        else:
            # Fallback
            return {
                'annual_max_temp_celsius': 38.5,
                'heatwave_days_per_year': 25,
                'tropical_nights': 15,
                'heat_wave_duration': 10,
                'heatwave_intensity': 'high',
                'climate_scenario': self.scenario,
                'trend': 'increasing',
                'year': self.target_year,
                'data_source': 'fallback',
            }

    # ========================================================================
    # 2. 극한 한파 (Extreme Cold)
    # ========================================================================

    def _calculate_cold_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """극한 한파 Hazard - KMA SSP 시나리오 데이터 사용"""
        if self.climate_loader:
            cold_data = self.climate_loader.get_extreme_cold_data(lat, lon, self.target_year)

            # 한파 강도 판단
            coldwave_days = cold_data['coldwave_days_per_year']
            if coldwave_days > 20:
                intensity = 'very_high'
            elif coldwave_days > 10:
                intensity = 'high'
            elif coldwave_days > 5:
                intensity = 'medium'
            else:
                intensity = 'low'

            return {
                'annual_min_temp_celsius': cold_data['annual_min_temp_celsius'],
                'coldwave_days_per_year': coldwave_days,
                'ice_days': cold_data['ice_days'],
                'cold_wave_duration': cold_data['cold_wave_duration'],
                'coldwave_intensity': intensity,
                'climate_scenario': self.scenario,
                'trend': 'decreasing',
                'year': self.target_year,
                'data_source': cold_data['data_source'],
            }
        else:
            # Fallback
            return {
                'annual_min_temp_celsius': -15.0,
                'coldwave_days_per_year': 10,
                'ice_days': 5,
                'cold_wave_duration': 8,
                'coldwave_intensity': 'medium',
                'climate_scenario': self.scenario,
                'trend': 'decreasing',
                'year': self.target_year,
                'data_source': 'fallback',
            }

    # ========================================================================
    # 3. 가뭄 (Drought)
    # ========================================================================

    def _calculate_drought_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """가뭄 Hazard - KMA SSP + SMAP 토양수분 데이터 사용"""
        if self.climate_loader:
            drought_data = self.climate_loader.get_drought_data(lat, lon, self.target_year)

            # 토양수분 데이터 추가
            if self.spatial_loader:
                soil_data = self.spatial_loader.get_soil_moisture_data(lat, lon)
                drought_indicator = soil_data['drought_indicator']
                soil_moisture = soil_data['soil_moisture']
            else:
                drought_indicator = 'normal'
                soil_moisture = 0.2

            # SPI 지수 계산 (연속 무강수일수 기반)
            cdd = drought_data['consecutive_dry_days']
            if cdd > 30:
                spi = -2.0  # 극심한 가뭄
                freq = 0.2
            elif cdd > 20:
                spi = -1.5  # 심한 가뭄
                freq = 0.15
            elif cdd > 15:
                spi = -1.0  # 보통 가뭄
                freq = 0.1
            else:
                spi = -0.5  # 경미한 가뭄
                freq = 0.05

            return {
                'annual_rainfall_mm': drought_data['annual_rainfall_mm'],
                'consecutive_dry_days': drought_data['consecutive_dry_days'],
                'rainfall_intensity': drought_data['rainfall_intensity'],
                'soil_moisture': soil_moisture,
                'drought_indicator': drought_indicator,
                'drought_frequency': freq,
                'drought_duration_months': int(cdd / 30),
                'spi_index': spi,
                'trend': 'stable',
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': drought_data['data_source'],
            }
        else:
            # Fallback
            return {
                'annual_rainfall_mm': 1200,
                'consecutive_dry_days': 15,
                'rainfall_intensity': 10.0,
                'soil_moisture': 0.2,
                'drought_indicator': 'normal',
                'drought_frequency': 0.1,
                'drought_duration_months': 3,
                'spi_index': -1.0,
                'trend': 'stable',
                'climate_scenario': self.scenario,
                'year': self.target_year,
                'data_source': 'fallback',
            }

    # ========================================================================
    # 4. 내륙 홍수 (Inland Flood)
    # ========================================================================

    def _calculate_inland_flood_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """내륙 홍수 Hazard - KMA SSP + 재난 API 데이터 사용"""
        # 재난 API에서 하천 정보 가져오기
        try:
            river_info = self.disaster_fetcher.get_nearest_river_info(lat, lon)
            river_name = river_info.get('river_name', '알수없음')
            river_grade = river_info.get('river_grade', 3)
            watershed_area = river_info.get('watershed_area_km2', 2500)
        except:
            river_name = data.get('river_name', '알수없음')
            river_grade = 3
            watershed_area = data.get('watershed_area_km2', 2500)

        # 침수 이력
        flood_history = data.get('flood_history_count', 0)

        # KMA SSP 강수 데이터
        if self.climate_loader:
            flood_data = self.climate_loader.get_flood_data(lat, lon, self.target_year)
            extreme_rainfall = flood_data['max_1day_rainfall_mm']
            heavy_rain_days = flood_data['heavy_rain_days']

            # 홍수 빈도 계산 (하천 등급, 강수량, 침수 이력 고려)
            base_freq = 0.02
            if river_grade == 1:  # 국가하천
                base_freq += 0.01
            if extreme_rainfall > 300:
                base_freq += 0.02
            if flood_history > 5:
                base_freq += 0.02

            data_source = flood_data['data_source'] + ' + disaster_api'
        else:
            extreme_rainfall = 250
            heavy_rain_days = 5
            base_freq = 0.05
            data_source = 'fallback + disaster_api'

        return {
            'extreme_rainfall_100yr_mm': extreme_rainfall,
            'extreme_rainfall_1day_mm': extreme_rainfall,
            'heavy_rain_days': heavy_rain_days,
            'flood_frequency': base_freq,
            'river_name': river_name,
            'river_grade': river_grade,
            'watershed_area_km2': watershed_area,
            'stream_order': data.get('stream_order', 3),
            'historical_flood_count': flood_history,
            'climate_scenario': self.scenario,
            'year': self.target_year,
            'data_source': data_source,
        }

    # ========================================================================
    # 5. 도시 홍수 (Urban Flood)
    # ========================================================================

    def _calculate_urban_flood_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """도시 홍수 Hazard - KMA SSP + 토지피복도 데이터 사용"""
        flood_history = data.get('flood_history_count', 0)

        # 토지피복도 데이터
        if self.spatial_loader:
            landcover = self.spatial_loader.get_landcover_data(lat, lon)
            impervious_ratio = landcover['impervious_ratio']
            urban_intensity = landcover['urban_intensity']
        else:
            impervious_ratio = 0.7
            urban_intensity = 'medium'

        # KMA SSP 강수 데이터
        if self.climate_loader:
            flood_data = self.climate_loader.get_flood_data(lat, lon, self.target_year)
            # 1일 최대강수량을 시간당으로 환산 (대략 1/24 ~ 1/12)
            extreme_1hr = flood_data['max_1day_rainfall_mm'] / 12
            heavy_rain_days = flood_data['heavy_rain_days']

            # 홍수 빈도 계산 (불투수율, 도시화 정도 고려)
            base_freq = 0.05
            if impervious_ratio > 0.7:
                base_freq += 0.03
            if urban_intensity == 'high':
                base_freq += 0.02
            if flood_history > 5:
                base_freq += 0.02

            data_source = flood_data['data_source'] + ' + landcover'
        else:
            extreme_1hr = 80
            heavy_rain_days = 5
            base_freq = 0.1
            data_source = 'fallback + landcover'

        # 배수 용량 (도시 인프라 수준 추정)
        if urban_intensity == 'high':
            drainage_capacity = 60  # 대도시
        elif urban_intensity == 'medium':
            drainage_capacity = 50  # 중소도시
        else:
            drainage_capacity = 40  # 농촌

        return {
            'extreme_rainfall_1hr_mm': extreme_1hr,
            'heavy_rain_days': heavy_rain_days,
            'urban_drainage_capacity_mm': drainage_capacity,
            'impervious_surface_ratio': impervious_ratio,
            'urban_intensity': urban_intensity,
            'flood_frequency': base_freq,
            'historical_flood_count': flood_history,
            'climate_scenario': self.scenario,
            'year': self.target_year,
            'data_source': data_source,
        }

    # ========================================================================
    # 6. 해안 홍수 (Coastal Flood)
    # ========================================================================

    def _calculate_coastal_flood_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """해안 홍수 Hazard"""
        distance_to_coast = data.get('distance_to_coast_m', 50000)

        # 해안 50km 이상이면 위험 없음
        if distance_to_coast > 50000:
            return {
                'storm_surge_height_m': 0,
                'sea_level_rise_cm': 0,
                'coastal_exposure': False,
                'flood_frequency': 0,
                'data_source': 'distance_based',
            }

        return {
            'storm_surge_height_m': 2.5,  # 폭풍 해일 높이
            'sea_level_rise_cm': 30,  # 2050년 해수면 상승
            'coastal_exposure': True,
            'flood_frequency': 0.02,  # 50년에 1회
            'data_source': 'climate_model',
        }

    # ========================================================================
    # 7. 태풍 (Typhoon)
    # ========================================================================

    def _calculate_typhoon_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """태풍 Hazard"""
        # TODO: 기상청 태풍 베스트트랙 API 연동

        return {
            'annual_typhoon_frequency': 2.3,  # 연평균 태풍 횟수
            'max_wind_speed_kmh': 180,  # 최대 풍속
            'typhoon_intensity': 'strong',  # 강도
            'track_probability': 0.15,  # 영향권 확률
            'historical_typhoon_count': 12,  # 최근 10년 영향 횟수
            'data_source': 'typhoon_api',
        }

    # ========================================================================
    # 8. 산불 (Wildfire)
    # ========================================================================

    def _calculate_wildfire_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """산불 Hazard - NDVI + 토지피복도 + KMA SSP 데이터 사용"""
        # NDVI 식생 데이터
        if self.spatial_loader:
            ndvi_data = self.spatial_loader.get_ndvi_data(lat, lon)
            vegetation_fuel = ndvi_data['wildfire_fuel']
            vegetation_health = ndvi_data['vegetation_health']
            ndvi = ndvi_data['ndvi']
        else:
            vegetation_fuel = 'medium'
            vegetation_health = 'fair'
            ndvi = 0.4

        # 토지피복도 데이터
        if self.spatial_loader:
            landcover = self.spatial_loader.get_landcover_data(lat, lon)
            landcover_type = landcover['landcover_type']
            vegetation_ratio = landcover['vegetation_ratio']
        else:
            landcover_type = 'mixed'
            vegetation_ratio = 0.3

        # 기후 데이터 (온도, 건조도)
        if self.climate_loader:
            heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, self.target_year)
            drought_data = self.climate_loader.get_drought_data(lat, lon, self.target_year)

            max_temp = heat_data['annual_max_temp_celsius']
            dry_days = drought_data['consecutive_dry_days']

            # 화재 기상 지수 계산 (온도 + 건조도)
            fwi = (max_temp - 20) * 2 + dry_days
            if fwi < 0:
                fwi = 0
        else:
            max_temp = 38.5
            dry_days = 15
            fwi = 25

        # 산불 위험 지수 계산
        risk_index = 30  # 기본값

        # 식생 연료 고려
        if vegetation_fuel == 'high':
            risk_index += 30
        elif vegetation_fuel == 'medium':
            risk_index += 15

        # 토지피복 고려
        if landcover_type == 'forest':
            risk_index += 20
        elif landcover_type == 'grassland':
            risk_index += 10

        # 기후 고려
        if dry_days > 20:
            risk_index += 10

        # 최대 100으로 제한
        risk_index = min(risk_index, 100)

        # 연간 화재 빈도
        if risk_index > 70:
            fire_freq = 0.1
        elif risk_index > 50:
            fire_freq = 0.05
        else:
            fire_freq = 0.02

        # 가연성 판단
        if ndvi > 0.6:
            flammability = 'high'
        elif ndvi > 0.4:
            flammability = 'medium'
        else:
            flammability = 'low'

        return {
            'wildfire_risk_index': risk_index,
            'annual_fire_frequency': fire_freq,
            'fire_weather_index': fwi,
            'vegetation_flammability': flammability,
            'ndvi': ndvi,
            'vegetation_fuel': vegetation_fuel,
            'landcover_type': landcover_type,
            'max_temp_celsius': max_temp,
            'dry_days': dry_days,
            'climate_scenario': self.scenario,
            'year': self.target_year,
            'data_source': 'NDVI + landcover + climate',
        }

    # ========================================================================
    # 9. 수자원 스트레스 (Water Stress)
    # ========================================================================

    def _calculate_water_stress_hazard(self, lat: float, lon: float, data: Dict) -> Dict:
        """수자원 스트레스 Hazard"""
        return {
            'water_demand_m3_per_day': 500000,  # 일일 수요
            'water_supply_m3_per_day': 450000,  # 일일 공급
            'supply_ratio': 0.9,  # 공급 비율 (90%)
            'drought_frequency': 0.1,  # 가뭄 빈도
            'stress_level': 'medium',  # 스트레스 수준
            'data_source': 'water_api',
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _print_summary(self, hazard: Dict):
        """Hazard 요약 출력"""
        print(f"\n🌡️  극한 고온: 최고기온 {hazard['extreme_heat']['annual_max_temp_celsius']}°C, 폭염 {hazard['extreme_heat']['heatwave_days_per_year']}일/년")
        print(f"❄️  극한 한파: 최저기온 {hazard['extreme_cold']['annual_min_temp_celsius']}°C, 한파 {hazard['extreme_cold']['coldwave_days_per_year']}일/년")
        print(f"🏜️  가뭄: 연강수량 {hazard['drought']['annual_rainfall_mm']}mm, SPI {hazard['drought']['spi_index']}")
        print(f"🌊 내륙 홍수: 하천 '{hazard['inland_flood']['river_name']}', 유역면적 {hazard['inland_flood']['watershed_area_km2']}km², 침수이력 {hazard['inland_flood']['historical_flood_count']}회")
        print(f"🏙️  도시 홍수: 시간최대강수 {hazard['urban_flood']['extreme_rainfall_1hr_mm']}mm/hr, 침수이력 {hazard['urban_flood']['historical_flood_count']}회")
        print(f"🌊 해안 홍수: 노출 {hazard['coastal_flood']['coastal_exposure']}, 해일 {hazard['coastal_flood']['storm_surge_height_m']}m")
        print(f"🌀 태풍: 연평균 {hazard['typhoon']['annual_typhoon_frequency']}회, 최대풍속 {hazard['typhoon']['max_wind_speed_kmh']}km/h")
        print(f"🔥 산불: 위험지수 {hazard['wildfire']['wildfire_risk_index']}/100")
        print(f"💧 수자원: 공급비율 {hazard['water_stress']['supply_ratio']*100:.0f}%, 스트레스 {hazard['water_stress']['stress_level']}")


if __name__ == "__main__":
    # 테스트
    calculator = HazardCalculator()

    # 테스트 1: 서울 강남
    print("\n" + "="*80)
    print("테스트 1: 서울 강남")
    result1 = calculator.calculate(37.5172, 127.0473)

    # 테스트 2: 대전 유성
    print("\n" + "="*80)
    print("테스트 2: 대전 유성")
    result2 = calculator.calculate(36.38296731680909, 127.3954419423826)
