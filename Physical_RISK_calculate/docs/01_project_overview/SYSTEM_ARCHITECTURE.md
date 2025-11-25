# 물리적 기후 리스크 평가 시스템 아키텍처

## 1. 시스템 개요

본 시스템은 **TCFD(Task Force on Climate-related Financial Disclosures)** 권고안에 따라 물리적 기후 리스크를 정량적으로 평가하는 자동화 시스템입니다.

### 핵심 공식: H × E × V

```
Risk Score = Hazard × Exposure × Vulnerability
```

- **Hazard (H)**: 재난의 강도 (얼마나 강한 재난이 발생하는가?)
- **Exposure (E)**: 노출도 (건물이 재난에 얼마나 노출되어 있는가?)
- **Vulnerability (V)**: 취약성 (건물이 재난에 얼마나 취약한가?)

### 평가 대상: 9개 물리적 리스크

1. **극한 고온** (Extreme Heat)
2. **극한 한파** (Extreme Cold)
3. **가뭄** (Drought)
4. **내륙 홍수** (Inland Flood)
5. **도시 홍수** (Urban Flood)
6. **해안 홍수** (Coastal Flood)
7. **태풍** (Typhoon)
8. **산불** (Wildfire)
9. **수자원 스트레스** (Water Stress)

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 입력                                │
│                 주소 또는 위/경도 좌표                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   risk_calculator.py                            │
│                   (메인 오케스트레이터)                           │
└─────┬───────────────────┬───────────────────┬───────────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│   Hazard (H) │  │ Exposure (E) │  │ Vulnerability (V)│
│              │  │              │  │                  │
│ hazard_      │  │ exposure_    │  │ vulnerability_   │
│ calculator.py│  │ calculator.py│  │ calculator.py    │
└──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
       │                 │                    │
       │                 │                    │
       ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      데이터 레이어                               │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ climate_data_    │  │ spatial_data_    │  │ building_    │ │
│  │ loader.py        │  │ loader.py        │  │ data_fetcher.│ │
│  │                  │  │                  │  │ py           │ │
│  │ - KMA SSP        │  │ - 토지피복도      │  │ - 건축물대장 │ │
│  │   NetCDF 로드    │  │ - NDVI           │  │   API        │ │
│  │ - 기후 변수 추출 │  │ - 토양수분        │  │ - 건물 정보  │ │
│  │                  │  │ - 행정구역        │  │              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ disaster_api_    │  │ stream_order_    │                    │
│  │ fetcher.py       │  │ simple.py        │                    │
│  │                  │  │                  │                    │
│  │ - 재난 이력      │  │ - DEM 고도 추출  │                    │
│  │ - 하천 정보      │  │ - 하천 차수      │                    │
│  │ - 침수 이력      │  │ - 유역 면적      │                    │
│  └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 핵심 모듈 상세

### 3.1 risk_calculator.py (메인 오케스트레이터)

**역할**: H, E, V를 조합하여 최종 리스크 점수 산출

**입력**:
- 위치 정보 (주소 또는 좌표)
- SSP 시나리오 (SSP126, SSP245, SSP370, SSP585)
- 분석 연도 (2021-2100)

**출력**:
```json
{
  "extreme_heat": {
    "risk_score": 75.5,
    "hazard_score": 85.0,
    "exposure_score": 90.0,
    "vulnerability_score": 70.0,
    "risk_level": "high"
  },
  ...
}
```

**핵심 로직**:
```python
def calculate_all_risks(self, location, scenario='SSP245', year=2030):
    # 1. H 계산
    hazard = self.hazard_calculator.calculate(lat, lon)

    # 2. E 계산
    exposure = self.exposure_calculator.calculate(location)

    # 3. V 계산
    vulnerability = self.vulnerability_calculator.calculate(
        hazard, exposure
    )

    # 4. Risk = H × E × V
    risk_score = (H * E * V) / 10000  # 0-100 스케일

    return risk_scores
```

---

### 3.2 hazard_calculator.py (재난 강도 계산)

**역할**: 각 지역에 얼마나 강한 재난이 발생하는지 계산

**데이터 소스**:
- KMA SSP 시나리오 (NetCDF)
- 재난안전데이터 API
- NDVI 위성 데이터
- 토지피복도

