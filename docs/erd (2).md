# SKALA Physical Risk AI - 통합 ERD

> 최종 수정일: 2025-12-10
> 버전: v10 (site_risk_results, site_risk_summary, candidate_sites 추가)

---

## 개요

SKALA Physical Risk AI 시스템은 **GCP Cloud SQL**의 **단일 PostgreSQL 인스턴스** 내에 **2개의 데이터베이스**를 사용합니다:

| 데이터베이스 | 포트 | 서비스 | 용도 |
|-------------|------|--------|------|
| **datawarehouse** | 5432 | FastAPI + ModelOPS | 기후 데이터, AI 분석 결과 |
| **application** | 5432 | SpringBoot | 사용자, 사업장, 리포트 |

---

## 1. Datawarehouse (FastAPI + ModelOPS 공유)

### 1.1 테이블 개요

| 카테고리 | 테이블 수 | 데이터 소스 | 설명 |
|----------|----------|-------------|------|
| Location | 3개 | **Local ETL** | 위치 참조 (행정구역, 격자) |
| Climate Data | 17개 | **Local ETL** | 기후 데이터 (SSP 시나리오별) |
| Raw Raster | 3개 | **Local ETL** | DEM, 가뭄, 토지피복도 래스터 |
| Reference Data | 3개 | **Local ETL** | 기상관측소, 물스트레스 순위 |
| Site Additional | 2개 | **Local ETL / API** | 사업장 추가 데이터 + 배치 작업 |
| Site Risk | 3개 | **서비스 생성** | Site별 리스크 결과 + 후보지 |
| ModelOPS | 5개 | **서비스 생성** | H × E × V 계산 결과 |
| API Cache | 11개 | **OpenAPI ETL** | 외부 API 캐시 |
| **합계** | **47개** | | |

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
Site Additional (2개): site_additional_data, batch_jobs
```

#### OpenAPI ETL (11개 테이블) - 외부 API 적재
```
API Cache (11개):      building_aggregate_cache, api_wamis, api_wamis_stations,
                       api_river_info, api_emergency_messages,
                       api_typhoon_info, api_typhoon_track, api_typhoon_td,
                       api_typhoon_besttrack, api_disaster_yearbook,
                       api_vworld_geocode
```

#### 서비스 생성 (8개 테이블) - ModelOPS/FastAPI 계산 결과
```
ModelOPS (5개):        probability_results, hazard_results, exposure_results,
                       vulnerability_results, aal_scaled_results
Site Risk (3개):       site_risk_results, site_risk_summary, candidate_sites
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
| population_2025 | INTEGER | 2025년 추정 인구 | 인구 전망 |
| population_2030 | INTEGER | 2030년 추정 인구 | 인구 전망 |
| population_2035 | INTEGER | 2035년 추정 인구 | 인구 전망 |
| population_2040 | INTEGER | 2040년 추정 인구 | 인구 전망 |
| population_2045 | INTEGER | 2045년 추정 인구 | 인구 전망 |
| population_2050 | INTEGER | 2050년 인구 | 미래 Exposure 계산 |
| population_change_2020_2050 | INTEGER | 2020-2050 순증감 (명) | 보고서용 |
| population_change_rate_percent | NUMERIC(5,2) | 2020-2050 증감률 (%) | 보고서용 |

**예상 데이터 규모:** 5,259 rows (5,007 읍면동 + 252 시군구)

**보고서 활용 예시:**
```
"대상 지역은 2020년 인구 xxx명에서 2050년 xxx명으로
[xx% 증가/감소]할 것으로 예상되는 [인구 증가/감소 지역]입니다."
```

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

### 1.4 ModelOPS Tables (5개)

ModelOPS가 H × E × V = Risk 공식에 따라 계산한 결과를 저장합니다.

> ⚠️ **변경 이력 (2025-12-03)**: probability_results 테이블 컬럼 수정 (probability → aal, bin_probabilities), 3개 테이블 추가 (exposure_results, vulnerability_results, aal_scaled_results)

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
| aal | REAL | 연간 평균 손실률 (0.0~1.0) | AAL 계산 기초값 |
| bin_probabilities | JSONB | bin별 발생확률 배열 | [0.65, 0.25, 0.08, ...] |
| bin_data | JSONB | 히스토그램 상세 | 하위 호환성 유지 |
| calculation_details | JSONB | 계산 상세정보 | 모델 파라미터 기록 |
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

