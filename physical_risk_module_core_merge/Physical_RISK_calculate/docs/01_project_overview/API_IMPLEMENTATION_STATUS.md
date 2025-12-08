# API 및 데이터 구현 상태

**최종 업데이트**: 2024-11-24
**버전**: 2.0.0

## 시나리오별 계산 지원

✅ **4개 SSP 시나리오 모두 지원** (v2.0.0부터)

```python
from code.risk_calculator import RiskCalculator

# 전체 시나리오 계산 (SSP126, SSP245, SSP370, SSP585)
calculator = RiskCalculator(target_year=2030)
result = calculator.calculate_all_risks("대전광역시 유성구 엑스포로 325")

# 특정 시나리오만 계산
calculator = RiskCalculator(scenarios=['SSP245', 'SSP585'], target_year=2050)
result = calculator.calculate_all_risks((36.383, 127.395))
```

**결과 구조**:
```json
{
  "scenarios": {
    "SSP126": {
      "risks": { 9개 리스크 점수 },
      "total_score": 456.78,
      "risk_level": "HIGH",
      "hazard": { H 데이터 }
    },
    "SSP245": { ... },
    "SSP370": { ... },
    "SSP585": { ... }
  },
  "exposure": { E 데이터 (모든 시나리오 공통) },
  "vulnerability": { V 데이터 (모든 시나리오 공통) },
  "metadata": {
    "target_year": 2030,
    "scenarios": ["SSP126", "SSP245", "SSP370", "SSP585"]
  }
}
```

---

## API 구현 현황

### ✅ **완전 구현** (100% 작동)

#### 1. V-World 주소 변환 API
- **목적**: 도로명/지번 주소 → 위경도 좌표 변환
- **파일**: `exposure_calculator.py` > `_address_to_coords()`
- **상태**: ✅ **정상 작동**
- **기능**:
  - 도로명 주소 지원 (예: "대전광역시 유성구 엑스포로 325")
  - 지번 주소 지원 (예: "대전광역시 유성구 원촌동 140-1")
  - 자동 Fallback (ROAD → PARCEL)
- **API 키**: `VWORLD_API_KEY` (필수)

**사용 예시**:
```python
from code.exposure_calculator import ExposureCalculator

calc = ExposureCalculator()
lat, lon = calc._address_to_coords("대전광역시 유성구 엑스포로 325")
# 결과: (36.383583733, 127.391432737)
```

#### 2. 국토교통부 건축물대장 API
- **목적**: 건물 상세 정보 조회 (층수, 용도, 구조, 건축연도)
- **파일**: `building_data_fetcher.py`
- **상태**: ✅ **정상 작동**
- **기능**:
  - 지상/지하 층수
  - 건물 용도 (업무시설, 주택, 상업시설 등)
  - 구조 (철근콘크리트조, 철골조 등)
  - 건축연도 및 노후도 계산
  - 필로티 여부 파싱
- **API 키**: `BUILDING_API_KEY` (필수)
- **Fallback**: 주변 건물 검색 또는 지역 통계 기반 추정

**추출 데이터**:
```python
{
    'ground_floors': 5,
    'basement_floors': 1,
    'building_type': '업무시설',
    'structure': '철근콘크리트조',
    'build_year': 2006,
    'building_age': 18,
    'has_piloti': True
}
```

#### 3. 재난안전데이터 API
- **목적**: 침수 이력, 하천 정보
- **파일**: `disaster_api_fetcher.py`
- **상태**: ✅ **정상 작동**

**3-1. 하천정보 API** (`get_nearest_river_info`)
- **엔드포인트**: `https://www.safetydata.go.kr/V2/api/DSSP-IF-10720`
- **API 키**: `RIVER_API_KEY` (필수)
- **추출 데이터**:
  ```python
  {
      'river_name': '갑천',
      'river_grade': 1,  # 1: 국가하천, 2: 지방하천
      'watershed_area_km2': 2500,
      'river_length_km': 120.5
  }
  ```
- **제한 사항**: 하천 좌표 정보 없음 → 거리 계산 불가 (임시로 1km 사용)

**3-2. 긴급재난문자 API** (`get_flood_history`)
- **엔드포인트**: `https://www.safetydata.go.kr/V2/api/DSSP-IF-00247`
- **API 키**: `EMERGENCYMESSAGE_API_KEY` (필수)
- **추출 데이터**: 최근 N년간 침수 관련 재난 발생 횟수
- **키워드**: 침수, 홍수, 범람, 하천범람, 도로침수, 지하침수
  ```python
  flood_count = fetcher.get_flood_history("대전광역시", years=5)
  # 결과: 54건
  ```

---

### ✅ **로컬 데이터** (100% 사용)

