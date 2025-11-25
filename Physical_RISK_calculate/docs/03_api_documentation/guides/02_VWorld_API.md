# V-World (브이월드) API 가이드

## 개요

국토교통부에서 제공하는 V-World 공간정보 플랫폼 Open API입니다.

**API 키**: `.env` 파일의 `VWORLD_API_KEY` 참조

---

## 1. 하천망 데이터 API

### 기본 정보

- **제공기관**: 국토교통부
- **서비스명**: V-World 공간정보 API
- **링크**: https://www.vworld.kr/dev
- **응답형식**: JSON/GeoJSON

### 용도

- 내륙홍수 위해성 평가 (사업장-하천 거리 계산)
- 하천 근접도 분석

### API 엔드포인트

```
https://api.vworld.kr/req/data
```

### 요청 파라미터 (하천망 조회)

| 파라미터   | 타입    | 필수 | 설명               | 예시                    |
| ---------- | ------- | ---- | ------------------ | ----------------------- |
| service    | String  | O    | 서비스 유형        | data                    |
| request    | String  | O    | 요청 유형          | GetFeature              |
| data       | String  | O    | 레이어명           | LT_C_WKMSTRM (하천망)   |
| key        | String  | O    | API 키             | -                       |
| domain     | String  | O    | 도메인             | http://localhost        |
| geomFilter | String  | X    | 공간 필터          | POINT(126.9780 37.5665) |
| buffer     | Integer | X    | 검색반경(m)        | 5000                    |
| size       | Integer | X    | 결과 개수          | 10                      |
| format     | String  | X    | 응답형식           | json                    |
| geometry   | Boolean | X    | 도형정보 포함 여부 | true                    |
| attribute  | Boolean | X    | 속성정보 포함 여부 | true                    |

### 응답 예시 (정상)

```json
{
  "response": {
    "service": {
      "name": "data",
      "version": "2.0",
      "operation": "GetFeature"
    },
    "status": "OK",
    "result": {
      "featureCollection": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "geometry": {
              "type": "LineString",
              "coordinates": [
                [126.98, 37.57],
                [126.99, 37.58]
              ]
            },
            "properties": {
              "flw_nm": "한강",
              "flw_grd_nm": "대하천",
              "flw_len": "12345.67"
            }
          }
        ]
      }
    }
  }
}
```

### 주요 레이어

| 레이어명          | 설명        | 용도             |
| ----------------- | ----------- | ---------------- |
| LT_C_WKMSTRM      | 하천망      | 홍수 위해성 평가 |
| LT_C_ADSIGG_INFO  | 시군구 경계 | 행정구역 분석    |
| lt_l_toisdepcntah | 해안선      | 해안홍수 노출도  |

### Python 예제 (하천망 조회)

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('VWORLD_API_KEY')

url = "https://api.vworld.kr/req/data"

params = {
    'service': 'data',
    'request': 'GetFeature',
    'data': 'LT_C_WKMSTRM',  # 하천망
    'key': API_KEY,
    'domain': 'http://localhost',
    'geomFilter': 'POINT(126.9780 37.5665)',  # 서울시청
    'buffer': '5000',  # 5km 반경
    'size': '10',
    'format': 'json',
    'geometry': 'true',
    'attribute': 'true'
}

response = requests.get(url, params=params)
data = response.json()

if data['response']['status'] == 'OK':
    features = data['response']['result']['featureCollection']['features']
    for feature in features:
        props = feature['properties']
        print(f"하천명: {props.get('flw_nm')}, 등급: {props.get('flw_grd_nm')}")
```

---

## 2. 행정구역 경계 API

### 요청 파라미터 (시군구 조회)

| 파라미터   | 타입    | 필수 | 설명        | 예시                   |
| ---------- | ------- | ---- | ----------- | ---------------------- |
| service    | String  | O    | 서비스 유형 | data                   |
| request    | String  | O    | 요청 유형   | GetFeature             |
| data       | String  | O    | 레이어명    | LT_C_ADSIGG_INFO       |
| key        | String  | O    | API 키      | -                      |
| domain     | String  | O    | 도메인      | http://localhost       |
| attrFilter | String  | X    | 속성 필터   | sig_kor_nm:like:종로구 |
| size       | Integer | X    | 결과 개수   | 10                     |
| format     | String  | X    | 응답형식    | json                   |

### Python 예제 (행정구역 조회)

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('VWORLD_API_KEY')

url = "https://api.vworld.kr/req/data"

params = {
    'service': 'data',
    'request': 'GetFeature',
    'data': 'LT_C_ADSIGG_INFO',
    'key': API_KEY,
    'domain': 'http://localhost',
    'attrFilter': 'sig_kor_nm:like:종로구',
    'size': '5',
    'format': 'json',
    'geometry': 'false',
    'attribute': 'true'
}

response = requests.get(url, params=params)
data = response.json()
```

