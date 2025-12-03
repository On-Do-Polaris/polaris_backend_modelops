# SKALA Physical Risk AI - 통합 ERD

> 최종 수정일: 2025-12-03
> 버전: v05 (Application DB 8개 테이블 생성 완료)

---

## 개요

SKALA Physical Risk AI 시스템은 **2개의 분리된 데이터베이스**를 사용합니다:

| 데이터베이스 | 포트 | 서비스 | 용도 |
|-------------|------|--------|------|
| **skala_datawarehouse** | 5434 | FastAPI + ModelOPS | 기후 데이터, AI 분석 결과 |
| **skala_application** | 5435 | SpringBoot | 사용자, 사업장, 리포트 |

---

## 1. Datawarehouse (FastAPI + ModelOPS 공유)

### 1.1 테이블 개요

| 카테고리 | 테이블 수 | 데이터 소스 | 설명 |
|----------|----------|-------------|------|
| Location | 3개 | **Local ETL** | 위치 참조 (행정구역, 격자) |
| Climate Data | 17개 | **Local ETL** | 기후 데이터 (SSP 시나리오별) |
| Raw Raster | 3개 | **Local ETL** | DEM, 가뭄, 토지피복도 래스터 |
| Reference Data | 3개 | **Local ETL** | 기상관측소, 물스트레스 순위 |
| Site Energy | 2개 | **Local ETL** | 사업장 에너지 사용량 |
| ModelOPS | 2개 | **서비스 생성** | P(H), Hazard Score 결과 |
| API Cache | 11개 | **OpenAPI ETL** | 외부 API 캐시 |
| **합계** | **41개** | | |

### 1.1.1 데이터 소스별 테이블 분류

#### Local ETL (28개 테이블) - 로컬 파일 적재
```
Location (3개):        location_admin, location_grid, sea_level_grid
Climate Data (17개):   tamax_data, tamin_data, ta_data, rn_data, ws_data,
                       rhm_data, si_data, spei12_data, csdi_data, wsdi_data,
                       rx1day_data, rx5day_data, cdd_data, rain80_data,
                       sdii_data, ta_yearly_data, sea_level_data
Raw Raster (3개):      raw_dem, raw_drought, raw_landcover
Reference Data (3개):  weather_stations, grid_station_mappings, water_stress_rankings
Site Energy (2개):     site_dc_power_usage, site_campus_energy_usage
```

#### OpenAPI ETL (11개 테이블) - 외부 API 적재
```
API Cache (11개):      api_buildings, api_wamis, api_wamis_stations,
                       api_river_info, api_emergency_messages,
                       api_typhoon_info, api_typhoon_track, api_typhoon_td,
                       api_typhoon_besttrack, api_disaster_yearbook,
                       api_vworld_geocode
```

#### 서비스 생성 (2개 테이블) - ModelOPS 계산 결과
```
ModelOPS (2개):        probability_results, hazard_results
```

---

### 1.2 Location Tables (3개)

위치 정보를 저장하며, 모든 기후 데이터의 공간 참조 기준이 됩니다.

#### location_admin - 행정구역 위치 정보

**필요 이유:** 일별 기후 데이터(tamax_data, tamin_data)가 시군구 레벨로 제공되어 행정구역 기준 조회 필요

**사용처:**
- FastAPI: 좌표 → 행정구역 매핑 (VWorld 역지오코딩 결과와 연계)
- ETL: 일별 기후 데이터 적재 시 admin_id 참조

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| admin_id | SERIAL PK | 행정구역 ID | 기후 테이블의 FK 참조 대상 |
| admin_code | VARCHAR(10) UK | 행정구역 코드 (10자리) | 공공데이터 API 연계 키 |
| admin_name | VARCHAR(100) | 행정구역명 | 표시용 |
| sido_code | VARCHAR(2) | 시도코드 2자리 | 시도 레벨 필터링 |
| sigungu_code | VARCHAR(5) | 시군구코드 5자리 | 시군구 레벨 필터링 |
| emd_code | VARCHAR(10) | 읍면동코드 10자리 | 상세 위치 |
| level | SMALLINT | 1:시도, 2:시군구, 3:읍면동 | 레벨별 집계 |
| geom | GEOMETRY | MULTIPOLYGON EPSG:5174 | 공간 조인 (ST_Contains) |
| centroid | GEOMETRY | POINT EPSG:5174 | 대표점 좌표 |
| population_2020 | INTEGER | 2020년 인구 | Exposure 계산 |
| population_2050 | INTEGER | 2050년 인구 | 미래 Exposure 계산 |