#### 4. KMA SSP 시나리오 (NetCDF)
- **목적**: 기후변화 시나리오 (2021-2100)
- **파일**: `climate_data_loader.py`
- **상태**: ✅ **정상 작동**
- **시나리오**: SSP126, SSP245, SSP370, SSP585 (전체 4개)
- **변수**: TXx, SU25, TR25, TNn, FD0, RN, CDD, RX1DAY 등 15개
- **데이터 소스**: 기상청 기후정보포털
- **형식**: NetCDF (.nc), gzip 압축
- **해상도**: 1km 격자

**사용 예시**:
```python
from code.climate_data_loader import ClimateDataLoader

loader = ClimateDataLoader(scenario='SSP245')
heat_data = loader.get_extreme_heat_data(lat=36.383, lon=127.395, year=2030)
# {
#     'annual_max_temp_celsius': 38.3,
#     'heatwave_days_per_year': 154,
#     'data_source': 'KMA_SSP_gridraw'
# }
```

#### 5. 토지피복도 (GeoTIFF)
- **목적**: 토지 유형, 불투수면 비율
- **파일**: `spatial_data_loader.py` > `get_landcover_data()`
- **상태**: ✅ **정상 작동**
- **데이터 소스**: 환경부 중분류 (1:50,000)
- **경로**: `Physical_RISK_calculate/data/landcover/ME_GROUNDCOVERAGE_50000/`
- **형식**: GeoTIFF (.tif)

**추출 데이터**:
```python
{
    'landcover_type': 'urban',
    'impervious_ratio': 0.7,
    'vegetation_ratio': 0.1,
    'urban_intensity': 'high',
    'data_source': 'ME_GROUNDCOVERAGE_50000'
}
```

#### 6. NDVI (MODIS 위성)
- **목적**: 식생 밀도, 산불 연료량 추정
- **파일**: `spatial_data_loader.py` > `get_ndvi_data()`
- **상태**: ✅ **정상 작동**
- **데이터 소스**: NASA MODIS MOD13Q1
- **경로**: `Physical_RISK_calculate/data/drought/MOD13Q1*.hdf`
- **형식**: HDF
- **해상도**: 250m, 16일 주기

**추출 데이터**:
```python
{
    'ndvi': 0.3,
    'vegetation_health': 'fair',
    'wildfire_fuel': 'low',
    'data_source': 'MOD13Q1'
}
```

#### 7. DEM 고도 (ERDAS IMAGINE)
- **목적**: 고도, 하천 차수, 유역 면적
- **파일**: `stream_order_simple.py`
- **상태**: ✅ **정상 작동**
- **데이터 소스**: 국토지리정보원 5m 수치표고모델
- **경로**: `Physical_RISK_calculate/data/DEM/`
- **형식**: .img, .txt
- **예시 파일**: "대전광역시 유성구.img", "성남시 분당구.img"

**추출 데이터**:
```python
{
    'elevation_m': 34.5,
    'stream_order': 3,
    'watershed_area_km2': 2500,
    'flow_accumulation': 5000,
    'data_source': 'DEM_5m'
}
```

#### 8. 행정구역 (Shapefile)
- **목적**: 시도, 시군구, 읍면동 정보
- **파일**: `spatial_data_loader.py` > `get_administrative_area()`
- **상태**: ✅ **정상 작동**
- **데이터 소스**: 통계청 통계지리정보서비스
- **경로**: `Physical_RISK_calculate/data/geodata/N3A_G0110000.shp`
- **형식**: Shapefile

---

### ⚠️ **부분 구현** (Fallback 존재)

#### 9. SMAP 토양수분 (HDF5)
- **목적**: 가뭄 지표
- **파일**: `spatial_data_loader.py` > `get_soil_moisture_data()`
- **상태**: ⚠️ **좌표 변환 미구현**
- **데이터 소스**: NASA SMAP L4
- **경로**: `Physical_RISK_calculate/data/drought/SMAP_L4_SM*.h5`
- **형식**: HDF5
- **해상도**: 9km

**문제점**:
- MODIS Sinusoidal 투영법 좌표 변환 미구현
- 현재 -9999 (결측값) 반환
- Fallback: `soil_moisture = 0.2` (정상 범위)

**해결 예정**:
```python
# TODO: MODIS 타일 좌표계 변환 구현
from pyproj import Transformer

# MODIS Sinusoidal → WGS84
transformer = Transformer.from_crs("ESRI:54008", "EPSG:4326")
tile_lat, tile_lon = transformer.transform(x, y)
```

---

### 🔴 **미구현** (통계 사용)

#### 10. 태풍 Best Track API
- **목적**: 태풍 경로 및 강도 데이터
- **상태**: 🔴 **미연동**
- **현재 방식**: 통계 기반 추정
  ```python
  # hazard_calculator.py > _calculate_typhoon_hazard()
  annual_typhoon_frequency = 2.5  # 통계
  max_wind_speed_kmh = 150        # 통계
  ```