#### exposure_results - E (노출도) 결과

**필요 이유:** ModelOPS Exposure Agent가 계산한 자산 노출 정도 저장

**사용처:**
- ModelOPS: exposure_calculate 에이전트가 결과 저장
- FastAPI: H × E × V 계산에 사용

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 위험 종류 구분 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 |
| exposure_score | REAL | 노출도 점수 (0.0~1.0) | E 값 |
| proximity_factor | REAL | 근접도 계수 | 위험원 근접성 |
| normalized_asset_value | REAL | 정규화 자산가치 | 자산 규모 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 |

**예상 데이터 규모:** ~4.06M rows (451,351 grids × 9 risk types)

---

#### vulnerability_results - V (취약성) 결과

**필요 이유:** ModelOPS Vulnerability Agent가 계산한 건물 특성 기반 취약성 저장

**사용처:**
- ModelOPS: vulnerability_calculate 에이전트가 결과 저장
- FastAPI: H × E × V 계산에 사용

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 위험 종류 구분 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 |
| vulnerability_score | REAL | 취약성 점수 (0~100) | V 값 |
| vulnerability_level | VARCHAR(20) | 등급 | very_low/low/medium/high/very_high |
| factors | JSONB | 취약성 요인 상세 | 건물 연식, 구조 등 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 |

**예상 데이터 규모:** ~4.06M rows (451,351 grids × 9 risk types)

---

#### aal_scaled_results - AAL 최종 결과

**필요 이유:** ModelOPS AAL Scaling Agent가 계산한 취약성 보정 연간 평균 손실률 저장

**사용처:**
- FastAPI: 최종 Physical Risk Score 계산
- 리포트: 예상 손실액 산출

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 위험 종류 구분 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 |
| base_aal | REAL | 기본 AAL | probability_results.aal |
| vulnerability_scale | REAL | F_vuln (0.9~1.1) | 취약성 스케일 계수 |
| final_aal | REAL | 최종 AAL | base_aal × F_vuln × (1-insurance_rate) |
| insurance_rate | REAL | 보험 보전율 (0~1) | 보험 가입률 |
| expected_loss | BIGINT | 예상 손실액 (원) | final_aal × asset_value |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 |

**계산 공식:**
```
F_vuln = 0.9 + (V_score / 100) × 0.2  (범위: 0.9 ~ 1.1)
final_aal = base_aal × F_vuln × (1 - insurance_rate)
expected_loss = final_aal × asset_value
```

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
| sbsncd | VARCHAR(20) | 소권역 유역 코드 | 상세 유역 분류 |
| mngorg | VARCHAR(100) | 관리기관 | 기관 정보 |
| minyear | INTEGER | 데이터 시작 연도 | 데이터 범위 |
| maxyear | INTEGER | 데이터 종료 연도 | 데이터 범위 |
| basin_code | INTEGER | 유역 코드 (1~6) | 권역별 필터링 |
| basin_name | VARCHAR(50) | 유역명 | 표시용 |
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
| basin_code | INTEGER | 유역 코드 | 권역 분류 |
| basin_name | VARCHAR(50) | 유역명 | 표시용 |
| station_rank | SMALLINT | 최근접 순위 (1~3) | 가중치 계산용 |
| obscd | VARCHAR(10) | 관측소 코드 | weather_stations 참조 |
| obsnm | VARCHAR(100) | 관측소명 | 표시용 |
| station_lat | NUMERIC(10,7) | 관측소 위도 | 관측소 위치 |
| station_lon | NUMERIC(11,7) | 관측소 경도 | 관측소 위치 |
| distance_km | NUMERIC(8,4) | 거리 (km) | 역거리 가중치 계산 |
| geom | GEOMETRY | 격자점 POINT | 공간 조인 |