**예상 데이터 규모:** 5,259 rows (5,007 읍면동 + 252 시군구)

---

#### location_grid - 격자점 위치 정보

**필요 이유:** 월별/연별 기후 데이터가 0.01° 격자 레벨로 제공됨

**사용처:**
- FastAPI: 사업장 좌표 → 최근접 격자 매핑
- ModelOPS: 격자별 P(H) 및 Hazard Score 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| grid_id | SERIAL PK | 격자 ID | 기후 테이블의 FK 참조 대상 |
| longitude | NUMERIC(9,6) | 경도 (124.5~132.0) | 격자 위치 식별 |
| latitude | NUMERIC(8,6) | 위도 (33.0~39.0) | 격자 위치 식별 |
| geom | GEOMETRY | POINT EPSG:4326 | 공간 조인 (ST_DWithin) |

**예상 데이터 규모:** 451,351 rows (601 × 751 격자)

---

#### sea_level_grid - 해수면 격자점 위치 정보

**필요 이유:** 해수면 상승 데이터는 별도의 저해상도 격자(1° 간격)로 제공됨

**사용처:**
- FastAPI: 해안 사업장의 coastal_flood 위험도 계산
- ModelOPS: 해수면 상승 시나리오 기반 Hazard 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| grid_id | SERIAL PK | 격자 ID | sea_level_data FK 참조 대상 |
| longitude | NUMERIC(9,6) | 경도 (124.50~131.50) | 해수면 격자 위치 |
| latitude | NUMERIC(8,6) | 위도 (33.49~42.14) | 해수면 격자 위치 |
| geom | GEOMETRY | POINT EPSG:4326 | 공간 조인 |

**예상 데이터 규모:** 80 rows (10 × 8 격자)

---

### 1.3 Climate Data Tables (17개)

모든 기후 테이블은 **Wide Format** (SSP 컬럼 방식)을 사용합니다:
- `ssp1`: SSP1-2.6 시나리오 (지속가능 발전)
- `ssp2`: SSP2-4.5 시나리오 (중간 경로)
- `ssp3`: SSP3-7.0 시나리오 (지역 경쟁)
- `ssp5`: SSP5-8.5 시나리오 (화석연료 의존)

#### 일별 데이터 (행정구역 레벨)

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| tamax_data | 일 최고기온 (°C) | 폭염(high_temperature) Hazard 계산 | (time, admin_id) | ~7.63M |
| tamin_data | 일 최저기온 (°C) | 한파(cold_wave) Hazard 계산 | (time, admin_id) | ~7.63M |

**컬럼 구조:**
- `time` (DATE): 관측일
- `admin_id` (INTEGER FK): location_admin 참조
- `ssp1~ssp5` (REAL): 각 시나리오별 기온값

---

#### 월별 데이터 (격자 레벨)

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| ta_data | 평균기온 (°C) | 폭염/한파 기준 온도 | (observation_date, grid_id) | ~108M |
| rn_data | 강수량 (mm) | 홍수/가뭄 Hazard, 산불 위험도 | (observation_date, grid_id) | ~108M |
| ws_data | 풍속 (m/s) | 태풍(typhoon) Hazard 계산 | (observation_date, grid_id) | ~108M |
| rhm_data | 상대습도 (%) | 산불(wildfire) 위험도 계산 | (observation_date, grid_id) | ~108M |
| si_data | 일사량 (MJ/m²) | 태양광 발전량, 열스트레스 | (observation_date, grid_id) | ~108M |
| spei12_data | SPEI 12개월 | 가뭄(drought) Hazard 핵심 지표 | (observation_date, grid_id) | ~108M |