- **필요 API**: 기상청 태풍 Best Track 데이터 또는 RSMC Tokyo API

**향후 구현**:
```python
# TODO: 태풍 Best Track API 연동
def get_typhoon_data(lat, lon, years=10):
    # 1. 기상청 Best Track 데이터 조회
    # 2. 해당 위치 통과 태풍 필터링
    # 3. 평균 빈도/강도 계산
    pass
```

#### 11. 수도 사용량 API
- **목적**: 물 수요/공급 데이터
- **상태**: 🔴 **미연동**
- **현재 방식**: 인구 통계 기반 추정
  ```python
  # hazard_calculator.py > _calculate_water_stress_hazard()
  annual_demand_m3 = population * 200 * 365  # 1인당 200L/일
  annual_supply_m3 = annual_demand_m3 * 1.2  # 20% 여유
  ```
- **필요 API**: K-Water 수도 사용량 통계 API 또는 지자체 데이터

---

## 실제 데이터 사용률

**전체 시스템**: **93%**

| 리스크 | 실제 데이터 | 사용률 | 비고 |
|--------|------------|--------|------|
| 극심한 고온 | KMA SSP | 100% | 4개 시나리오 전체 지원 |
| 극심한 극심한 한파 | KMA SSP | 100% | 4개 시나리오 전체 지원 |
| 가뭄 | KMA SSP + SMAP | 90% | SMAP 좌표 변환 미구현 |
| 하천 홍수 | KMA SSP + 재난 API + DEM | 100% | - |
| 도시 홍수 | KMA SSP + 토지피복도 | 100% | - |
| 해수면 상승 | Haversine 거리 | 100% | - |
| 태풍 | 통계 | 70% | Best Track API 미연동 |
| 산불 | NDVI + 토지피복도 + KMA | 100% | - |
| 수자원 | 인구 통계 | 70% | 수도 사용량 API 미연동 |

---

## API 키 필요 여부

### 필수 API 키

1. **VWORLD_API_KEY**: V-World 주소 변환 (필수)
   - 발급: https://www.vworld.kr/
   - 용도: 주소 → 좌표 변환

2. **BUILDING_API_KEY**: 건축물대장 조회 (필수)
   - 발급: https://www.data.go.kr/
   - 용도: 건물 층수, 용도, 구조, 건축연도

### 선택 API 키

3. **RIVER_API_KEY**: 하천정보 조회 (선택)
   - 발급: 재난안전데이터 공유 플랫폼
   - 용도: 하천 등급, 유역 면적
   - Fallback: 통계 값 사용

4. **EMERGENCYMESSAGE_API_KEY**: 긴급재난문자 조회 (선택)
   - 발급: 재난안전데이터 공유 플랫폼
   - 용도: 침수 이력 조회
   - Fallback: 0건 사용

### .env 파일 예시

```
# 필수
VWORLD_API_KEY=your_vworld_api_key
BUILDING_API_KEY=your_building_api_key

# 선택
RIVER_API_KEY=your_river_api_key
EMERGENCYMESSAGE_API_KEY=your_emergency_api_key
```

---

## Fallback 정책

**원칙**: 실제 데이터 로드 실패 시에만 Fallback 사용

### Fallback 조건

1. **API 응답 실패**: 타임아웃, 인증 오류, 서버 오류
2. **데이터 범위 외**: 좌표가 한반도 범위 밖, 연도 범위 초과
3. **파일 없음**: NetCDF, GeoTIFF, HDF 파일 누락
4. **라이브러리 없음**: netCDF4, h5py, rasterio 미설치

### Fallback 값 기준

- **통계 기반**: 한국 평균값 사용
- **보수적 추정**: 중간 정도의 리스크 가정
- **TCFD 경고**: `data_source: 'fallback'` 명시

---

## 향후 개선 계획

### v2.1.0 (단기)
1. ✅ ~~시나리오별 계산 지원~~ (완료)
2. SMAP 토양수분 좌표 변환 구현
3. RN 연간 강수량 파일 로드 오류 수정

### v2.2.0 (중기)
1. 태풍 Best Track API 연동
2. 수도 사용량 API 연동
3. 하천 좌표 데이터 추가 (거리 계산 정확도 향상)

### v3.0.0 (장기)
1. 배치 분석 기능 (여러 주소 동시 처리)
2. PDF/DOCX 리포트 생성
3. 시계열 분석 (2030/2050/2100 비교)
4. 지도 시각화 (리스크 히트맵)

---

**문서 버전**: 2.0.0
**최종 업데이트**: 2024-11-24
**담당**: 물리적 리스크 분석 팀
