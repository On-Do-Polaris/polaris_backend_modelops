# WAMIS 유역/하천 데이터 API

## API 개요

- **출처**: 국가수자원관리종합정보시스템 (WAMIS - Water Resources Management Information System)
- **링크**:
  - WAMIS 포털: https://wamis.go.kr
  - 지도 서비스: https://map.wamis.go.kr
  - 공공데이터포털 유역특성 API: https://data.go.kr/data/15107318/openapi.do
- **API 키**: `4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce`
- **데이터 타입**: JSON/XML, SHP
- **데이터 설명**:
  - **유역특성**: 유역면적, 유로연장, 유출곡선지수(CN), 하천등급
  - **홍수량**: 빈도별 홍수량 산정결과 (80년, 100년, 200년 빈도)
  - **용수이용**: 취수량, 용수 수요량 (생활용수, 공업용수, 농업용수)

## 사용 목적

본 프로젝트에서 WAMIS API는 다음 기후 리스크 평가에 사용됩니다:

- **내륙홍수 위해성 평가**: 하천범람 위험도, 홍수량 분석
- **물부족 위해성 평가**: 용수 취수량, 용수 수요량 분석

## API 엔드포인트

### 1. 유역특성조회 API

```
GET https://api.odcloud.kr/api/WamisBasinInfo/v1/list
```

### 2. 홍수량 조회 API

```
GET https://api.odcloud.kr/api/WamisFloodDischarge/v1/list
```

### 3. 하천정보 API (재난안전데이터)

```
GET https://www.safetydata.go.kr/V2/api/DSSP-IF-10720
```

## 요청 파라미터

### 유역특성조회 API

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 공공데이터포털 인증키 (Decoding) | `4b2f121a...` |
| `page` | Integer | X | 페이지 번호 (기본값: 1) | `1` |
| `perPage` | Integer | X | 페이지당 결과 수 (기본값: 10, 최대: 1000) | `100` |
| `대권역명` | String | X | 대권역명 필터 | `한강` |
| `중권역명` | String | X | 중권역명 필터 | `한강서해` |
| `소권역명` | String | X | 소권역명 필터 | `임진강` |
| `하천코드` | String | X | 하천코드 필터 | `1001` |

### 홍수량 조회 API

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 공공데이터포털 인증키 | `4b2f121a...` |
| `page` | Integer | X | 페이지 번호 | `1` |
| `perPage` | Integer | X | 페이지당 결과 수 | `100` |
| `산정지점명` | String | X | 산정지점명 | `팔당댐` |
| `년도` | String | X | 산정년도 | `2023` |

### 하천정보 API (재난안전데이터)

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| `serviceKey` | String | O | 서비스 키 | `B7XA41C895N96P2Z` |
| `pageNo` | Integer | X | 페이지 번호 | `1` |
| `numOfRows` | Integer | X | 한 페이지 결과 수 | `100` |
| `returnType` | String | X | 응답 형식 (json/xml) | `json` |

## 응답 데이터

### 유역특성 응답 필드

```json
{
  "page": 1,
  "perPage": 10,
  "totalCount": 150,
  "currentCount": 10,
  "matchCount": 150,
  "data": [
    {
      "대권역명": "한강",
      "중권역명": "한강서해",
      "소권역명": "임진강",
      "하천코드": "1001",
      "하천명": "임진강",
      "유역면적": "8,118.0",        // km²
      "유로연장": "254.6",          // km
      "유출곡선지수": "70.5",       // CN값
      "하천등급": "국가하천",
      "관리기관": "한강홍수통제소",
      "유역경계": "POLYGON(...)"    // GeoJSON Polygon
    }
  ]
}
```

### 홍수량 응답 필드

```json
{
  "data": [
    {
      "산정지점명": "팔당댐",
      "하천명": "한강",
      "년도": "2023",
      "빈도80년": "18,500",         // m³/s
      "빈도100년": "20,200",        // m³/s
      "빈도200년": "23,800",        // m³/s
      "유역면적": "23,292.0",       // km²
      "유로연장": "481.7",          // km
      "위도": "37.5123",
      "경도": "127.5456"
    }
  ]
}
```