**컬럼 구조:**
- `grid_id` (INTEGER FK): location_grid 참조
- `observation_date` (DATE): 관측 월 (YYYY-MM-01)
- `ssp1~ssp5` (REAL): 각 시나리오별 값

---

#### 연별 데이터 (격자 레벨)

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| csdi_data | 한랭야 계속기간 지수 (일) | 한파(cold_wave) 장기 추세 | (year, grid_id) | ~9M |
| wsdi_data | 온난야 계속기간 지수 (일) | 폭염(high_temperature) 장기 추세 | (year, grid_id) | ~9M |
| rx1day_data | 1일 최다강수량 (mm) | 내륙홍수(inland_flood) 극값 분석 | (year, grid_id) | ~9M |
| rx5day_data | 5일 최다강수량 (mm) | 내륙홍수(inland_flood) 극값 분석 | (year, grid_id) | ~9M |
| cdd_data | 연속 무강수일 (일) | 가뭄(drought) 장기 추세 | (year, grid_id) | ~9M |
| rain80_data | 80mm 이상 강수일수 (일) | 도시홍수(urban_flood) 위험도 | (year, grid_id) | ~9M |
| sdii_data | 강수강도 (mm/일) | 집중호우 분석 | (year, grid_id) | ~9M |
| ta_yearly_data | 연평균 기온 (°C) | 기후변화 장기 추세 | (year, grid_id) | ~9M |

**컬럼 구조:**
- `grid_id` (INTEGER FK): location_grid 참조
- `year` (INTEGER): 관측 연도 (2021~2100)
- `ssp1~ssp5` (REAL): 각 시나리오별 값

---

#### 해수면 상승 데이터

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| sea_level_data | 해수면 상승 (cm) | 해안홍수(coastal_flood) Hazard | (year, grid_id) | ~1,720 |

**컬럼 구조:**
- `grid_id` (INTEGER FK): sea_level_grid 참조
- `year` (INTEGER): 관측 연도 (2015~2100)
- `ssp1~ssp5` (REAL): 각 시나리오별 해수면 상승값

---

### 1.4 ModelOPS Tables (2개)

ModelOPS가 기후 데이터 기반으로 계산한 P(H) 확률 및 Hazard Score 결과를 저장합니다.

**위험 유형 (risk_type) 9가지:**
1. `coastal_flood` - 해안 홍수 (해수면 상승, 폭풍 해일)
2. `cold_wave` - 한파 (극심한 저온)
3. `drought` - 가뭄 (SPEI, 강수량 부족)
4. `high_temperature` - 폭염 (극심한 고온)
5. `inland_flood` - 내륙 홍수 (하천 범람)
6. `typhoon` - 태풍 (강풍, 집중호우)
7. `urban_flood` - 도시 홍수 (내수 침수)
8. `water_scarcity` - 물부족 (수자원 스트레스)
9. `wildfire` - 산불 (건조, 고온)

---

#### probability_results - P(H) 확률 결과

**필요 이유:** ModelOPS가 기후 데이터 기반으로 계산한 위험 발생 확률 저장

**사용처:**
- ModelOPS: probability_calculate 에이전트가 결과 저장 (save_probability_results)
- FastAPI: AI Agent가 조회하여 Physical Risk Score 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 (location_grid와 조인) |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 위험 종류 구분 |
| probability | REAL | P(H) 확률값 (0.0~1.0) | 위험 발생 확률 |
| bin_data | JSONB | 히스토그램 상세 | 확률 분포 시각화용 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 |

**예상 데이터 규모:** ~4.06M rows (451,351 grids × 9 risk types)

---

#### hazard_results - Hazard Score 결과

**필요 이유:** ModelOPS가 계산한 위험도 점수 저장 (Physical Risk Formula: H × E × V의 H 부분)

