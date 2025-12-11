"""
격자 → 최근접 관측소 조회 유틸리티

사용법:
    from grid_to_station_lookup import GridToStationLookup

    lookup = GridToStationLookup()
    result = lookup.get_nearest_stations(lat=36.35, lon=127.38)

    print(result['nearest_stations'][0]['obscd'])  # 가장 가까운 관측소 코드
"""
import json
import numpy as np
from pathlib import Path

BASIN_DATA_DIR = Path(__file__).parent / 'basin_data'


class GridToStationLookup:
    """격자 → 최근접 관측소 조회 클래스"""

    def __init__(self):
        self._load_data()

    def _load_data(self):
        """데이터 로드"""
        mapping_path = BASIN_DATA_DIR / 'grid_to_nearest_stations.json'
        with open(mapping_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.grid_info = data['grid_info']
        self.grid_mapping = data['grid_mapping']
        self.k_nearest = data['k_nearest']

        print(f"데이터 로드 완료: {self.grid_info['n_land_grids']:,}개 격자")

    def get_nearest_stations(self, lat: float, lon: float) -> dict:
        """
        특정 위경도의 최근접 관측소 조회

        Args:
            lat: 위도 (33.0 ~ 39.0)
            lon: 경도 (124.5 ~ 132.0)

        Returns:
            {
                'lat': 입력 위도,
                'lon': 입력 경도,
                'grid_lat': 격자 위도,
                'grid_lon': 격자 경도,
                'basin_code': 유역 코드,
                'basin_name': 유역 이름,
                'nearest_stations': [
                    {
                        'obscd': 관측소 코드,
                        'obsnm': 관측소명,
                        'lat': 관측소 위도,
                        'lon': 관측소 경도,
                        'distance_km': 거리(km)
                    },
                    ...
                ]
            }
        """
        # 격자 인덱스 계산
        lat_min = self.grid_info['lat_min']
        lon_min = self.grid_info['lon_min']
        res = self.grid_info['resolution']

        lat_idx = round((lat - lat_min) / res)
        lon_idx = round((lon - lon_min) / res)

        # 범위 체크
        if not (0 <= lat_idx < self.grid_info['n_lat'] and
                0 <= lon_idx < self.grid_info['n_lon']):
            return {
                'lat': lat, 'lon': lon,
                'error': '범위 밖 (한국 외 지역)'
            }

        # 그리드 키로 조회
        grid_key = f"{lat_idx},{lon_idx}"

        if grid_key not in self.grid_mapping:
            return {
                'lat': lat, 'lon': lon,
                'error': '바다 또는 육지 외 지역'
            }

        grid_data = self.grid_mapping[grid_key]

        return {
            'lat': lat,
            'lon': lon,
            'grid_lat': grid_data['lat'],
            'grid_lon': grid_data['lon'],
            'basin_code': grid_data['basin_code'],
            'basin_name': grid_data['basin_name'],
            'nearest_stations': grid_data['nearest_stations']
        }


def main():
    """테스트"""
    lookup = GridToStationLookup()

    # 테스트 위치
    test_locations = [
        (36.35, 127.38, '대전'),
        (37.57, 126.98, '서울'),
        (35.18, 129.08, '부산'),
        (35.87, 128.60, '대구'),
        (33.50, 126.53, '제주'),
    ]

    print("\n" + "=" * 70)
    print("격자 → 최근접 관측소 조회 테스트")
    print("=" * 70)

    for lat, lon, name in test_locations:
        result = lookup.get_nearest_stations(lat, lon)

        if 'error' in result:
            print(f"\n{name} ({lat}, {lon})")
            print(f"  오류: {result['error']}")
            continue

        print(f"\n{name} ({lat}, {lon})")
        print(f"  유역: {result['basin_name']} (코드: {result['basin_code']})")
        print(f"  최근접 관측소:")

        for i, st in enumerate(result['nearest_stations'], 1):
            print(f"    {i}. {st['obscd']} {st['obsnm']}")
            print(f"       거리: {st['distance_km']} km")
            print(f"       좌표: ({st['lat']:.4f}, {st['lon']:.4f})")

        # WAMIS API 호출 예시
        obscd = result['nearest_stations'][0]['obscd']
        print(f"\n  → WAMIS 일유량 API 호출:")
        print(f"     obscd={obscd}&sdt=20240101&edt=20241231")


if __name__ == '__main__':
    main()
