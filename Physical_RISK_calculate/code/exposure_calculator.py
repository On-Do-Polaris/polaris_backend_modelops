#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exposure Calculator (E)
노출도 계산: 건물이 재난에 노출되어 있는가?
"""

from typing import Dict, Union, Tuple
from building_data_fetcher import BuildingDataFetcher


class ExposureCalculator:
    """
    노출도(Exposure) 계산기

    입력: 위/경도 또는 주소
    출력: 건물 위치, 특성, 인프라 정보

    노출도 정의:
    - 건물이 특정 재난에 얼마나 노출되어 있는가?
    - 예: 하천까지 거리, 해안까지 거리, 고도, 토지이용
    """

    def __init__(self):
        self.fetcher = BuildingDataFetcher()

    def calculate(self, location: Union[str, Tuple[float, float]]) -> Dict:
        """
        위/경도 또는 주소 → 노출도 데이터

        Args:
            location: 주소(str) 또는 (lat, lon) 튜플

        Returns:
            노출도 데이터 딕셔너리
        """
        # 주소 → 좌표 변환
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

        # 노출도 구조화
        exposure = self._structure_exposure_data(raw_data, lat, lon)

        print(f"\n✅ 노출도 계산 완료")
        self._print_summary(exposure)

        return exposure

    def _structure_exposure_data(self, raw_data: Dict, lat: float, lon: float) -> Dict:
        """
        building_data_fetcher 결과 → 노출도 구조화
        """
        return {
            # ============ 위치 정보 ============
            'location': {
                'latitude': lat,
                'longitude': lon,
                'elevation_m': raw_data.get('elevation_m', 0),
                'land_use': self._classify_land_use(raw_data),
            },

            # ============ 건물 기본 정보 ============
            'building': {
                'floors_above': raw_data.get('ground_floors', 3),
                'floors_below': raw_data.get('basement_floors', 0),
                'building_type': raw_data.get('building_type', '주택'),
                'main_purpose': raw_data.get('main_purpose', '단독주택'),
                'structure': raw_data.get('structure', '철근콘크리트조'),
                'build_year': raw_data.get('build_year', 1995),
                'building_age': raw_data.get('building_age', 30),
                'has_piloti': raw_data.get('has_piloti', False),
            },

            # ============ 재난별 노출도 ============
            'flood_exposure': {
                'distance_to_river_m': raw_data.get('distance_to_river_m', 1000),
                'distance_to_coast_m': raw_data.get('distance_to_coast_m', 50000),
                'watershed_area_km2': raw_data.get('watershed_area_km2', 2500),
                'stream_order': raw_data.get('stream_order', 3),
                'in_flood_zone': self._is_in_flood_zone(raw_data),
            },

            'heat_exposure': {
                'urban_heat_island': self._estimate_uhi_intensity(raw_data),
                'green_space_nearby': False,  # TODO: 녹지 데이터
                'building_orientation': 'unknown',  # TODO: 방위 데이터
            },

            'typhoon_exposure': {
                'distance_to_coast_m': raw_data.get('distance_to_coast_m', 50000),
                'coastal_exposure': raw_data.get('distance_to_coast_m', 50000) < 10000,
                'terrain_shelter': self._estimate_terrain_shelter(raw_data),
            },

            'wildfire_exposure': {
                'distance_to_forest_m': 5000,  # TODO: 산림 거리 데이터
                'vegetation_type': 'urban',
                'slope_degree': 0,  # TODO: 경사도 데이터
            },

            # ============ 인프라 접근성 ============
            'infrastructure': {
                'nearest_fire_station_m': 2000,  # TODO: 소방서 거리
                'nearest_hospital_m': 3000,  # TODO: 병원 거리
                'water_supply_available': True,
                'drainage_system': 'standard',
                'emergency_shelter_nearby': False,
            },

            # ============ 메타데이터 ============
            'metadata': {
                'data_source': 'building_data_fetcher',
                'data_quality': self._assess_data_quality(raw_data),
                'tcfd_warnings': raw_data.get('tcfd_warnings', []),
            }
        }

    def _address_to_coords(self, address: str) -> Tuple[float, float]:
        """주소 → 좌표 변환 (V-World API 사용)"""
        import os
        import requests
        from dotenv import load_dotenv
        from pathlib import Path

        BASE_DIR = Path(__file__).parent.parent
        load_dotenv(BASE_DIR / ".env")

        VWORLD_KEY = os.getenv("VWORLD_API_KEY")

        url = "https://api.vworld.kr/req/address"

        # 도로명 주소 먼저 시도
        for address_type in ['ROAD', 'PARCEL']:
            params = {
                'service': 'address',
                'request': 'getcoord',
                'format': 'json',
                'crs': 'epsg:4326',
                'address': address,
                'type': address_type,
                'key': VWORLD_KEY
            }

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

    def _classify_land_use(self, data: Dict) -> str:
        """토지 이용 분류"""
        building_type = data.get('building_type', '주택')

        if '업무' in building_type or '사무' in building_type:
            return 'commercial'
        elif '공장' in building_type or '창고' in building_type:
            return 'industrial'
        elif '주택' in building_type or '아파트' in building_type:
            return 'residential'
        else:
            return 'mixed'

    def _is_in_flood_zone(self, data: Dict) -> bool:
        """홍수 위험 구역 여부"""
        distance_to_river = data.get('distance_to_river_m', 1000)
        elevation = data.get('elevation_m', 50)

        # 하천 100m 이내 & 저지대(50m 이하)
        return distance_to_river < 100 and elevation < 50

    def _estimate_uhi_intensity(self, data: Dict) -> str:
        """도시 열섬 강도 추정"""
        building_type = data.get('building_type', '주택')

        if '업무' in building_type or '상업' in building_type:
            return 'high'
        elif '주택' in building_type:
            return 'medium'
        else:
            return 'low'

    def _estimate_terrain_shelter(self, data: Dict) -> str:
        """지형 차폐 효과 추정"""
        # TODO: DEM 데이터로 주변 지형 분석
        return 'medium'

    def _assess_data_quality(self, data: Dict) -> str:
        """데이터 품질 평가"""
        # 필수 데이터 확인
        required_fields = [
            'ground_floors', 'building_type', 'distance_to_river_m',
            'distance_to_coast_m', 'elevation_m'
        ]

        available = sum(1 for field in required_fields if field in data and data[field] is not None)
        ratio = available / len(required_fields)

        if ratio >= 0.9:
            return 'high'
        elif ratio >= 0.7:
            return 'medium'
        else:
            return 'low'

    def _print_summary(self, exposure: Dict):
        """노출도 요약 출력"""
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

    # 테스트 1: 좌표
    print("\n" + "="*80)
    print("테스트 1: 좌표 입력")
    result1 = calculator.calculate((37.5172, 127.0473))

    # 테스트 2: 주소
    print("\n" + "="*80)
    print("테스트 2: 주소 입력")
    result2 = calculator.calculate("대전광역시 유성구 원촌동 140-1")