**사용처:**
- ModelOPS: hazard_calculate 에이전트가 결과 저장 (save_hazard_results)
- FastAPI: AI Agent가 조회하여 최종 Physical Risk Score 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 위험 종류 구분 |
| hazard_score | REAL | 원본 위험도 점수 | 모델 출력값 |
| hazard_score_100 | REAL | 0-100 정규화 점수 | UI 표시용 |
| hazard_level | VARCHAR(20) | 위험 등급 | 낮음/보통/높음/매우높음 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 |

**위험 등급 기준:**
- 낮음: < 30
- 보통: 30 ~ 60
- 높음: 60 ~ 80
- 매우높음: > 80

**예상 데이터 규모:** ~4.06M rows (451,351 grids × 9 risk types)

---

### 1.5 Raw Raster Tables (3개)

PostGIS RASTER 타입으로 저장되는 원시 래스터 데이터입니다.

#### raw_dem - DEM 원시 래스터

**필요 이유:** 고도/경사도 데이터로 홍수 취약성, 산불 위험도 계산에 활용

**사용처:**
- FastAPI: 사업장 위치의 고도/경사 조회
- ModelOPS: Vulnerability 계산 보조 데이터

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| rid | SERIAL PK | 래스터 타일 ID | 자동 생성 |
| rast | RASTER | PostGIS RASTER | 고도 데이터 저장 |
| filename | TEXT | 원본 파일명 | 데이터 추적용 |

---

#### raw_drought - 가뭄 원시 래스터

**필요 이유:** MODIS/SMAP 위성 데이터로 토양수분 기반 가뭄 분석

**사용처:**
- FastAPI: 실시간 가뭄 상황 모니터링
- ModelOPS: drought Hazard 계산 보조

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| rid | SERIAL PK | 래스터 타일 ID | 자동 생성 |
| rast | RASTER | PostGIS RASTER | 가뭄 지수 저장 |
| filename | TEXT | 원본 HDF/H5 파일명 | 데이터 추적용 |

---

#### raw_landcover - 토지피복도 래스터

**필요 이유:** 도시 불투수 면적 계산 → 도시홍수(urban_flood) Hazard 계산에 필수

**사용처:**
- FastAPI: 사업장 위치의 토지피복 유형 조회
- ModelOPS: urban_flood Vulnerability 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| rid | SERIAL PK | 래스터 타일 ID | 자동 생성 |
| rast | RASTER | PostGIS RASTER | 토지피복 분류 코드 |
| filename | TEXT | 원본 파일명 | 데이터 추적용 |

**데이터 소스:** 환경부 토지피복도 (Static)

---

### 1.6 Reference Data Tables (3개)

외부 데이터 소스와의 매핑 및 참조 데이터를 저장합니다.

#### weather_stations - 기상 관측소 정보

**필요 이유:** WAMIS 유량 관측소와 격자 매핑을 위한 메타데이터

**사용처:**
- ETL: 격자-관측소 매핑 계산
- FastAPI: 관측소 기반 데이터 조회

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| station_id | SERIAL PK | 관측소 ID | 내부 식별자 |
| obscd | VARCHAR(10) UK | 관측소 코드 | WAMIS API 연계 키 |
| obsnm | VARCHAR(100) | 관측소명 | 표시용 |
| bbsnnm | VARCHAR(50) | 대권역 유역명 | 유역 분류 |
| basin_code | INTEGER | 유역 코드 (1~6) | 권역별 필터링 |
| latitude | NUMERIC(10,7) | 위도 | 공간 조인 |
| longitude | NUMERIC(11,7) | 경도 | 공간 조인 |
| geom | GEOMETRY | POINT EPSG:4326 | 공간 인덱스 |

**예상 데이터 규모:** 1,086 rows

---

#### grid_station_mappings - 격자-관측소 매핑

**필요 이유:** 격자점과 최근접 관측소 3개의 사전 계산된 매핑