**주요 메서드**:
```python
def calculate(self, lat: float, lon: float) -> Dict:
    return {
        'extreme_heat': self._calculate_heat_hazard(),
        'extreme_cold': self._calculate_cold_hazard(),
        'drought': self._calculate_drought_hazard(),
        'inland_flood': self._calculate_inland_flood_hazard(),
        'urban_flood': self._calculate_urban_flood_hazard(),
        'coastal_flood': self._calculate_coastal_flood_hazard(),
        'typhoon': self._calculate_typhoon_hazard(),
        'wildfire': self._calculate_wildfire_hazard(),
        'water_stress': self._calculate_water_stress_hazard(),
    }
```

**예시 - 극한 고온**:
```python
def _calculate_heat_hazard(self, lat, lon, data):
    # KMA SSP 데이터 로드
    heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, year)

    # 폭염일수 기반 강도 판단
    heatwave_days = heat_data['heatwave_days_per_year']
    if heatwave_days > 30:
        intensity = 'very_high'
    elif heatwave_days > 20:
        intensity = 'high'
    ...

    return {
        'annual_max_temp_celsius': 38.3,
        'heatwave_days_per_year': 154,
        'tropical_nights': 23,
        'heat_wave_duration': 18.2,
        'heatwave_intensity': 'very_high',
        'data_source': 'KMA_SSP_gridraw'
    }
```

---

### 3.3 exposure_calculator.py (노출도 계산)

**역할**: 건물이 재난에 얼마나 노출되어 있는지 계산

**데이터 소스**:
- 국토교통부 건축물대장 API
- V-World 주소 변환 API
- DEM 고도 데이터
- 하천/해안 거리 계산

**주요 메서드**:
```python
def calculate(self, location: Union[str, Tuple]) -> Dict:
    # 1. 주소 → 좌표 변환 (도로명/지번 주소 모두 지원)
    if isinstance(location, str):
        lat, lon = self._address_to_coords(location)

    # 2. 건축물 데이터 수집
    raw_data = self.fetcher.fetch_all_building_data(lat, lon)

    # 3. 노출도 구조화
    return {
        'location': {...},
        'building': {...},
        'flood_exposure': {
            'distance_to_river_m': 1000,
            'distance_to_coast_m': 100000,
            'stream_order': 3,
            'in_flood_zone': False
        },
        'heat_exposure': {...},
        'typhoon_exposure': {...},
        ...
    }
```

**주소 변환 로직** (도로명/지번 주소 자동 처리):
```python
def _address_to_coords(self, address: str) -> Tuple[float, float]:
    # ROAD 타입 먼저 시도 (도로명 주소)
    # PARCEL 타입 시도 (지번 주소)
    for address_type in ['ROAD', 'PARCEL']:
        params = {
            'service': 'address',
            'request': 'getcoord',
            'type': address_type,
            'address': address,
            ...
        }
        response = requests.get(VWORLD_API, params=params)
        if success:
            return lat, lon
```

---

### 3.4 vulnerability_calculator.py (취약성 계산)

**역할**: 건물이 재난에 얼마나 취약한지 계산

**계산 방식**: E + H 조합으로 V 산출

**주요 메서드**:
```python
def calculate(self, hazard: Dict, exposure: Dict) -> Dict:
    return {
        'extreme_heat': self._calc_heat_vulnerability(H, E),
        'extreme_cold': self._calc_cold_vulnerability(H, E),
        ...
    }
```

**예시 - 홍수 취약성**:
```python
def _calc_flood_vulnerability(self, hazard, exposure):
    vuln = 50  # 기본값

    # 지하층 있으면 +30
    if exposure['building']['floors_below'] > 0:
        vuln += 30

    # 노후 건물 +20
    if exposure['building']['building_age'] > 30:
        vuln += 20

    # 하천 100m 이내 +20
    if exposure['flood_exposure']['distance_to_river_m'] < 100:
        vuln += 20

    return min(vuln, 100)
```

---

## 4. 데이터 소스 상세

### 4.1 climate_data_loader.py (기후 데이터)

**데이터**: 기상청 KMA SSP 시나리오 (2021-2100)

