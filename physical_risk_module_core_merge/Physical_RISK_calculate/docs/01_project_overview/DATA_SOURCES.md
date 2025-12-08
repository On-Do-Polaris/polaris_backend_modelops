# 데이터 소스 상세 가이드

## 목차
1. [KMA SSP 기후 시나리오 데이터](#1-kma-ssp-기후-시나리오-데이터)
2. [공간 데이터](#2-공간-데이터)
3. [건축물 데이터](#3-건축물-데이터)
4. [재난 이력 데이터](#4-재난-이력-데이터)
5. [데이터 품질 관리](#5-데이터-품질-관리)

---

## 1. KMA SSP 기후 시나리오 데이터

### 1.1 개요

**데이터 제공**: 기상청 (KMA, Korea Meteorological Administration)

**시나리오**: IPCC AR6 SSP (Shared Socioeconomic Pathways)
- **SSP126**: 저탄소 시나리오 (온실가스 강력 감축, 2°C 목표)
- **SSP245**: 중간 시나리오 (현재 정책 유지)
- **SSP370**: 고탄소 시나리오 (제한적 감축)
- **SSP585**: 최악 시나리오 (감축 없음, 4-5°C 상승)

**시간 범위**: 2021-2100 (연단위)

**공간 해상도**: 1km 격자 (한반도 전역)

**파일 형식**: NetCDF (.nc), gzip 압축

### 1.2 데이터 경로

```
Physical_RISK_calculate/data/KMA/gridraw/
├── SSP126/yearly/
│   ├── SSP126_TXx_gridraw_yearly_2021-2100.nc
│   ├── SSP126_SU25_gridraw_yearly_2021-2100.nc
│   └── ...
├── SSP245/yearly/
│   └── ...
├── SSP370/yearly/
│   └── ...
└── SSP585/yearly/
    └── ...
```

### 1.3 변수 목록

#### 온도 관련

| 변수명 | 설명 | 단위 | 사용 리스크 |
|--------|------|------|------------|
| **TXx** | 연간 최고기온 | °C | 극심한 고온 |
| **TNn** | 연간 최저기온 | °C | 극심한 극심한 한파 |
| **SU25** | 극심한 고온일수 (일최고 ≥25°C) | 일 | 극심한 고온 |
| **TR25** | 열대야일수 (일최저 ≥25°C) | 일 | 극심한 고온 |
| **FD0** | 결빙일수 (일최저 <0°C) | 일 | 극심한 극심한 한파 |
| **ID0** | 얼음일수 (일최고 <0°C) | 일 | 극심한 극심한 한파 |
| **WSDIx** | 극심한 고온 지속일수 (6일 이상) | 일 | 극심한 고온 |
| **CSDIx** | 극심한 한파 지속일수 (6일 이상) | 일 | 극심한 극심한 한파 |

#### 강수 관련

| 변수명 | 설명 | 단위 | 사용 리스크 |
|--------|------|------|------------|
| **RN** | 연간 총 강수량 | mm | 가뭄 |
| **RX1DAY** | 1일 최대 강수량 | mm | 내륙/도시 홍수 |
| **RX5DAY** | 5일 최대 강수량 | mm | 하천 홍수 |
| **CDD** | 최대 연속 무강수일수 | 일 | 가뭄 |
| **SDII** | 강수일 평균 강수강도 | mm/일 | 가뭄 |
| **RAIN80** | 강수량 80mm 이상 일수 | 일 | 내륙/도시 홍수 |
| **RD95P** | 95백분위 강수량 | mm | 홍수 |

### 1.4 데이터 구조

```python
# NetCDF 파일 구조
dimensions:
    time = 80         # 2021-2100 (80년)
    latitude = 1000   # 위도 격자
    longitude = 800   # 경도 격자

variables:
    time(time)           # 연도
    latitude(latitude)   # 위도 (33-43°N)
    longitude(longitude) # 경도 (124-132°E)
    TXx(time, latitude, longitude)  # 데이터

# 데이터 접근
value = dataset['TXx'][year_idx, lat_idx, lon_idx]
```

### 1.5 사용 예시

```python
from climate_data_loader import ClimateDataLoader

loader = ClimateDataLoader(scenario='SSP245')

# 대전 유성구 2030년 극심한 고온 데이터
heat_data = loader.get_extreme_heat_data(
    lat=36.383,
    lon=127.395,
    year=2030
)

print(heat_data)
# {
#     'annual_max_temp_celsius': 38.3,
#     'heatwave_days_per_year': 154,
#     'tropical_nights': 23,
#     'heat_wave_duration': 18.2,
#     'climate_scenario': 'SSP245',
#     'year': 2030,
#     'data_source': 'KMA_SSP_gridraw'
# }
```

### 1.6 데이터 처리 과정

```python
# 1. gzip 압축 해제
with gzip.open(filepath, 'rb') as gz_file:
    nc_data = gz_file.read()

# 2. 임시 파일 생성
tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
tmp_file.write(nc_data)

# 3. NetCDF 데이터셋 열기
dataset = nc.Dataset(tmp_file.name, 'r')

# 4. 좌표 → 격자 인덱스 변환
lats = dataset.variables['latitude'][:]
lons = dataset.variables['longitude'][:]
lat_idx = np.abs(lats - lat).argmin()
lon_idx = np.abs(lons - lon).argmin()

# 5. 연도 인덱스 계산
year_idx = year - 2021  # 2030 → 9

# 6. 값 추출
value = dataset.variables['TXx'][year_idx, lat_idx, lon_idx]
```

### 1.7 데이터 품질

- **공간 해상도**: 1km (세밀)
- **시간 범위**: 80년 (충분)
- **업데이트**: IPCC AR6 최신 시나리오
- **검증**: 기상청 공식 데이터

**제한 사항**:
- 연단위 데이터 (월/일 단위 없음)
- 한반도 범위만 제공
- 파일 크기 큼 (압축 필수)

---

## 2. 공간 데이터

### 2.1 토지피복도 (Land Cover)

#### 데이터 제공
**출처**: 환경부 환경공간정보서비스

**명칭**: 토지피복지도 중분류 (1:50,000)

**경로**: `Physical_RISK_calculate/data/landcover/ME_GROUNDCOVERAGE_50000/`

**파일 형식**: GeoTIFF (.tif)

**좌표계**: EPSG:5179 (한국 중부원점)

#### 분류 체계

```python
# 환경부 중분류 (값 1-90)
분류 코드:
1-10:   시가화건조지역 (주거, 상업, 공업 등)
11-30:  농업지역 (논, 밭, 과수원 등)
31-50:  산림지역 (활엽수림, 침엽수림, 혼효림)
51-60:  초지 (자연초지, 골프장)
61-70:  습지 (내륙습지, 연안습지)
71-80:  나지 (자연나지, 채광지역)
81-90:  수역 (내륙수, 해양수)
```

#### 해석 기준

```python
if 1 <= value <= 10:      # 도시
    landcover_type = 'urban'
    impervious_ratio = 0.7    # 불투수면 비율 70%
    vegetation_ratio = 0.1
    urban_intensity = 'high'

elif 11 <= value <= 30:   # 농업
    landcover_type = 'agricultural'
    impervious_ratio = 0.1
    vegetation_ratio = 0.6
    urban_intensity = 'low'

elif 31 <= value <= 50:   # 산림
    landcover_type = 'forest'
    impervious_ratio = 0.0
    vegetation_ratio = 0.9
    urban_intensity = 'low'
```

#### 사용처
- **도시 홍수**: 불투수면 비율 → 배수 용량 평가
- **산불**: 식생 유형 → 연료량 추정
- **열섬**: 도시화 정도 → 열섬 강도

#### 사용 예시

```python
from spatial_data_loader import SpatialDataLoader

loader = SpatialDataLoader()
landcover = loader.get_landcover_data(lat=36.383, lon=127.395)

print(landcover)
# {
#     'landcover_type': 'urban',
#     'impervious_ratio': 0.7,
#     'vegetation_ratio': 0.1,
#     'urban_intensity': 'high',
#     'raw_value': 5,
#     'data_source': 'ME_GROUNDCOVERAGE_50000'
# }
```

---

### 2.2 NDVI (식생지수)

#### 데이터 제공
**출처**: NASA MODIS (Terra 위성)

**제품명**: MOD13Q1 (16-Day Vegetation Indices)

**경로**: `Physical_RISK_calculate/data/drought/`

**파일 형식**: HDF (.hdf)

**공간 해상도**: 250m

**시간 해상도**: 16일 주기

#### NDVI 해석

```python
NDVI = (NIR - Red) / (NIR + Red)  # -1 to 1

# 식생 건강도 판단
if ndvi < 0.2:
    vegetation_health = 'poor'      # 식생 불량
    wildfire_fuel = 'low'
elif ndvi < 0.4:
    vegetation_health = 'fair'      # 보통
    wildfire_fuel = 'low'
elif ndvi < 0.6:
    vegetation_health = 'good'      # 양호
    wildfire_fuel = 'medium'
else:
    vegetation_health = 'excellent' # 우수
    wildfire_fuel = 'high'          # 산불 연료 많음
```

#### 사용처
- **산불**: 식생 밀도 → 연료량 추정
- **가뭄**: 식생 건강도 → 가뭄 지표

#### 사용 예시

```python
ndvi_data = loader.get_ndvi_data(lat=36.383, lon=127.395)

print(ndvi_data)
# {
#     'ndvi': 0.3,
#     'vegetation_health': 'fair',
#     'wildfire_fuel': 'low',
#     'data_source': 'MOD13Q1'
# }
```

---

### 2.3 토양수분

#### 데이터 제공
**출처**: NASA SMAP (Soil Moisture Active Passive)

**제품명**: SMAP L4 Global

**경로**: `Physical_RISK_calculate/data/drought/`

**파일 형식**: HDF5 (.h5)

**공간 해상도**: 9km

**시간 해상도**: 3시간

#### 토양수분 해석

```python
# 단위: m³/m³ (체적 함수율)
정상 범위: 0.1 - 0.4

if soil_moisture < 0.1:
    drought_indicator = 'very_dry'  # 극심한 가뭄
elif soil_moisture < 0.2:
    drought_indicator = 'dry'        # 가뭄
else:
    drought_indicator = 'normal'     # 정상
```

#### 사용처
- **가뭄**: 토양 건조도 평가

#### 현재 이슈
⚠️ **좌표 변환 문제**: MODIS 타일 좌표계 변환 미구현 → -9999 반환

**해결 예정**: MODIS Sinusoidal 투영법 적용

---

### 2.4 행정구역

#### 데이터 제공
**출처**: 통계청 통계지리정보서비스

**명칭**: 읍면동 경계 (N3A_G0110000)

**경로**: `Physical_RISK_calculate/data/geodata/N3A_G0110000.shp`

**파일 형식**: Shapefile (.shp)

**좌표계**: EPSG:5179

#### 추출 정보

```python
admin = loader.get_administrative_area(lat=36.383, lon=127.395)

print(admin)
# {
#     'sido': '대전광역시',         # CTP_KOR_NM
#     'sigungu': '유성구',          # SIG_KOR_NM
#     'dong': '구암동',             # EMD_KOR_NM
#     'adm_code': '3020010300',     # ADM_DR_CD
#     'data_source': 'N3A_G0110000'
# }
```

#### 사용처
- 행정구역 기반 통계 집계
- 시군구 코드 추출 (건축물대장 API 호출용)

---

### 2.5 DEM (고도)

#### 데이터 제공
**출처**: 국토지리정보원 수치표고모델

**경로**: `Physical_RISK_calculate/data/DEM/`

**파일 형식**: ERDAS IMAGINE (.img), ASCII Grid (.txt)

**공간 해상도**: 5m

**파일 예시**:
- `대전광역시 유성구.img`
- `성남시 분당구.img`

#### 추출 정보

```python
from stream_order_simple import StreamOrderCalculator

calculator = StreamOrderCalculator()
result = calculator.get_stream_order(lat=36.383, lon=127.395)

print(result)
# {
#     'elevation_m': 34.5,          # 고도
#     'stream_order': 3,            # 하천 차수
#     'watershed_area_km2': 2500,   # 유역 면적
#     'flow_accumulation': 5000,    # 흐름 누적
#     'data_source': 'DEM_5m'
# }
```

#### 하천 차수 계산 (D8 Flow Accumulation)

```python
# D8 알고리즘: 8방향 흐름 분석
Flow Accumulation 값 기준:

if flow_acc > 10000:
    stream_order = 5  # 대하천 (금강, 한강 등)
elif flow_acc > 5000:
    stream_order = 4  # 중하천
elif flow_acc > 1000:
    stream_order = 3  # 소하천
elif flow_acc > 100:
    stream_order = 2  # 실개천
else:
    stream_order = 1  # 계곡
```

#### 사용처
- **홍수**: 고도, 하천 차수 → 침수 위험 평가
- **산사태**: 경사도 계산
- **지형 분석**: 유역 면적 추출

---

## 3. 건축물 데이터

### 3.1 국토교통부 건축물대장 API

#### API 정보
**제공**: 국토교통부 건축데이터개방

**엔드포인트**: `http://apis.data.go.kr/1613000/BldRgstService_v2/getBrRecapTitleInfo`

**인증**: API 키 (Decoding)

**요청 제한**: 1,000건/일

#### 입력 파라미터

```python
params = {
    'serviceKey': API_KEY,       # 서비스 키
    'sigunguCd': '30200',        # 시군구 코드 (5자리)
    'bjdongCd': '10300',         # 법정동 코드 (5자리)
    'platGbCd': '0',             # 대지구분 (0: 대지, 1: 산)
    'bun': '0140',               # 번 (4자리)
    'ji': '0001',                # 지 (4자리)
    'numOfRows': '1',            # 결과 수
    'pageNo': '1'                # 페이지
}
```

#### 응답 데이터

```xml
<response>
    <body>
        <items>
            <item>
                <platPlc>대전광역시 유성구 원촌동 140-1</platPlc>
                <grndFlrCnt>5</grndFlrCnt>       <!-- 지상 층수 -->
                <ugrndFlrCnt>1</ugrndFlrCnt>     <!-- 지하 층수 -->
                <mainPurpsCdNm>업무시설</mainPurpsCdNm>
                <strctCdNm>철근콘크리트조</strctCdNm>
                <useAprDay>20061215</useAprDay>  <!-- 사용승인일 -->
                <etcPurps>지하1층 필로티</etcPurps>
            </item>
        </items>
    </body>
</response>
```

#### 추출 정보

```python
{
    'ground_floors': 5,              # 지상 층수
    'basement_floors': 1,            # 지하 층수
    'building_type': '업무시설',     # 용도
    'main_purpose': '업무시설',
    'structure': '철근콘크리트조',   # 구조
    'build_year': 2006,              # 건축연도
    'building_age': 18,              # 노후도 (2024 - 2006)
    'has_piloti': True,              # 필로티 여부 (etcPurps에서 파싱)
}
```

#### Fallback 전략

```python
# 1. 지번 주소로 검색
result = fetch_by_jibun(sido, sigungu, dong, bun, ji)

if not result:
    # 2. 주변 건물 검색 (번지 ±5)
    result = fetch_nearby_buildings(...)

if not result:
    # 3. 통계 기반 추정
    result = estimate_by_region(sido, sigungu)
    # - 지상 3층 (단독주택 평균)
    # - 지하 0층
    # - 주택 용도
```

#### 사용처
- **모든 취약성 계산**: 건물 노후도, 지하층 여부, 구조 등

---

## 4. 재난 이력 데이터

### 4.1 행정안전부 재난안전데이터 API

#### API 목록

1. **자연재해위험지구**
   - 침수 위험 지역 정보
   - 지정 사유 (하천범람, 내수침수 등)

2. **하천 대장**
   - 하천명, 하천 등급 (국가/지방하천)
   - 유역 면적, 하천 연장

3. **재난 통계**
   - 태풍 피해 이력
   - 폭설, 극심한 고온 피해 통계

#### 사용 예시

```python
from disaster_api_fetcher import DisasterAPIFetcher

fetcher = DisasterAPIFetcher()

# 침수 이력 조회
flood_history = fetcher.get_flood_history(lat=36.383, lon=127.395)
print(flood_history)
# {
#     'flood_count': 54,           # 과거 침수 횟수
#     'last_flood_year': 2020,     # 최근 침수 연도
#     'flood_type': '하천범람',    # 침수 유형
# }

# 하천 정보 조회
river_info = fetcher.get_nearest_river_info(lat=36.383, lon=127.395)
print(river_info)
# {
#     'river_name': '갑천',
#     'river_grade': 1,            # 1: 국가하천, 2: 지방하천
#     'watershed_area_km2': 2500,
# }
```

#### 사용처
- **하천 홍수**: 침수 이력 → 홍수 빈도 보정
- **태풍**: 태풍 피해 통계 → 피해 규모 추정

---

## 5. 데이터 품질 관리

### 5.1 데이터 소스 명시

**TCFD 투명성 원칙**: 모든 데이터 소스를 명시

```python
# 실제 데이터
{
    'data_source': 'KMA_SSP_gridraw'
}

# Fallback 사용
{
    'data_source': 'fallback'
}

# 조합 데이터
{
    'data_source': 'NDVI + landcover + climate'
}
```

### 5.2 품질 등급

```python
def assess_data_quality(data):
    required_fields = [
        'ground_floors',
        'building_type',
        'distance_to_river_m',
        'distance_to_coast_m',
        'elevation_m'
    ]

    available = sum(1 for field in required_fields if field in data)
    ratio = available / len(required_fields)

    if ratio >= 0.9:
        return 'high'      # 90% 이상: 우수
    elif ratio >= 0.7:
        return 'medium'    # 70-90%: 보통
    else:
        return 'low'       # 70% 미만: 낮음
```

### 5.3 TCFD 경고

```python
tcfd_warnings = []

# 데이터 누락 경고
if data_source == 'fallback':
    tcfd_warnings.append("⚠️ 실제 데이터 로드 실패: 기본값 사용")

# 품질 낮음 경고
if data_quality == 'low':
    tcfd_warnings.append("⚠️ 데이터 품질 낮음: 일부 추정값 포함")

# 좌표 범위 초과 경고
if lat < 33 or lat > 43:
    tcfd_warnings.append("⚠️ 한반도 범위 외: 기후 데이터 없음")
```

### 5.4 실제 데이터 사용률

**전체 시스템**: 93%

| 리스크 | 실제 데이터 | Fallback | 사용률 |
|--------|------------|----------|--------|
| 극심한 고온 | KMA SSP | - | 100% |
| 극심한 극심한 한파 | KMA SSP | - | 100% |
| 가뭄 | KMA SSP + SMAP | SMAP 좌표 이슈 | 90% |
| 하천 홍수 | KMA SSP + 재난 API + DEM | - | 100% |
| 도시 홍수 | KMA SSP + 토지피복도 | - | 100% |
| 해수면 상승 | Haversine 거리 | - | 100% |
| 태풍 | 통계 | Best Track API 미연동 | 70% |
| 산불 | NDVI + 토지피복도 + KMA | - | 100% |
| 수자원 | 인구 통계 | 수도 사용량 API 미연동 | 70% |

### 5.5 데이터 업데이트 주기

| 데이터 | 업데이트 주기 | 최신 버전 |
|--------|--------------|----------|
| KMA SSP | 5년 (IPCC 보고서 주기) | IPCC AR6 (2021) |
| 토지피복도 | 5년 | 2020년 |
| NDVI | 16일 | 실시간 |
| SMAP | 3시간 | 실시간 |
| 건축물대장 | 실시간 | API 연동 |
| 재난 이력 | 실시간 | API 연동 |
| DEM | 10년 | 2018년 |
| 행정구역 | 1년 | 2023년 |

---

## 6. 데이터 다운로드 가이드

### 6.1 KMA SSP 시나리오

**다운로드 경로**: 기상청 기후정보포털 (http://www.climate.go.kr/)

**필요 파일**:
```
SSP245_TXx_gridraw_yearly_2021-2100.nc
SSP245_SU25_gridraw_yearly_2021-2100.nc
SSP245_TR25_gridraw_yearly_2021-2100.nc
SSP245_WSDIx_gridraw_yearly_2021-2100.nc
SSP245_TNn_gridraw_yearly_2021-2100.nc
SSP245_FD0_gridraw_yearly_2021-2100.nc
SSP245_ID0_gridraw_yearly_2021-2100.nc
SSP245_CSDIx_gridraw_yearly_2021-2100.nc
SSP245_RN_gridraw_yearly_2021-2100.nc
SSP245_CDD_gridraw_yearly_2021-2100.nc
SSP245_SDII_gridraw_yearly_2021-2100.nc
SSP245_RX1DAY_gridraw_yearly_2021-2100.nc
SSP245_RX5DAY_gridraw_yearly_2021-2100.nc
SSP245_RAIN80_gridraw_yearly_2021-2100.nc
SSP245_RD95P_gridraw_yearly_2021-2100.nc
```

### 6.2 토지피복도

**다운로드 경로**: 환경공간정보서비스 (https://egis.me.go.kr/)

**검색**: 토지피복지도 중분류 (1:50,000)

### 6.3 NDVI

**다운로드 경로**: NASA Earthdata (https://earthdata.nasa.gov/)

**제품**: MOD13Q1.061 (Terra MODIS Vegetation Indices 16-Day)

### 6.4 SMAP

**다운로드 경로**: NASA Earthdata (https://earthdata.nasa.gov/)

**제품**: SMAP L4 Global Daily 9 km

### 6.5 DEM

**다운로드 경로**: 국토지리정보원 (http://www.ngii.go.kr/)

**제품**: 5m 수치표고모델 (시군구별)

### 6.6 행정구역

**다운로드 경로**: 통계청 통계지리정보서비스 (https://sgis.kostat.go.kr/)

**제품**: 읍면동 경계 (N3A_G0110000)

---

## 7. API 키 발급 가이드

### 7.1 V-World API

**발급처**: V-World (https://www.vworld.kr/)

1. 회원가입
2. "오픈API" → "인증키 신청"
3. 용도: 주소 변환
4. `.env` 파일에 저장:
   ```
   VWORLD_API_KEY=your_key_here
   ```

### 7.2 건축물대장 API

**발급처**: 공공데이터포털 (https://www.data.go.kr/)

1. 회원가입
2. "건축물대장 정보 조회 서비스" 검색
3. 활용신청 (일반 인증키 Decoding)
4. `.env` 파일에 저장:
   ```
   BUILDING_API_KEY=your_key_here
   ```

---

**문서 버전**: 1.0.0 (2024-11-24)