**UNIQUE 제약조건:** (grid_lat, grid_lon, station_rank)

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
| gid_1 | VARCHAR(20) | 지역 코드 | 국가 내 세부 지역 |
| name_0 | VARCHAR(100) | 국가명 | 표시용 |
| name_1 | VARCHAR(200) | 지역명 | 표시용 |
| year | INTEGER | 전망 연도 | 2030, 2050, 2080 |
| scenario | VARCHAR(20) | 시나리오 | opt (낙관), pes (비관) |
| indicator_name | VARCHAR(50) | 지표명 | bws (baseline water stress) |
| weight | VARCHAR(20) | 가중치 유형 | Dom (가정용), Ind (산업용) |
| score | NUMERIC(12,8) | 스코어 (0~5) | 물 스트레스 정도 |
| score_ranked | INTEGER | 순위 | 전세계 대비 순위 |
| cat | SMALLINT | 카테고리 (0~4) | 위험도 단계 |
| label | VARCHAR(100) | 레이블 | 위험도 설명 |
| un_region | VARCHAR(100) | UN 지역 | UN 지역 구분 |
| wb_region | VARCHAR(100) | 세계은행 지역 | WB 지역 구분 |

**예상 데이터 규모:** 161,731 rows

---

### 1.7 Site Additional Data Tables (2개)

사업장 추가 데이터 및 배치 작업 상태를 저장합니다.

> ⚠️ **변경 이력 (2025-12-03)**: 기존 `site_dc_power_usage`, `site_campus_energy_usage` 테이블이 `site_additional_data`로 통합되었습니다.

#### site_additional_data - 사업장 추가 데이터

**필요 이유:** 사용자가 제공하는 추가 데이터를 범용적으로 저장

**사용처:**
- FastAPI: 전력, 보험, 건물 정보 등 사용자 제공 데이터 조회
- Agent 2 (Impact Analysis): HEV 가중치 계산

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 레코드 ID | 내부 식별자 |
| site_id | UUID | 사업장 ID | Application DB 참조 |
| data_category | VARCHAR(50) | 데이터 카테고리 | building/asset/power/insurance/custom |
| raw_text | TEXT | 원본 텍스트 | PDF 추출 등 |
| structured_data | JSONB | 정형화된 데이터 | 구조화된 JSON |
| file_name | VARCHAR(255) | 업로드 파일명 | 파일 추적 |
| file_s3_key | VARCHAR(500) | S3 저장 키 | 파일 위치 |
| file_size | BIGINT | 파일 크기 (bytes) | 파일 정보 |
| file_mime_type | VARCHAR(100) | MIME 타입 | 파일 타입 |
| metadata | JSONB | 추가 메타데이터 | 확장 정보 |
| uploaded_by | UUID | 업로드 사용자 ID | 추적 |
| uploaded_at | TIMESTAMP | 업로드 시점 | 추적 |
| expires_at | TIMESTAMP | 만료 시점 | 임시 데이터 관리 |

**UNIQUE 제약조건:** (site_id, data_category, file_name)

**사용 예시 (전력 데이터):**
```json
{
  "data_category": "power",
  "structured_data": {
    "it_power_kwh": 25000,
    "cooling_power_kwh": 8000,
    "total_power_kwh": 40000
  }
}
```

---

#### batch_jobs - 배치 작업 상태 추적

**필요 이유:** 후보지 추천, 대량 분석 등 비동기 작업 상태 추적

**사용처:**
- FastAPI: 배치 작업 진행률 조회
- Frontend: 작업 상태 폴링

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| batch_id | UUID PK | 배치 작업 ID | 내부 식별자 |
| job_type | VARCHAR(50) | 작업 유형 | site_recommendation/bulk_analysis/data_export |
| status | VARCHAR(20) | 상태 | queued/running/completed/failed/cancelled |
| progress | INTEGER | 진행률 (0-100) | UI 진행바 |
| total_items | INTEGER | 전체 항목 수 | 작업 규모 |
| completed_items | INTEGER | 완료 항목 수 | 진행 현황 |
| failed_items | INTEGER | 실패 항목 수 | 에러 추적 |
| input_params | JSONB | 입력 파라미터 | 재실행용 |
| results | JSONB | 결과 데이터 | 배치 결과 |
| error_message | TEXT | 에러 메시지 | 에러 상세 |
| error_stack_trace | TEXT | 스택 트레이스 | 디버깅 |
| estimated_duration_minutes | INTEGER | 예상 소요 시간 | UI 표시 |
| actual_duration_seconds | INTEGER | 실제 소요 시간 | 성능 추적 |
| created_at | TIMESTAMP | 생성 시점 | 기록 |
| started_at | TIMESTAMP | 시작 시점 | 기록 |
| completed_at | TIMESTAMP | 완료 시점 | 기록 |
| expires_at | TIMESTAMP | 만료 시점 | 결과 보관 (예: 7일) |
| created_by | UUID | 생성 사용자 ID | 추적 |