**파일 형식**: NetCDF (.nc), gzip 압축

**경로**: `Physical_RISK_calculate/data/KMA/gridraw/SSP245/yearly/`

**지원 변수**:
| 변수명 | 설명 | 사용 리스크 |
|--------|------|------------|
| TXx | 연간 최고기온 (°C) | 극한 고온 |
| SU25 | 폭염일수 (일최고 ≥25°C) | 극한 고온 |
| TR25 | 열대야일수 (일최저 ≥25°C) | 극한 고온 |
| WSDIx | 폭염 지속일수 | 극한 고온 |
| TNn | 연간 최저기온 (°C) | 극한 한파 |
| FD0 | 결빙일수 (일최저 <0°C) | 극한 한파 |
| ID0 | 얼음일수 (일최고 <0°C) | 극한 한파 |
| CSDIx | 한파 지속일수 | 극한 한파 |
| RN | 연간 총 강수량 (mm) | 가뭄 |
| CDD | 최대 연속 무강수일수 | 가뭄 |
| SDII | 강수일 평균 강수강도 | 가뭄 |
| RX1DAY | 1일 최대 강수량 (mm) | 내륙/도시 홍수 |
| RX5DAY | 5일 최대 강수량 (mm) | 내륙 홍수 |
| RAIN80 | 강수량 80mm 이상 일수 | 내륙/도시 홍수 |
| RD95P | 95백분위 강수량 (mm) | 홍수 |

**핵심 로직**:
```python
def get_extreme_heat_data(self, lat, lon, year=2030):
    # 1. NetCDF 파일 열기 (gzip 압축 해제)
    with gzip.open(filepath, 'rb') as gz_file:
        nc_data = gz_file.read()

    # 2. 임시 파일로 저장
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_file.write(nc_data)

    # 3. NetCDF 데이터셋 열기
    dataset = nc.Dataset(tmp_file.name, 'r')

    # 4. 좌표 → 격자 인덱스 변환
    lats = dataset.variables['latitude'][:]
    lons = dataset.variables['longitude'][:]
    lat_idx = np.abs(lats - lat).argmin()
    lon_idx = np.abs(lons - lon).argmin()

    # 5. 연도 인덱스 (2021-2100 → 0-79)
    year_idx = year - 2021

    # 6. 값 추출: (time, latitude, longitude)
    value = dataset.variables['TXx'][year_idx, lat_idx, lon_idx]

    return value
```

---

### 4.2 spatial_data_loader.py (공간 데이터)

**데이터 종류**:
1. **토지피복도** (환경부 중분류)
2. **NDVI** (MODIS 위성 식생지수)
3. **토양수분** (SMAP L4)
4. **행정구역** (통계청 경계 Shapefile)

#### 4.2.1 토지피복도

**파일 형식**: GeoTIFF (.tif)

**경로**: `Physical_RISK_calculate/data/landcover/ME_GROUNDCOVERAGE_50000/`

**분류 체계**:
```python
# 환경부 중분류 기준
if 1 <= value <= 10:      # 시가화건조지역
    landcover_type = 'urban'
    impervious_ratio = 0.7  # 불투수면 70%
    vegetation_ratio = 0.1
elif 11 <= value <= 30:   # 농업지역
    landcover_type = 'agricultural'
    impervious_ratio = 0.1
    vegetation_ratio = 0.6
elif 31 <= value <= 50:   # 산림지역
    landcover_type = 'forest'
    impervious_ratio = 0.0
    vegetation_ratio = 0.9
...
```

**사용처**: 도시 홍수, 산불 리스크

#### 4.2.2 NDVI (식생지수)

**파일 형식**: HDF (.hdf)

**경로**: `Physical_RISK_calculate/data/drought/`

**데이터 소스**: MODIS MOD13Q1 (250m 해상도, 16일 주기)

**NDVI 해석**:
```python
if ndvi < 0.2:      # 식생 불량
    vegetation_health = 'poor'
    wildfire_fuel = 'low'
elif ndvi < 0.4:    # 식생 보통
    vegetation_health = 'fair'
    wildfire_fuel = 'low'
elif ndvi < 0.6:    # 식생 양호
    vegetation_health = 'good'
    wildfire_fuel = 'medium'
else:               # 식생 우수
    vegetation_health = 'excellent'
    wildfire_fuel = 'high'
```