### 하천정보 응답 필드 (재난안전데이터)

```json
{
  "response": {
    "body": {
      "items": [
        {
          "하천명": "한강",
          "하천관리번호": "HG-001",
          "본류": "한강",
          "하천등급코드": "1",
          "하천등급": "국가하천",
          "관리기관": "한강홍수통제소",
          "홍수용량": "25000",        // m³/s
          "하천너비": "800",          // m
          "하천연장길이": "481.7",    // km
          "유로연장내용": "481.7km",
          "유역면적": "26018.0",      // km²
          "하천위치": "LINESTRING(...)"
        }
      ]
    }
  }
}
```

## Python 사용 예시

### 1. 유역특성 조회

```python
import requests
from typing import Optional, Dict, List

def get_basin_info(
    api_key: str,
    major_basin: Optional[str] = None,
    medium_basin: Optional[str] = None,
    river_code: Optional[str] = None
) -> List[Dict]:
    """
    WAMIS 유역특성 정보를 조회합니다.

    Args:
        api_key: 공공데이터포털 API 키
        major_basin: 대권역명 (예: '한강')
        medium_basin: 중권역명 (예: '한강서해')
        river_code: 하천코드

    Returns:
        List[Dict]: 유역특성 정보 리스트
    """
    url = "https://api.odcloud.kr/api/WamisBasinInfo/v1/list"

    params = {
        "serviceKey": api_key,
        "page": 1,
        "perPage": 1000
    }

    # 선택적 필터 추가
    if major_basin:
        params["대권역명"] = major_basin
    if medium_basin:
        params["중권역명"] = medium_basin
    if river_code:
        params["하천코드"] = river_code

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get('data', [])

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []

# 사용 예시
api_key = "4b2f121a7492c996d0dca08a311bb9ae1063ae49a3ef40ed955de1f617da8bce"

# 한강 유역 조회
han_river_basins = get_basin_info(api_key, major_basin="한강")

for basin in han_river_basins:
    print(f"하천명: {basin['하천명']}")
    print(f"유역면적: {basin['유역면적']} km²")
    print(f"유로연장: {basin['유로연장']} km")
    print(f"유출곡선지수(CN): {basin['유출곡선지수']}")
    print("---")
```

### 2. 홍수량 조회

```python
def get_flood_discharge(
    api_key: str,
    location: Optional[str] = None,
    year: Optional[str] = None
) -> List[Dict]:
    """
    WAMIS 빈도별 홍수량 정보를 조회합니다.

    Args:
        api_key: 공공데이터포털 API 키
        location: 산정지점명 (예: '팔당댐')
        year: 산정년도 (예: '2023')

    Returns:
        List[Dict]: 홍수량 정보 리스트
    """
    url = "https://api.odcloud.kr/api/WamisFloodDischarge/v1/list"

    params = {
        "serviceKey": api_key,
        "page": 1,
        "perPage": 1000
    }

    if location:
        params["산정지점명"] = location
    if year:
        params["년도"] = year

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get('data', [])

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []

# 사용 예시
flood_data = get_flood_discharge(api_key, location="팔당댐", year="2023")

for item in flood_data:
    print(f"지점: {item['산정지점명']}")
    print(f"100년 빈도 홍수량: {item['빈도100년']} m³/s")
    print(f"200년 빈도 홍수량: {item['빈도200년']} m³/s")
```

### 3. 하천 근접도 계산 (내륙홍수 리스크)