---

### 1.8 API Cache Tables (11개)

외부 API 데이터를 캐싱하여 저장합니다.

| 테이블 | API 소스 | 사용처 |
|--------|----------|--------|
| building_aggregate_cache | 국토교통부 건축물대장 | Vulnerability 계산 (번지 단위 집계) |
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

### 1.9 Site Risk Tables (3개)

Site별 최종 리스크 분석 결과 및 이전 후보지 정보를 저장합니다.

> ⚠️ **신규 추가 (2025-12-10)**: site_risk_results, site_risk_summary, candidate_sites 테이블 추가
> ⚠️ **스키마 변경 (2025-12-10)**: 시나리오별/연도별 분석을 위해 ssp_scenario, target_year, probability 컬럼 추가

#### site_risk_results - Site별 시나리오/연도/리스크별 결과

**필요 이유:** FastAPI AI Agent가 계산한 site별 시나리오/연도/리스크타입별 최종 결과 저장

**사용처:**
- FastAPI: AI Agent가 H × E × V 계산 결과 저장
- SpringBoot: 대시보드 리스크 조회

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| site_id | UUID PK | 사업장 ID | Application DB sites 참조 |
| ssp_scenario | VARCHAR(10) PK | SSP 시나리오 | SSP1/SSP2/SSP3/SSP5 |
| target_year | INTEGER PK | 분석 연도 | 2030/2050/2080 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 복합 PK |
| hazard_score | REAL | H Score (0.0~1.0) | Hazard |
| exposure_score | REAL | E Score (0.0~1.0) | Exposure |
| vulnerability_score | REAL | V Score (0.0~1.0) | Vulnerability |
| probability | REAL | P(H) (0.0~1.0) | 발생 확률 |
| aal_percentage | REAL | AAL (%) | 연평균 손실률 |
| physical_risk_score | REAL | H × E × V (0.0~1.0) | 물리적 리스크 |
| physical_risk_score_100 | REAL | 0~100 스케일 | UI 표시용 |
| risk_level | VARCHAR(20) | 물리적 리스크 등급 | Very High/High/Medium/Low/Very Low |
| calculation_details | JSONB | 계산 상세 | 디버깅용 |
| calculated_at | TIMESTAMP | 계산 시점 | 신선도 확인 |
| analysis_job_id | UUID | 분석 작업 ID | 추적용 |

**PK 구조:** (site_id, ssp_scenario, target_year, risk_type)

**예상 데이터 규모:** 사이트 수 × 4 시나리오 × 3 연도 × 9 리스크 = 사이트 × 108

---

#### site_risk_summary - Site별 시나리오/연도별 요약

**필요 이유:** Site별 시나리오/연도별 9개 리스크 타입을 통합한 요약 정보

**사용처:**
- FastAPI: 전체 리스크 등급 조회
- SpringBoot: 대시보드 요약

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| site_id | UUID PK | 사업장 ID | Application DB sites 참조 |
| ssp_scenario | VARCHAR(10) PK | SSP 시나리오 | SSP1/SSP2/SSP3/SSP5 |
| target_year | INTEGER PK | 분석 연도 | 2030/2050/2080 |
| avg_physical_risk_score | REAL | 9개 평균 (0~100) | 전체 물리적 리스크 |
| total_aal_percentage | REAL | 9개 합계 (%) | 전체 AAL |
| avg_hazard_score | REAL | H 평균 (0~1) | 평균 Hazard |
| avg_exposure_score | REAL | E 평균 (0~1) | 평균 Exposure |
| avg_vulnerability_score | REAL | V 평균 (0~1) | 평균 Vulnerability |
| highest_risk_type | VARCHAR(50) | 가장 높은 리스크 | 핵심 리스크 |
| highest_risk_score | REAL | 해당 점수 | 핵심 리스크 점수 |
| overall_risk_grade | VARCHAR(20) | 전체 등급 | A/B/C/D/F |
| calculated_at | TIMESTAMP | 계산 시점 | 신선도 확인 |
| analysis_job_id | UUID | 분석 작업 ID | 추적용 |