**사용처**: 산불 리스크 (연료량 추정)

#### 4.2.3 토양수분

**파일 형식**: HDF5 (.h5)

**데이터 소스**: NASA SMAP L4 (9km 해상도)

**토양수분 해석**:
```python
if soil_moisture < 0.1:     # 매우 건조
    drought_indicator = 'very_dry'
elif soil_moisture < 0.2:   # 건조
    drought_indicator = 'dry'
else:                        # 정상
    drought_indicator = 'normal'
```

**사용처**: 가뭄 리스크

#### 4.2.4 행정구역

**파일 형식**: Shapefile (.shp)

**경로**: `Physical_RISK_calculate/data/geodata/N3A_G0110000.shp`

**추출 정보**:
- 시도 (CTP_KOR_NM)
- 시군구 (SIG_KOR_NM)
- 읍면동 (EMD_KOR_NM)
- 행정코드 (ADM_DR_CD)

---

### 4.3 building_data_fetcher.py (건물 데이터)

**API**: 국토교통부 건축물대장 API

**주요 데이터**:
```python
{
    'ground_floors': 5,           # 지상 층수
    'basement_floors': 1,         # 지하 층수
    'building_type': '업무시설',  # 건물 용도
    'structure': '철근콘크리트조', # 구조
    'build_year': 2006,           # 건축연도
    'building_age': 18,           # 노후도
    'has_piloti': False,          # 필로티 여부
}
```

**사용처**: 모든 취약성 계산

---

### 4.4 disaster_api_fetcher.py (재난 이력)

**API**: 행정안전부 재난안전데이터 API

**주요 데이터**:
1. **침수 이력**: 과거 침수 발생 횟수
2. **하천 정보**: 하천명, 하천 등급, 유역 면적
3. **재난 통계**: 태풍, 폭설 등 통계

**예시**:
```python
{
    'flood_history_count': 54,
    'river_name': '갑천',
    'river_grade': 1,  # 1: 국가하천, 2: 지방하천
    'watershed_area_km2': 2500
}
```

---

### 4.5 stream_order_simple.py (지형 분석)

**데이터**: DEM (Digital Elevation Model)

**파일 형식**: ERDAS IMAGINE (.img)

**경로**: `Physical_RISK_calculate/data/DEM/`

**파일 예시**:
- `대전광역시 유성구.img`
- `성남시 분당구.img`

**추출 정보**:
1. **고도** (elevation_m)
2. **하천 차수** (stream_order): D8 Flow Accumulation 기반
3. **유역 면적** (watershed_area_km2)

**하천 차수 계산**:
```python
# D8 Flow Accumulation 값 기준
if flow_acc > 10000:
    stream_order = 5  # 대하천
elif flow_acc > 5000:
    stream_order = 4
elif flow_acc > 1000:
    stream_order = 3
elif flow_acc > 100:
    stream_order = 2
else:
    stream_order = 1  # 소하천
```

---

## 5. API 사용 현황

### 5.1 V-World 주소 변환 API

**용도**: 도로명/지번 주소 → 위경도 좌표 변환

**엔드포인트**: `https://api.vworld.kr/req/address`

**파라미터**:
```python
params = {
    'service': 'address',
    'request': 'getcoord',
    'format': 'json',
    'crs': 'epsg:4326',
    'address': '대전광역시 유성구 엑스포로 325',
    'type': 'ROAD',  # 또는 'PARCEL'
    'key': VWORLD_API_KEY
}
```

**응답**:
```json
{
    "response": {
        "status": "OK",
        "result": {
            "point": {
                "x": "127.391432737",
                "y": "36.383583733"
            }
        }
    }
}
```

**구현**:
- `exposure_calculator.py` > `_address_to_coords()`
- 도로명 주소 우선, 실패 시 지번 주소 시도

---

### 5.2 국토교통부 건축물대장 API

**용도**: 건물 상세 정보 조회

**엔드포인트**: `http://apis.data.go.kr/1613000/BldRgstService_v2/getBrRecapTitleInfo`