**사용처:**
- FastAPI: 격자점 기준 가중 평균 계산
- ModelOPS: 관측소 데이터 격자 보간

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| mapping_id | SERIAL PK | 매핑 ID | 내부 식별자 |
| grid_lat | NUMERIC(8,6) | 격자점 위도 | 격자 위치 |
| grid_lon | NUMERIC(9,6) | 격자점 경도 | 격자 위치 |
| station_rank | SMALLINT | 최근접 순위 (1~3) | 가중치 계산용 |
| obscd | VARCHAR(10) | 관측소 코드 | weather_stations 참조 |
| distance_km | NUMERIC(8,4) | 거리 (km) | 역거리 가중치 계산 |

**예상 데이터 규모:** ~292k rows (97,377 grids × 3 stations)

---

#### water_stress_rankings - WRI Aqueduct 물 스트레스 순위

**필요 이유:** WRI Aqueduct 4.0 데이터로 전세계 물 스트레스 순위 제공

**사용처:**
- FastAPI: water_scarcity Hazard 계산
- 리포트: 글로벌 물부족 비교 분석

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| ranking_id | SERIAL PK | 순위 ID | 내부 식별자 |
| gid_0 | VARCHAR(3) | 국가 코드 (ISO) | 국가 필터링 (KOR) |
| name_0 | VARCHAR(100) | 국가명 | 표시용 |
| year | INTEGER | 전망 연도 | 2030, 2050, 2080 |
| scenario | VARCHAR(20) | 시나리오 | opt (낙관), pes (비관) |
| indicator_name | VARCHAR(50) | 지표명 | bws (baseline water stress) |
| score | NUMERIC(12,8) | 스코어 (0~5) | 물 스트레스 정도 |
| cat | SMALLINT | 카테고리 (0~4) | 위험도 단계 |

**예상 데이터 규모:** 161,731 rows

---

### 1.7 Site Energy Tables (2개)

사업장 에너지 사용량 데이터를 저장합니다.

#### site_dc_power_usage - 데이터센터 전력 사용량

**필요 이유:** Agent 2 (Impact Analysis)가 HEV 가중치 계산에 사용

**사용처:**
- FastAPI Agent 2: IT전력/냉방전력 비율로 열취약성(HEV) 계산
- ESG 보고서: 데이터센터 PUE 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| power_usage_id | UUID PK | 사용량 ID | 내부 식별자 |
| site_id | UUID | 사업장 ID | Application DB 참조 |
| it_power_kwh | REAL | IT 장비 전력 (kWh) | HEV 가중치 분자 |
| cooling_power_kwh | REAL | 냉방 전력 (kWh) | HEV 가중치 분모 |
| total_power_kwh | REAL | 총 전력 (kWh) | PUE 계산 |
| measurement_year | INTEGER | 측정 연도 | 시계열 분석 |
| measurement_month | INTEGER | 측정 월 (1-12) | 월별 추세 |

---

#### site_campus_energy_usage - 캠퍼스 에너지 사용량

**필요 이유:** ESG 보고서 및 탄소 배출량 계산에 사용

**사용처:**
- FastAPI: ESG 대시보드 데이터 제공
- 리포트: 탄소 배출량 추세 분석

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| energy_usage_id | UUID PK | 사용량 ID | 내부 식별자 |
| site_id | UUID | 사업장 ID | Application DB 참조 |
| total_power_kwh | REAL | 총 전력 (kWh) | 전력 사용량 |
| gas_usage_m3 | REAL | 가스 사용량 (m³) | 난방/취사 |
| water_usage_m3 | REAL | 수도 사용량 (m³) | 용수 사용량 |
| co2_emissions_ton | REAL | 탄소 배출량 (tCO2eq) | ESG 지표 |

---

### 1.8 API Cache Tables (11개)

외부 API 데이터를 캐싱하여 저장합니다.