**PK 구조:** (site_id, ssp_scenario, target_year)

**예상 데이터 규모:** 사이트 수 × 4 시나리오 × 3 연도 = 사이트 × 12

---

#### candidate_sites - 이전 후보지

**필요 이유:** 사업장 이전 후보지 정보 및 리스크 분석 결과 저장

**사용처:**
- FastAPI: AI Agent가 후보지 추천 및 리스크 계산
- SpringBoot: 후보지 목록 조회 (FastAPI API 통해)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 후보지 ID | 내부 식별자 |
| name | VARCHAR(255) | 후보지 이름 | 표시용 |
| road_address | VARCHAR(500) | 도로명 주소 | 위치 정보 |
| jibun_address | VARCHAR(500) | 지번 주소 | 위치 정보 |
| city | VARCHAR(100) | 도시 | 필터링 |
| latitude | DECIMAL(10,8) | 위도 | 격자 매핑 |
| longitude | DECIMAL(11,8) | 경도 | 격자 매핑 |
| risk_score | INTEGER | 종합 리스크 점수 (0-100) | AI 계산 결과 |
| risk_level | VARCHAR(20) | 리스크 레벨 | low/medium/high/critical |
| risks | JSONB | 개별 리스크 점수 | {flood, typhoon, heatwave, ...} |
| aal | DECIMAL(15,2) | 연평균 손실 (AAL) | 재무 지표 |
| cvar | DECIMAL(15,2) | 조건부 VaR | 재무 지표 |
| estimated_cost | DECIMAL(15,2) | 이전 예상 비용 | 재무 지표 |
| carbon_impact | DECIMAL(15,2) | 탄소 영향 | ESG 지표 |
| cost_change | DECIMAL(15,2) | 비용 변화 | 재무 지표 |
| location_summary | TEXT | 위치 요약 설명 | 표시용 |
| advantages | TEXT[] | 장점 배열 | 표시용 |
| disadvantages | TEXT[] | 단점 배열 | 표시용 |
| is_active | BOOLEAN | 활성 여부 | 상태 관리 |
| created_at | TIMESTAMP | 생성 시점 | 추적 |
| updated_at | TIMESTAMP | 수정 시점 | 추적 |

**인덱스:** location (lat, lon), risk_level, city, is_active

---

## 2. Application DB (SpringBoot)

### 2.1 테이블 개요

| 카테고리 | 테이블 수 | 설명 |
|----------|----------|------|
| User | 3개 | 사용자 인증 (users, password_reset_tokens, refresh_tokens) |
| Site | 1개 | 사업장 관리 (basic.dbml 기준) |
| Analysis | 2개 | AI 분석 작업/결과 (SpringBoot Entity) |
| Report | 1개 | 리포트 관리 (SpringBoot Entity) |
| Meta | 2개 | 메타데이터 (SpringBoot Entity) |
| **합계** | **9개** | 생성 완료 ✓ |

> **SQL 파일:**
> - `create_springboot_tables.sql` - 9개 테이블 모두 포함

---

### 2.2 User Tables (3개)

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
| used | BOOLEAN | 사용 여부 | 기본값 false |

---

#### refresh_tokens - 리프레시 토큰

**필요 이유:** JWT 리프레시 토큰 관리 (로그인 세션 유지)

**사용처:**
- SpringBoot: AuthController (토큰 갱신, 로그아웃)
- 멀티 디바이스 로그인 추적 및 관리

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 토큰 ID | 내부 식별자 |
| user_id | UUID FK | 사용자 ID | users 참조 (CASCADE 삭제) |
| token | VARCHAR(500) UK | JWT 리프레시 토큰 | 토큰 값 |
| expires_at | TIMESTAMP | 만료 시간 | 기본 7일 |
| created_at | TIMESTAMP | 생성 시간 | 기본값 now() |
| revoked | BOOLEAN | 무효화 여부 | 로그아웃 시 true |
| device_info | VARCHAR(255) | User-Agent 정보 | 기기 추적 |
| ip_address | VARCHAR(45) | 접속 IP | IPv4/IPv6 지원 |