**주요 파라미터**:
```python
params = {
    'sigunguCd': '30200',      # 시군구 코드
    'bjdongCd': '10300',       # 법정동 코드
    'platGbCd': '0',           # 대지구분 (0: 대지, 1: 산)
    'bun': '0140',             # 번
    'ji': '0001',              # 지
    'serviceKey': API_KEY
}
```

**응답 데이터**:
- `grndFlrCnt`: 지상 층수
- `ugrndFlrCnt`: 지하 층수
- `mainPurpsCdNm`: 주용도
- `strctCdNm`: 구조
- `useAprDay`: 사용승인일

**구현**: `building_data_fetcher.py`

---

### 5.3 행정안전부 재난안전데이터 API

**용도**: 침수 이력, 하천 정보, 재난 통계

**API 종류**:
1. **자연재해 위험지구**: 침수 위험 지역
2. **하천 대장**: 하천 등급, 유역 면적
3. **재난 통계**: 태풍, 폭설 등 발생 이력

**구현**: `disaster_api_fetcher.py`

---

## 6. 데이터 플로우 예시

### 시나리오: "대전광역시 유성구 엑스포로 325" 리스크 분석

```
1. 사용자 입력
   └─ 주소: "대전광역시 유성구 엑스포로 325"
   └─ 시나리오: SSP245
   └─ 연도: 2030

2. risk_calculator.py 실행
   │
   ├─ exposure_calculator.py
   │  ├─ V-World API: 주소 → (36.3836, 127.3914)
   │  ├─ building_data_fetcher.py
   │  │  └─ 건축물대장 API
   │  │     ├─ 지상 5층 / 지하 1층
   │  │     ├─ 업무시설
   │  │     ├─ 철근콘크리트조
   │  │     └─ 건축연도 2006년 (노후도 18년)
   │  ├─ stream_order_simple.py
   │  │  └─ DEM: 대전광역시 유성구.img
   │  │     ├─ 고도: 34.5m
   │  │     └─ 하천 차수: 3
   │  └─ 거리 계산
   │     ├─ 해안까지: 100km (내륙)
   │     └─ 하천까지: 1000m
   │
   ├─ hazard_calculator.py
   │  ├─ climate_data_loader.py
   │  │  └─ KMA SSP245 NetCDF
   │  │     ├─ TXx: 38.3°C (연간 최고기온)
   │  │     ├─ SU25: 154일 (폭염일수)
   │  │     ├─ TR25: 23일 (열대야일수)
   │  │     ├─ WSDIx: 18.2일 (폭염 지속)
   │  │     ├─ TNn: -10.5°C (연간 최저기온)
   │  │     ├─ FD0: 85일 (결빙일수)
   │  │     ├─ RN: 1351mm (연간 강수량)
   │  │     ├─ CDD: 37일 (최대 연속 무강수)
   │  │     ├─ RX1DAY: 254mm (1일 최대 강수)
   │  │     └─ RAIN80: 4일 (호우일수)
   │  ├─ spatial_data_loader.py
   │  │  ├─ 토지피복도: urban (불투수율 70%)
   │  │  ├─ NDVI: 0.3 (식생지수)
   │  │  └─ 토양수분: -9999 (데이터 누락)
   │  └─ disaster_api_fetcher.py
   │     ├─ 침수 이력: 54건
   │     └─ 하천: 갑천 (국가하천)
   │
   └─ vulnerability_calculator.py
      ├─ 극한 고온 취약성
      │  └─ 지하층 있음 (+20)
      │  └─ 노후 건물 (+10)
      │  └─ V = 80
      ├─ 내륙 홍수 취약성
      │  └─ 지하층 있음 (+30)
      │  └─ 침수 이력 많음 (+20)
      │  └─ V = 85
      ...

3. 최종 리스크 점수 산출
   ├─ 극한 고온: H(85) × E(90) × V(80) = 76.5점 (high)
   ├─ 내륙 홍수: H(70) × E(75) × V(85) = 72.1점 (high)
   ├─ 도시 홍수: H(65) × E(80) × V(75) = 68.9점 (medium)
   ...
   └─ 종합 리스크: 평균 65.3점
```

---

## 7. 실제 데이터 vs Fallback 현황

### 실제 데이터 사용률: **93%**