---

## 3. Geocoding API (주소 검색)

### 기본 정보

- **용도**: 주소를 좌표로 변환, 좌표를 주소로 변환
- **서비스**: address

### API 엔드포인트

```
https://api.vworld.kr/req/address
```

### 요청 파라미터 (주소→좌표)

| 파라미터 | 타입    | 필수 | 설명        | 예시                                  |
| -------- | ------- | ---- | ----------- | ------------------------------------- |
| service  | String  | O    | 서비스 유형 | address                               |
| request  | String  | O    | 요청 유형   | getcoord                              |
| key      | String  | O    | API 키      | -                                     |
| address  | String  | O    | 검색할 주소 | 서울특별시 종로구 세종대로 110        |
| format   | String  | X    | 응답형식    | json                                  |
| type     | String  | X    | 주소 유형   | road (도로명주소) / parcel (지번주소) |
| simple   | Boolean | X    | 간략 응답   | false                                 |

### 응답 예시

```json
{
  "response": {
    "service": {
      "name": "address",
      "version": "2.0",
      "operation": "getcoord"
    },
    "status": "OK",
    "result": {
      "point": {
        "x": "126.9780141",
        "y": "37.5662952"
      },
      "text": "서울특별시 종로구 세종대로 110"
    }
  }
}
```

### Python 예제 (Geocoding)

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('VWORLD_API_KEY')

url = "https://api.vworld.kr/req/address"

params = {
    'service': 'address',
    'request': 'getcoord',
    'key': API_KEY,
    'address': '서울특별시 종로구 세종대로 110',
    'format': 'json',
    'type': 'road'
}

response = requests.get(url, params=params)
data = response.json()

if data['response']['status'] == 'OK':
    point = data['response']['result']['point']
    print(f"좌표: ({point['x']}, {point['y']})")
```

---

## 4. WMS 지도 이미지 API

### 기본 정보

- **용도**: 정적 지도 이미지 생성
- **서비스**: WMS (Web Map Service)

### API 엔드포인트

```
https://api.vworld.kr/req/wms
```

### 요청 파라미터

| 파라미터 | 타입    | 필수 | 설명        | 예시                  |
| -------- | ------- | ---- | ----------- | --------------------- |
| service  | String  | O    | 서비스 유형 | WMS                   |
| request  | String  | O    | 요청 유형   | GetMap                |
| version  | String  | O    | WMS 버전    | 1.3.0                 |
| layers   | String  | O    | 레이어명    | lt_c_wkmstrm          |
| key      | String  | O    | API 키      | -                     |
| domain   | String  | O    | 도메인      | http://localhost      |
| crs      | String  | O    | 좌표계      | EPSG:4326             |
| bbox     | String  | O    | 경계 영역   | 126.9,37.5,127.0,37.6 |
| width    | Integer | O    | 이미지 너비 | 512                   |
| height   | Integer | O    | 이미지 높이 | 512                   |
| format   | String  | O    | 이미지 포맷 | image/png             |

---

## 테스트 결과

### API 키 인증 문제

⚠️ **현재 .env의 VWORLD_API_KEY로는 인증 오류 발생**

```
"error": {
  "code": "INCORRECT_KEY",
  "text": "인증키 정보가 올바르지 않습니다."
}
```

### 해결 방법

1. **V-World 개발자센터에서 API 키 재발급**

   - https://www.vworld.kr/dev/v4dv_apikey2_s001.do
   - 도메인 등록 필요 (예: localhost, 실제 도메인)

2. **문서에 언급된 다른 API 키 시도**

   - `14A52498-DB87-3CF4-91D4-D31039BC603F`
   - `961911EC-A96C-3B0E-AE0D-15B8E47EDF59`

3. **API 키 활성화 확인**
   - V-World 개발자센터에서 키 상태 확인
   - 트래픽 제한 확인

---

## 참고사항

### 좌표계

- **EPSG:4326**: WGS84 경위도 좌표계 (일반적으로 사용)
- **EPSG:3857**: Web Mercator (웹 지도 서비스)
- **EPSG:5179**: UTM-K (한국 중부원점)

### 공간 필터 형식

- **POINT**: `POINT(경도 위도)`
- **BBOX**: `BBOX(minX, minY, maxX, maxY)`
- **POLYGON**: `POLYGON((x1 y1, x2 y2, ...))`

### 속성 필터 예시

- **같음**: `필드명:=:값`
- **포함**: `필드명:like:값`
- **범위**: `필드명:>=:값1;필드명:<=:값2`

---

## 추가 리소스

- V-World API 문서: https://www.vworld.kr/dev/v4dv_2ddataguide2_s001.do
- V-World 데이터 목록: https://www.vworld.kr/dev/v4dv_2ddatacatalog_s002.do
- 개발자센터: https://www.vworld.kr/dev