| 테이블 | API 소스 | 사용처 |
|--------|----------|--------|
| api_buildings | 국토교통부 건축물대장 | Vulnerability 계산 (건물 구조, 노후도) |
| api_wamis | WAMIS 용수이용량 | 물부족 Hazard 계산 |
| api_wamis_stations | WAMIS 관측소 | 유량 관측소 메타데이터 |
| api_river_info | 재난안전데이터 하천정보 | 하천홍수 Hazard 계산 |
| api_emergency_messages | 재난안전데이터 재난문자 | 재난 이력 추적 |
| api_typhoon_info | 기상청 태풍정보 | AAL 분석 - 태풍 메타 |
| api_typhoon_track | 기상청 태풍경로 | AAL 분석 - 태풍 경로 |
| api_typhoon_td | 기상청 열대저압부 | 태풍 전단계 추적 |
| api_typhoon_besttrack | 기상청 베스트트랙 | 정밀 태풍 분석 |
| api_disaster_yearbook | 행정안전부 재해연보 | 과거 피해 통계 |
| api_vworld_geocode | VWorld 역지오코딩 | 좌표 → 주소 변환 |

---

## 2. Application DB (SpringBoot)

### 2.1 테이블 개요

| 카테고리 | 테이블 수 | 설명 |
|----------|----------|------|
| User | 2개 | 사용자 인증 (basic.dbml 기준) |
| Site | 1개 | 사업장 관리 (basic.dbml 기준) |
| Analysis | 2개 | AI 분석 작업/결과 (SpringBoot Entity) |
| Report | 1개 | 리포트 관리 (SpringBoot Entity) |
| Meta | 2개 | 메타데이터 (SpringBoot Entity) |
| **합계** | **8개** | 생성 완료 ✓ |

> **SQL 파일:**
> - `01_create_basic_tables.sql` - users, sites, password_reset_tokens (basic.dbml 기준)
> - `02_create_additional_tables.sql` - analysis_jobs, analysis_results, reports, industries, hazard_types

---

### 2.2 User Tables (basic.dbml 기준)

#### users - 사용자 정보

**필요 이유:** 사용자 인증

**사용처:**
- SpringBoot: AuthController (로그인, 회원가입)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 사용자 ID | 내부 식별자 |
| email | VARCHAR(255) UK | 이메일 | 로그인 ID |
| name | VARCHAR(100) | 이름 | 표시용 |
| password | VARCHAR(255) | 비밀번호 (암호화) | 인증 |
| language | VARCHAR(10) | 언어 (ko/en) | UI 언어 설정 |

---

#### password_reset_tokens - 비밀번호 재설정 토큰

**필요 이유:** 이메일 기반 비밀번호 재설정 기능

**사용처:**
- SpringBoot: AuthController (비밀번호 재설정)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 토큰 ID | 내부 식별자 |
| user_id | UUID FK | 사용자 ID | users 참조 |
| token | VARCHAR(255) UK | 재설정 토큰 | URL 파라미터 |
| expires_at | TIMESTAMP | 만료 시간 | 토큰 유효성 |
| created_at | TIMESTAMP | 생성 시간 | 기본값 now() |

---

### 2.3 Site Tables (basic.dbml 기준)

#### sites - 사업장 정보

**필요 이유:** 기후 리스크 분석 대상 사업장 정보 관리

**사용처:**
- SpringBoot: SiteController (사업장 CRUD)
- FastAPI: 분석 요청 시 사업장 정보 전달
- ModelOPS: 좌표 기반 격자 매핑

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 사업장 ID | 내부 식별자 |
| user_id | UUID FK | 소유자 ID | users 참조 |
| name | VARCHAR(255) | 사업장 이름 | 표시용 |
| road_address | VARCHAR(500) | 도로명 주소 | 위치 정보 |
| jibun_address | VARCHAR(500) | 지번 주소 | 위치 정보 |
| latitude | DECIMAL(10,8) | 위도 | 격자 매핑에 사용 |
| longitude | DECIMAL(11,8) | 경도 | 격자 매핑에 사용 |
| type | VARCHAR(100) | 업종/유형 | 업종별 분류 |

---

### 2.4 Analysis Tables (SpringBoot Entity 기준)

#### analysis_jobs - AI 분석 작업

**필요 이유:** FastAPI AI Agent 분석 작업 상태 추적