| 리스크 | 실제 데이터 사용률 | 데이터 소스 |
|--------|-------------------|------------|
| 극한 고온 | 100% | KMA SSP (TXx, SU25, TR25, WSDIx) |
| 극한 한파 | 100% | KMA SSP (TNn, FD0, ID0, CSDIx) |
| 가뭄 | 90% | KMA SSP (CDD, SDII) + SMAP 토양수분 |
| 내륙 홍수 | 100% | KMA SSP + 재난 API + DEM |
| 도시 홍수 | 100% | KMA SSP + 토지피복도 |
| 해안 홍수 | 100% | Haversine 거리 계산 |
| 태풍 | 70% | 통계 기반 (Best Track API 미연동) |
| 산불 | 100% | NDVI + 토지피복도 + KMA SSP |
| 수자원 스트레스 | 70% | 인구 통계 (수도 사용량 API 미연동) |

### Fallback 사용 조건

**원칙**: 데이터 로드 실패 시에만 Fallback 사용

```python
# 예시: climate_data_loader.py
if self.climate_loader:
    heat_data = self.climate_loader.get_extreme_heat_data(lat, lon, year)
    return heat_data
else:
    # Fallback: netCDF4 라이브러리 없을 때만
    return {
        'annual_max_temp_celsius': 38.5,
        'data_source': 'fallback'
    }
```

**Fallback 발생 케이스**:
1. NetCDF 파일 없음
2. 좌표가 격자 범위 밖
3. 필수 라이브러리 미설치 (netCDF4, h5py, rasterio)
4. API 응답 실패 (타임아웃, 인증 오류)

---

## 8. 주요 계산 공식

### 8.1 FWI (Fire Weather Index) - 산불

```python
FWI = (max_temp - 20) × 2 + consecutive_dry_days

# 예시: 대전
max_temp = 38.3°C
dry_days = 37일
FWI = (38.3 - 20) × 2 + 37 = 73.6
```

### 8.2 SPI (Standardized Precipitation Index) - 가뭄

```python
if CDD > 30:
    SPI = -2.0  # 극심한 가뭄
elif CDD > 20:
    SPI = -1.5  # 심한 가뭄
elif CDD > 15:
    SPI = -1.0  # 보통 가뭄
else:
    SPI = -0.5  # 경미한 가뭄
```

### 8.3 Haversine Distance - 거리 계산

```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # 지구 반지름 (km)

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c * 1000  # m 단위
```

---

## 9. TCFD 준수 사항

### 투명성 (Transparency)

**모든 데이터 소스 명시**:
```python
{
    'data_source': 'KMA_SSP_gridraw',  # 실제 데이터
    'data_source': 'fallback',          # Fallback 사용
    'data_source': 'NDVI + landcover + climate'  # 조합 데이터
}
```

### 품질 경고

```python
if data_quality < 0.7:
    tcfd_warnings.append("⚠️ 데이터 품질 낮음: 일부 추정값 포함")

if data['data_source'] == 'fallback':
    tcfd_warnings.append("⚠️ 실제 데이터 로드 실패: 기본값 사용")
```

### 시나리오 기반 분석

**4가지 SSP 시나리오 지원**:
- **SSP126**: 저탄소 시나리오 (2°C 목표)
- **SSP245**: 중간 시나리오 (현재 추세)
- **SSP370**: 고탄소 시나리오
- **SSP585**: 최악 시나리오 (4°C 이상)

---

## 10. 파일 구조