```python
from shapely.geometry import Point, LineString
from shapely.wkt import loads as wkt_loads

def calculate_river_proximity(
    facility_lat: float,
    facility_lon: float,
    api_key: str,
    search_radius_km: float = 10.0
) -> Dict:
    """
    사업장과 가장 가까운 하천까지의 거리를 계산합니다.

    Args:
        facility_lat: 사업장 위도
        facility_lon: 사업장 경도
        api_key: API 키
        search_radius_km: 검색 반경 (km)

    Returns:
        Dict: 가장 가까운 하천 정보 및 거리
    """
    # 유역 정보 조회
    basins = get_basin_info(api_key)

    facility_point = Point(facility_lon, facility_lat)
    min_distance = float('inf')
    nearest_river = None

    for basin in basins:
        if 'geometry' in basin and basin['geometry']:
            try:
                # 하천 경계선 geometry 파싱
                river_geom = wkt_loads(basin['geometry'])

                # 거리 계산 (단위: degrees, 대략적 거리)
                distance = facility_point.distance(river_geom)

                # km 단위로 변환 (대략 1도 = 111km)
                distance_km = distance * 111

                if distance_km < min_distance and distance_km <= search_radius_km:
                    min_distance = distance_km
                    nearest_river = {
                        '하천명': basin['하천명'],
                        '하천등급': basin['하천등급'],
                        '거리_km': round(distance_km, 2),
                        '유역면적': basin['유역면적'],
                        '유로연장': basin['유로연장']
                    }

            except Exception as e:
                continue

    return nearest_river if nearest_river else {
        '하천명': None,
        '거리_km': None,
        '메시지': f'{search_radius_km}km 내 하천 없음'
    }

# 사용 예시
facility_lat = 37.5665  # 서울시청 위도
facility_lon = 126.9780  # 서울시청 경도

river_info = calculate_river_proximity(facility_lat, facility_lon, api_key)
print(f"가장 가까운 하천: {river_info['하천명']}")
print(f"거리: {river_info['거리_km']} km")
```

### 4. 용수 수요량 조회 (물부족 리스크)

```python
def get_water_demand(api_key: str, basin_name: str) -> Dict:
    """
    특정 유역의 용수 수요량 정보를 조회합니다.

    Args:
        api_key: API 키
        basin_name: 유역명

    Returns:
        Dict: 용수 수요량 정보 (생활용수, 공업용수, 농업용수)
    """
    # WAMIS 용수수급 API (별도 엔드포인트 필요)
    # 현재는 유역정보에서 간접적으로 추정

    basins = get_basin_info(api_key, major_basin=basin_name)

    total_demand = {
        '생활용수': 0,  # m³/day
        '공업용수': 0,  # m³/day
        '농업용수': 0,  # m³/day
        '총수요량': 0   # m³/day
    }

    # 실제 구현 시 WAMIS 용수수급 API 사용 필요
    # 현재는 placeholder

    return total_demand
```

## 프로젝트 내 사용 위치

본 API는 다음 리스크 계산 모듈에서 사용됩니다:

1. **내륙홍수 리스크** ([inland_flood_risk.py](../code/inland_flood_risk.py))
   - 하천범람 위험도 평가
   - 사업장-하천 거리 계산
   - 빈도별 홍수량 분석

2. **물부족 리스크** ([water_stress_risk.py](../code/water_stress_risk.py))
   - 용수 취수량 분석
   - 용수 수요량 추정

## 주의사항

1. **API 키 관리**: API 키는 [api_key.md](api_key.md)에 별도로 관리됩니다.
2. **데이터 갱신**: 유역특성 데이터는 연 1회 갱신되며, 최신 데이터 확인이 필요합니다.
3. **좌표계**: WAMIS 공간 데이터는 주로 EPSG:5186 (Korea 2000 / Central Belt) 좌표계를 사용합니다.
4. **하천등급**: 국가하천, 지방하천, 소하천으로 구분되며 등급에 따라 관리기관이 다릅니다.
5. **홍수량 산정**: 빈도별 홍수량은 확률강우량 기반으로 산정되며, 기후변화를 고려한 재산정이 필요할 수 있습니다.

## 주요 대권역 목록

- **한강**: 서울, 경기, 강원 일부
- **낙동강**: 부산, 대구, 경남, 경북
- **금강**: 대전, 세종, 충남, 충북
- **영산강**: 광주, 전남 일부
- **섬진강**: 전북, 전남 일부

## 참고 문서

- WAMIS 포털: https://wamis.go.kr
- WAMIS 지도 서비스: https://map.wamis.go.kr
- 공공데이터포털 유역특성 API: https://data.go.kr/data/15107318/openapi.do
- 재난안전데이터 하천정보 API: https://www.safetydata.go.kr/V2/api/DSSP-IF-10720
- 수자원 장기종합계획: http://www.molit.go.kr