**사용처:**
- SpringBoot: AnalysisController (작업 생성, 상태 조회)
- SpringBoot: AnalysisJobPollingService (상태 폴링)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 작업 ID | 내부 식별자 |
| site_id | UUID FK | 사업장 ID | sites 참조 |
| job_id | VARCHAR(100) UK | FastAPI 작업 ID | API 연동 키 |
| status | VARCHAR(20) | 상태 | QUEUED/RUNNING/COMPLETED/FAILED |
| progress | INTEGER | 진행률 (0-100) | UI 진행바 표시 |
| current_node | VARCHAR(100) | 현재 노드 | LangGraph 노드명 |
| error_code | VARCHAR(50) | 에러 코드 | 에러 분류 |
| error_message | TEXT | 에러 메시지 | 에러 상세 |

---

#### analysis_results - AI 분석 결과

**필요 이유:** FastAPI로부터 받은 분석 결과를 JSON 형태로 저장

**사용처:**
- SpringBoot: AnalysisController (결과 조회)
- SpringBoot: DashboardController (대시보드 데이터)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 결과 ID | 내부 식별자 |
| site_id | UUID FK | 사업장 ID | sites 참조 |
| hazard_type | VARCHAR(50) | 위험 유형 | 9가지 위험 중 하나 |
| analysis_data | JSONB | 분석 결과 | 상세 결과 JSON |
| analyzed_at | TIMESTAMP | 분석 일시 | 결과 신선도 |

---

### 2.5 Report Tables

#### reports - 리포트 정보

**필요 이유:** 생성된 리포트 파일 정보 관리

**사용처:**
- SpringBoot: ReportController (리포트 생성, 다운로드)
- S3: 리포트 PDF 파일 저장

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 리포트 ID | 내부 식별자 |
| site_id | UUID FK | 사업장 ID | sites 참조 |
| site_name | VARCHAR(200) | 사업장명 스냅샷 | 리포트 제목 |
| type | VARCHAR(20) | 유형 | SUMMARY/FULL/GOVERNANCE |
| status | VARCHAR(20) | 상태 | PENDING/GENERATING/COMPLETED/FAILED |
| s3_key | VARCHAR(500) | S3 키 | 파일 위치 |
| file_size | BIGINT | 파일 크기 (bytes) | 다운로드 정보 |
| expires_at | TIMESTAMP | 만료 일시 | 7일 후 자동 삭제 |

---

### 2.6 Meta Tables

#### hazard_types - 위험 요인 메타데이터

**필요 이유:** 시스템에서 지원하는 9가지 위험 유형 정의

**사용처:**
- SpringBoot: MetaController (메타데이터 API)
- Frontend: 드롭다운 선택지

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | SERIAL PK | ID | 내부 식별자 |
| code | VARCHAR(50) UK | 코드 | API 키 (extreme_heat 등) |
| name | VARCHAR(100) | 한글 이름 | 표시용 |
| name_en | VARCHAR(100) | 영문 이름 | 다국어 지원 |
| category | VARCHAR(20) | 카테고리 | TEMPERATURE/WATER/WIND/OTHER |

**초기 데이터 (9개):**
| code | name | category |
|------|------|----------|
| extreme_heat | 극심한 고온 | TEMPERATURE |
| extreme_cold | 극심한 한파 | TEMPERATURE |
| wildfire | 산불 | OTHER |
| drought | 가뭄 | WATER |
| water_stress | 물부족 | WATER |
| sea_level_rise | 해수면 상승 | WATER |
| river_flood | 하천 홍수 | WATER |
| urban_flood | 도시 홍수 | WATER |
| typhoon | 태풍 | WIND |

---

#### industries - 업종 메타데이터

**필요 이유:** 업종별 취약성 계수 관리

**사용처:**
- SpringBoot: MetaController (업종 목록 API)
- FastAPI: 업종별 V(Vulnerability) 계수 조회

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | SERIAL PK | ID | 내부 식별자 |
| code | VARCHAR(50) UK | 코드 | API 키 |
| name | VARCHAR(100) | 업종 이름 | 표시용 |
| description | TEXT | 설명 | 상세 정보 |