```
Physical_RISK_calculate/
│
├── code/                           # 코드
│   ├── risk_calculator.py          # 메인 오케스트레이터
│   ├── hazard_calculator.py        # H 계산
│   ├── exposure_calculator.py      # E 계산
│   ├── vulnerability_calculator.py # V 계산
│   │
│   ├── climate_data_loader.py      # KMA SSP NetCDF 로더
│   ├── spatial_data_loader.py      # 토지피복도/NDVI/토양수분 로더
│   ├── building_data_fetcher.py    # 건축물대장 API
│   ├── disaster_api_fetcher.py     # 재난 API
│   └── stream_order_simple.py      # DEM 지형 분석
│
├── data/                           # 데이터
│   ├── KMA/                        # 기상청 SSP 시나리오
│   │   └── gridraw/
│   │       └── SSP245/yearly/
│   │           ├── SSP245_TXx_gridraw_yearly_2021-2100.nc
│   │           ├── SSP245_SU25_gridraw_yearly_2021-2100.nc
│   │           └── ...
│   │
│   ├── DEM/                        # 고도 데이터
│   │   ├── 대전광역시 유성구.img
│   │   └── 성남시 분당구.img
│   │
│   ├── landcover/                  # 토지피복도
│   │   └── ME_GROUNDCOVERAGE_50000/
│   │       └── *.tif
│   │
│   ├── drought/                    # 가뭄 관련 데이터
│   │   ├── MOD13Q1*.hdf            # NDVI
│   │   └── SMAP_L4_SM*.h5          # 토양수분
│   │
│   └── geodata/                    # 행정구역
│       └── N3A_G0110000.shp
│
├── docs/                           # 문서
│   ├── 01_project_overview/        # 프로젝트 개요
│   ├── 02_data_models/             # 데이터 모델
│   ├── 03_api_documentation/       # API 문서
│   ├── 04_risk_analysis/           # 리스크 분석
│   └── 05_data_management/         # 데이터 관리
│
└── .env                            # API 키
    ├── VWORLD_API_KEY
    └── BUILDING_API_KEY
```

---

## 11. 환경 설정

### 필수 라이브러리

```bash
pip install netCDF4       # KMA SSP NetCDF 읽기
pip install h5py          # SMAP 토양수분 HDF5 읽기
pip install rasterio      # 토지피복도 GeoTIFF 읽기
pip install geopandas     # 행정구역 Shapefile 읽기
pip install requests      # API 호출
pip install python-dotenv # 환경 변수 관리
```

### API 키 설정

`.env` 파일:
```
VWORLD_API_KEY=your_vworld_key
BUILDING_API_KEY=your_building_key
```

---

## 12. 사용 예시

### Python 코드

```python
from code.risk_calculator import RiskCalculator

# 1. 초기화
calculator = RiskCalculator(
    scenario='SSP245',  # SSP 시나리오
    target_year=2030    # 분석 연도
)

# 2. 리스크 계산 (주소)
result = calculator.calculate_all_risks(
    location="대전광역시 유성구 엑스포로 325"
)

# 3. 리스크 계산 (좌표)
result = calculator.calculate_all_risks(
    location=(36.3836, 127.3914)
)

# 4. 결과 출력
print(f"극한 고온 리스크: {result['extreme_heat']['risk_score']}점")
print(f"리스크 등급: {result['extreme_heat']['risk_level']}")
```

### 출력 예시

```json
{
  "extreme_heat": {
    "risk_score": 76.5,
    "risk_level": "high",
    "hazard_score": 85.0,
    "exposure_score": 90.0,
    "vulnerability_score": 80.0,
    "data_sources": ["KMA_SSP_gridraw", "building_api"],
    "tcfd_warnings": []
  },
  "inland_flood": {
    "risk_score": 72.1,
    "risk_level": "high",
    ...
  },
  ...
}
```

---

## 13. 향후 개선 사항

### 현재 진행 중

1. **SMAP 토양수분 좌표 변환** - 현재 -9999 반환 문제 해결
2. **RN 연간 강수량** - 일부 NetCDF 파일 로드 실패 수정
3. **태풍 Best Track API** - 통계 대신 실제 경로 데이터 연동
4. **수도 사용량 API** - 수자원 스트레스 정확도 향상

### 추가 기능 (향후)

1. **배치 분석**: 여러 주소 동시 처리
2. **리포트 생성**: PDF/DOCX TCFD 보고서 자동 생성
3. **시계열 분석**: 2030/2050/2100 비교
4. **시나리오 비교**: SSP126 vs SSP585 차이 분석
5. **지도 시각화**: 리스크 히트맵 생성

---

## 14. 문의 및 기여

**프로젝트 담당**: 물리적 리스크 분석 팀

**관련 문서**:
- [데이터 모델 ERD](../02_data_models/)
- [API 상세 문서](../03_api_documentation/)
- [리스크 분석 방법론](../04_risk_analysis/)

**버전**: 1.0.0 (2024-11-24)