---

### 2.3 Site Tables (1개)

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
| site_additional_data | Excel/JSONB | 11_load_site_data.py |
| batch_jobs | 서비스 생성 | (서비스에서 동적 생성) |

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
| api_wamis_stations | WAMIS 관측소 | 05_load_wamis.py |
| building_aggregate_cache | 국토교통부 건축물대장 | 06_load_buildings.py |
| api_disaster_yearbook | 행정안전부 재해연보 | 15_load_disaster_yearbook.py |
| api_typhoon_besttrack | 기상청 베스트트랙 | 09_load_typhoon_besttrack.py |

---

## 5. 코드-DB 매핑

### 5.1 서비스별 테이블 참조

| 서비스 | 참조 테이블 | 용도 |
|--------|------------|------|
| **SpringBoot** | users, sites, password_reset_tokens | 사용자/사업장 관리 |
| | analysis_jobs, analysis_results | AI 분석 작업 관리 |
| | reports | 리포트 관리 |
| | industries, hazard_types | 메타데이터 조회 |
| **FastAPI** | location_grid, location_admin | 좌표 → 격자/행정구역 매핑 |
| | ta_data, rn_data, ws_data 등 | 기후 데이터 조회 |
| | probability_results, hazard_results | P(H), Hazard Score 조회 |
| | api_* 테이블들 | 외부 API 캐시 조회 |
| **ModelOPS** | ta_data, rn_data, spei12_data 등 | 기후 데이터 입력 |
| | probability_results | P(H) 확률 결과 저장 |
| | hazard_results | Hazard Score 결과 저장 |

### 5.2 Wide Format SSP 컬럼 매핑

코드에서 `ssp_scenario_data`를 참조할 경우, 실제 테이블의 컬럼 매핑:

| 코드 참조 | 실제 테이블 | SSP 컬럼 |
|----------|------------|----------|
| SSP1-2.6 | ta_data, rn_data 등 | ssp1 |
| SSP2-4.5 | ta_data, rn_data 등 | ssp2 |
| SSP3-7.0 | ta_data, rn_data 등 | ssp3 |
| SSP5-8.5 | ta_data, rn_data 등 | ssp5 |

### 5.3 코드 참조 vs 실제 테이블

| 코드에서 참조 | 실제 테이블 | 비고 |
|--------------|------------|------|
| climate_data | ta_data, rn_data, ws_data 등 | 개별 테이블로 분리됨 |
| geographic_data | raw_dem, raw_landcover | 래스터 테이블 |
| historical_events | api_disaster_yearbook | 유사 데이터 |

---

## 6. 참조 문서

### 6.1 소스 코드

| 서비스 | 위치 | 주요 파일 |
|--------|------|----------|
| SpringBoot | `/DB_ALL/springboot/polaris_backend/` | `domain/**/*.java` (Entity) |
| FastAPI | `/DB_ALL/fastapi/ai_agent/` | `utils/database.py` |
| ModelOPS | `/DB_ALL/modelops/modelops/` | `database/connection.py` |
| Frontend | `/DB_ALL/frontend/src/` | `assets/data/*.ts` (타입 정의) |

### 6.2 SQL 파일

| 데이터베이스 | 위치 |
|-------------|------|
| Datawarehouse | `/db_final_1202/db/sql/datawarehouse/*.sql` |
| Application | `/db_final_1202/db/sql/application/*.sql` |

### 6.3 ETL 스크립트

| 유형 | 위치 |
|------|------|
| Local ETL | `/db_final_1202/etl/local/scripts/*.py` |
| API ETL | `/db_final_1202/etl/api/scripts/*.py` |

---

## 7. 테이블 현황 요약

| 데이터베이스 | 테이블 수 | 상태 |
|-------------|----------|------|
| Datawarehouse | 47개 | ✓ 완료 |
| Application | 9개 | ✓ 완료 |
| **합계** | **56개** | ✓ |

---

*문서 작성: Claude Code*
*최종 수정: 2025-12-10*