---

## 3. 서비스 간 연동

### 3.1 데이터 흐름

```
[사용자 요청]
     ↓
[SpringBoot - Application DB]
   sites → (latitude, longitude)
     ↓
[FastAPI - Datawarehouse]
   location_grid → grid_id
   climate_data → 기후 분석
     ↓
[ModelOPS - Datawarehouse]
   probability_results → P(H)
   hazard_results → Hazard Score
     ↓
[FastAPI - AI Agent]
   H × E × V = Physical Risk Score
     ↓
[SpringBoot - Application DB]
   analysis_results ← JSON 저장
   sites.risk_score ← 캐시 업데이트
```

### 3.2 좌표 → 격자 매핑

```sql
-- Application의 sites 좌표 → Datawarehouse의 grid_id 조회
SELECT g.grid_id
FROM skala_datawarehouse.location_grid g
WHERE g.longitude = ROUND(sites.longitude::numeric, 2)
  AND g.latitude = ROUND(sites.latitude::numeric, 2);
```

---

## 4. ETL 데이터 소스 정리

### 4.1 Local ETL (로컬 파일 적재)

| 테이블 | 데이터 소스 | ETL 스크립트 |
|--------|-------------|--------------|
| location_admin | CTPRVN_EMD.shp | 01_load_admin_regions.py |
| weather_stations | station_info.csv | 02_load_weather_stations.py |
| grid_station_mappings | 계산 생성 | 03_create_grid_station_mapping.py |
| raw_dem | DEM GeoTIFF | 04_load_dem.py |
| raw_drought | MODIS/SMAP HDF | 05_load_drought.py |
| location_grid | 계산 생성 | 06_create_location_grid.py |
| ta_data, rn_data, ... | KMA NetCDF | 07_load_monthly_grid_data.py |
| csdi_data, wsdi_data, ... | KMA NetCDF | 08_load_yearly_grid_data.py |
| sea_level_grid, sea_level_data | KMA NetCDF | 09_load_sea_level.py |
| water_stress_rankings | WRI CSV | 10_load_water_stress.py |
| site_dc_power_usage | Excel | 11_load_site_energy.py |
| site_campus_energy_usage | Excel | 11_load_site_energy.py |

---

### 4.2 OpenAPI ETL (외부 API 적재)

| 테이블 | API 소스 | ETL 스크립트 |
|--------|----------|--------------|
| api_river_info | 재난안전데이터 하천정보 | 01_load_river_info.py |
| api_emergency_messages | 재난안전데이터 긴급재난문자 | 02_load_emergency_messages.py |
| api_vworld_geocode | VWorld 역지오코딩 | 03_load_geocode.py |
| api_typhoon_info | 기상청 태풍정보 | 04_load_typhoon.py |
| api_typhoon_track | 기상청 태풍경로 | 04_load_typhoon.py |
| api_typhoon_td | 기상청 열대저압부 | 04_load_typhoon.py |
| api_wamis | WAMIS 용수이용량 | 05_load_wamis.py |
| api_wamis_stations | WAMIS 관측소 | 06_load_wamis_stations.py |
| api_buildings | 국토교통부 건축물대장 | 07_load_buildings.py |
| api_disaster_yearbook | 행정안전부 재해연보 | 08_load_disaster_yearbook.py |
| api_typhoon_besttrack | 기상청 베스트트랙 | 09_load_typhoon_besttrack.py |

---

## 5. 참조 문서

- SpringBoot 엔티티: `/DB_ALL/springboot/polaris_backend/src/main/java/com/skax/physicalrisk/domain/`
- FastAPI database.py: `/DB_ALL/fastapi/ai_agent/utils/database.py`
- ModelOPS connection.py: `/DB_ALL/modelops/modelops/database/connection.py`
- Datawarehouse SQL: `/db_final_1202/db/sql/datawarehouse/`

---

*문서 작성: Claude Code*
*최종 수정: 2025-12-03*
