# SKALA Physical Risk AI - 통합 ERD

> 최종 수정일: 2025-12-12
> 버전: v14 (Application DB 10개 테이블 - google_oauth_tokens, verification_codes 추가)

**컬럼 사용 상태 범례:**
| 기호 | 의미 |
|------|------|
| ✅ | 실제 코드에서 사용됨 |
| ⚠️ | DEPRECATED 또는 NOT_USED (사용되지 않음) |
| 🔧 | 제한적 사용 (디버깅, 툴팁 등)

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

**코드 위치:**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 128-178)
  - `find_admin_by_coords()`: 좌표 → 행정구역 조회
  - `find_admin_by_code()`: 행정코드 → 행정구역 조회
- **ModelOPS**: `modelops/database/connection.py` (라인 785-839)
  - 인구 데이터 기반 Exposure 계산
- **ETL**: `modelops/etl/local/scripts/01_load_admin_regions.py`

**사용처:**
- FastAPI AI Agent Node 1 (`data_collection_node`): 좌표 기반 행정구역 + 인구 정보 조회
- ModelOPS ExposureAgent: 인구 데이터 기반 노출도(E) 계산
- FastAPI: VWorld 역지오코딩 결과와 연계하여 상세 지역명 표시
- ETL: 일별 기후 데이터 적재 시 admin_id 참조

**쿼리 예시:**
```sql
-- 좌표 기반 행정구역 조회
SELECT admin_id, admin_code, admin_name, population_2020, population_2050
FROM location_admin
WHERE ST_Contains(geom, ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 5174))
ORDER BY level DESC
LIMIT 1;
```

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

**필요 이유:** 월별/연별 기후 데이터가 0.01° 격자 레벨로 제공되어 좌표 기반 격자 매핑 필요

**코드 위치:**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 180-220)
  - `find_nearest_grid()`: 좌표 → 최근접 격자 조회
  - `get_climate_data_by_coords()`: 좌표로 기후 데이터 조회
- **ModelOPS**: `modelops/database/connection.py` (라인 340-420)
  - `get_grid_id_by_coords()`: 좌표 → grid_id 변환
  - 모든 Probability/Hazard Agent에서 사용
- **ETL**: `modelops/etl/local/scripts/06_create_location_grid.py`

**사용처:**
- FastAPI AI Agent Node 1 (`data_collection_node`): 사업장 좌표를 0.01° 단위로 반올림하여 grid_id 조회
- FastAPI AI Agent Node 3 (`risk_assessment_node`): grid_id로 기후 데이터(ta_data, rn_data 등) 조회
- ModelOPS ProbabilityAgent: 격자별 P(H) 확률 계산
- ModelOPS HazardAgent: 격자별 Hazard Score 계산
- ETL: 월별/연별 기후 데이터 적재 시 grid_id FK 참조

**쿼리 예시:**
```sql
-- 좌표 → 최근접 격자 조회
SELECT grid_id, longitude, latitude
FROM location_grid
WHERE longitude = ROUND(127.0276::numeric, 2)
  AND latitude = ROUND(37.4979::numeric, 2)
LIMIT 1;

-- PostGIS 공간 쿼리로 최근접 격자 조회
SELECT grid_id, longitude, latitude,
       ST_Distance(geom, ST_SetSRID(ST_MakePoint(127.0276, 37.4979), 4326)) as dist
FROM location_grid
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(127.0276, 37.4979), 4326)
LIMIT 1;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| grid_id | SERIAL PK | 격자 ID | **핵심** - 모든 기후 테이블의 FK 참조 대상 |
| longitude | NUMERIC(9,6) | 경도 (124.5~132.0) | 좌표 매핑 (0.01° 간격), UNIQUE(lon, lat) |
| latitude | NUMERIC(8,6) | 위도 (33.0~39.0) | 좌표 매핑 (0.01° 간격), UNIQUE(lon, lat) |
| geom | GEOMETRY | POINT EPSG:4326 | 공간 인덱스 (GIST), ST_DWithin 쿼리 지원 |

**예상 데이터 규모:** 451,351 rows (601 × 751 격자)

**격자 해상도:**
- 경도: 124.50 ~ 132.00 (0.01° 간격, 751 포인트)
- 위도: 33.00 ~ 39.00 (0.01° 간격, 601 포인트)

---

#### sea_level_grid - 해수면 격자점 위치 정보

**필요 이유:** 해수면 상승 데이터는 별도의 저해상도 격자(1° 간격)로 제공되며, 해안 지역 분석에 필수

**코드 위치:**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 420-480)
  - `find_nearest_sea_level_grid()`: 해안 좌표 → 해수면 격자 조회
  - `get_sea_level_data()`: 해수면 상승 데이터 조회
- **ModelOPS**: `modelops/database/connection.py` (라인 890-950)
  - `get_sea_level_rise()`: 해수면 상승 시나리오 데이터 조회
  - SeaLevelRiseProbabilityAgent에서 사용
- **ETL**: `modelops/etl/local/scripts/09_load_sea_level.py`

**사용처:**
- FastAPI AI Agent Node 3 (`risk_assessment_node`): 해안 사업장의 sea_level_rise Hazard 계산
- ModelOPS SeaLevelRiseProbabilityAgent: 해수면 상승 기반 P(H) 확률 계산
- 리포트: 해안 홍수 위험도 분석 및 시나리오별 예측

**쿼리 예시:**
```sql
-- 해안 좌표 → 최근접 해수면 격자 조회
SELECT g.grid_id, g.longitude, g.latitude,
       s.ssp1, s.ssp2, s.ssp3, s.ssp5
FROM sea_level_grid g
JOIN sea_level_data s ON g.grid_id = s.grid_id
WHERE s.year = 2050
ORDER BY g.geom <-> ST_SetSRID(ST_MakePoint(126.5, 34.0), 4326)
LIMIT 1;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| grid_id | SERIAL PK | 격자 ID | sea_level_data FK 참조 대상 |
| longitude | NUMERIC(9,6) | 경도 (124.50~131.50) | 해수면 격자 위치 (1° 간격) |
| latitude | NUMERIC(8,6) | 위도 (33.49~42.14) | 해수면 격자 위치 (1° 간격) |
| geom | GEOMETRY | POINT EPSG:4326 | 공간 인덱스 (GIST), 최근접 쿼리 지원 |

**예상 데이터 규모:** 80 rows (10 × 8 격자)

**사용 조건:**
- 해안선에서 50km 이내 사업장만 해수면 상승 위험 분석 대상
- location_grid보다 저해상도이므로 별도 테이블로 분리

---

### 1.3 Climate Data Tables (17개)

모든 기후 테이블은 **Wide Format** (SSP 컬럼 방식)을 사용합니다:
- `ssp1`: SSP1-2.6 시나리오 (지속가능 발전)
- `ssp2`: SSP2-4.5 시나리오 (중간 경로)
- `ssp3`: SSP3-7.0 시나리오 (지역 경쟁)
- `ssp5`: SSP5-8.5 시나리오 (화석연료 의존)

**코드 위치 (공통):**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 500-800)
  - `get_climate_data()`: 격자 ID와 기간으로 기후 데이터 조회
  - `get_climate_statistics()`: 기후 데이터 통계 계산 (평균, 최대, 최소)
  - `get_extreme_events()`: 극한 기상 이벤트 조회
- **ModelOPS**: `modelops/database/connection.py` (라인 200-600)
  - `get_temperature_data()`: 기온 데이터 조회 (tamax, tamin, ta)
  - `get_precipitation_data()`: 강수 데이터 조회 (rn, rx1day, rx5day)
  - `get_climate_indices()`: 기후 지수 조회 (spei12, csdi, wsdi)
- **ETL**: `modelops/etl/local/scripts/07_load_monthly_grid_data.py`, `08_load_yearly_grid_data.py`

**사용 흐름:**
1. 사업장 좌표 → location_grid에서 grid_id 조회
2. grid_id + 기간으로 각 기후 테이블에서 데이터 조회
3. SSP 시나리오별 컬럼에서 해당 시나리오 값 추출
4. ModelOPS Agent가 P(H), Hazard Score 계산

#### 일별 데이터 (행정구역 레벨)

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| tamax_data | 일 최고기온 (°C) | 폭염(extreme_heat) Hazard 계산 | (time, admin_id) | ~7.63M |
| tamin_data | 일 최저기온 (°C) | 한파(extreme_cold) Hazard 계산 | (time, admin_id) | ~7.63M |

**tamax_data 상세:**
- **사용 Agent**: ExtremeHeatProbabilityAgent, ExtremeHeatHazardAgent
- **계산 로직**: 일 최고기온 35°C 이상 연속 일수로 폭염 발생 확률 계산
- **쿼리 예시**:
```sql
SELECT time, ssp2 as temp_max
FROM tamax_data
WHERE admin_id = 123 AND time BETWEEN '2050-06-01' AND '2050-08-31'
  AND ssp2 >= 35
ORDER BY time;
```

**tamin_data 상세:**
- **사용 Agent**: ExtremeColdProbabilityAgent, ExtremeColdHazardAgent
- **계산 로직**: 일 최저기온 -12°C 이하 연속 일수로 한파 발생 확률 계산

**컬럼 구조:**
- `time` (DATE): 관측일 (2021-01-01 ~ 2100-12-31)
- `admin_id` (INTEGER FK): location_admin 참조 (시군구 레벨)
- `ssp1~ssp5` (REAL): 각 시나리오별 기온값 (°C)

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

**테이블별 상세:**

**ta_data (평균기온):**
- **사용 Agent**: ExtremeHeatProbabilityAgent, ExtremeColdProbabilityAgent
- **용도**: 기준 온도 대비 편차 계산, 장기 기후 트렌드 분석
- **쿼리 예시**:
```sql
SELECT observation_date, ssp2 as temp_avg
FROM ta_data
WHERE grid_id = 12345 AND observation_date BETWEEN '2050-01-01' AND '2050-12-01'
ORDER BY observation_date;
```

**rn_data (강수량):**
- **사용 Agent**: RiverFloodProbabilityAgent, DroughtProbabilityAgent, WildfireProbabilityAgent
- **용도**: 홍수 발생 강수량 임계치 분석, 무강수 기간 계산, 산불 건조 조건 판단
- **중요 임계값**: 80mm/일 이상 → 도시 홍수 경보, 30일 무강수 → 가뭄 경보

**ws_data (풍속):**
- **사용 Agent**: TyphoonProbabilityAgent, TyphoonHazardAgent
- **용도**: 강풍 발생 빈도, 태풍 피해 규모 추정
- **중요 임계값**: 17m/s 이상 → 강풍 경보, 25m/s 이상 → 폭풍 경보

**rhm_data (상대습도):**
- **사용 Agent**: WildfireProbabilityAgent, WildfireHazardAgent
- **용도**: 산불 발생 조건 평가 (건조도)
- **중요 임계값**: 30% 이하 + 고온 → 산불 위험 높음

**si_data (일사량):**
- **사용 Agent**: 리포트 생성 시 에너지 영향 분석
- **용도**: 태양광 발전 효율, 냉방 부하 예측

**spei12_data (표준화 강수-증발산 지수):**
- **사용 Agent**: DroughtProbabilityAgent, DroughtHazardAgent
- **용도**: 가뭄 심각도 핵심 지표 (12개월 누적)
- **중요 임계값**: -1.0 이하 → 경미한 가뭄, -1.5 이하 → 심한 가뭄, -2.0 이하 → 극심한 가뭄
- **쿼리 예시**:
```sql
SELECT observation_date, ssp2 as spei
FROM spei12_data
WHERE grid_id = 12345 AND observation_date >= '2050-01-01'
  AND ssp2 < -1.5  -- 심한 가뭄 필터
ORDER BY ssp2;
```

**컬럼 구조:**
- `grid_id` (INTEGER FK): location_grid 참조
- `observation_date` (DATE): 관측 월 (YYYY-MM-01, 매월 1일)
- `ssp1~ssp5` (REAL): 각 시나리오별 값

---

#### 연별 데이터 (격자 레벨)

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| csdi_data | 한랭야 계속기간 지수 (일) | 한파(extreme_cold) 장기 추세 | (year, grid_id) | ~9M |
| wsdi_data | 온난야 계속기간 지수 (일) | 폭염(extreme_heat) 장기 추세 | (year, grid_id) | ~9M |
| rx1day_data | 1일 최다강수량 (mm) | 하천홍수(river_flood) 극값 분석 | (year, grid_id) | ~9M |
| rx5day_data | 5일 최다강수량 (mm) | 하천홍수(river_flood) 극값 분석 | (year, grid_id) | ~9M |
| cdd_data | 연속 무강수일 (일) | 가뭄(drought) 장기 추세 | (year, grid_id) | ~9M |
| rain80_data | 80mm 이상 강수일수 (일) | 도시홍수(urban_flood) 위험도 | (year, grid_id) | ~9M |
| sdii_data | 강수강도 (mm/일) | 집중호우 분석 | (year, grid_id) | ~9M |
| ta_yearly_data | 연평균 기온 (°C) | 기후변화 장기 추세 | (year, grid_id) | ~9M |

**테이블별 상세:**

**csdi_data (한랭야 계속기간 지수):**
- **사용 Agent**: ExtremeColdProbabilityAgent
- **정의**: 하루 최저기온이 10번째 백분위수보다 낮은 연속 6일 이상의 기간
- **용도**: 한파 장기 추세 분석, P(H) 계산의 히스토리컬 데이터
- **쿼리 예시**:
```sql
SELECT year, ssp2 as csdi_days
FROM csdi_data
WHERE grid_id = 12345 AND year BETWEEN 2021 AND 2100
ORDER BY year;
```

**wsdi_data (온난야 계속기간 지수):**
- **사용 Agent**: ExtremeHeatProbabilityAgent
- **정의**: 하루 최고기온이 90번째 백분위수보다 높은 연속 6일 이상의 기간
- **용도**: 폭염 장기 추세 분석

**rx1day_data (1일 최다강수량):**
- **사용 Agent**: RiverFloodProbabilityAgent, RiverFloodHazardAgent
- **용도**: 극한 강수 이벤트 분석, 홍수 발생 확률 계산
- **중요 임계값**: 100mm 이상 → 홍수 주의, 200mm 이상 → 홍수 경보

**rx5day_data (5일 최다강수량):**
- **사용 Agent**: RiverFloodProbabilityAgent
- **용도**: 누적 강수로 인한 하천 범람 위험 평가

**cdd_data (연속 무강수일):**
- **사용 Agent**: DroughtProbabilityAgent, DroughtHazardAgent
- **정의**: 일 강수량 1mm 미만인 연속 최대 일수
- **용도**: 가뭄 심각도 평가, 수자원 스트레스 분석

**rain80_data (80mm 이상 강수일수):**
- **사용 Agent**: UrbanFloodProbabilityAgent, UrbanFloodHazardAgent
- **정의**: 일 강수량 80mm 이상인 날의 연간 일수
- **용도**: 도시 내수 침수 위험도 평가
- **중요 임계값**: 연간 5회 이상 → 도시 홍수 위험 높음

**sdii_data (강수강도):**
- **사용 Agent**: RiverFloodProbabilityAgent, UrbanFloodProbabilityAgent
- **정의**: 습윤일(강수량 ≥ 1mm) 평균 강수량
- **용도**: 집중호우 경향성 분석

**ta_yearly_data (연평균 기온):**
- **사용 Agent**: 리포트 생성, 기후 트렌드 시각화
- **용도**: 장기 기후변화 추세 분석, 기준 연도 대비 기온 상승폭 계산
- **쿼리 예시**:
```sql
SELECT year, ssp1, ssp2, ssp3, ssp5
FROM ta_yearly_data
WHERE grid_id = 12345 AND year IN (2030, 2050, 2080)
ORDER BY year;
```

**컬럼 구조:**
- `grid_id` (INTEGER FK): location_grid 참조
- `year` (INTEGER): 관측 연도 (2021~2100, 80년간)
- `ssp1~ssp5` (REAL): 각 시나리오별 값

---

#### 해수면 상승 데이터

| 테이블 | 설명 | 사용처 | PK | 예상 Rows |
|--------|------|--------|-----|-----------|
| sea_level_data | 해수면 상승 (cm) | 해안홍수(sea_level_rise) Hazard | (year, grid_id) | ~1,720 |

**sea_level_data 상세:**
- **사용 Agent**: SeaLevelRiseProbabilityAgent, SeaLevelRiseHazardAgent
- **용도**: 해안 침수 위험, 폭풍 해일 취약성 평가

**코드 위치:**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 480-520)
  - `get_sea_level_projection()`: 시나리오별 해수면 상승 예측치 조회
- **ModelOPS**: `modelops/database/connection.py` (라인 920-980)
  - `calculate_sea_level_risk()`: 해안 거리 + 해수면 상승으로 침수 위험 계산

**중요 임계값:**
- 0.5m 이상 상승 → 해안 침수 위험
- 1.0m 이상 상승 → 심각한 해안 침수
- 폭풍 해일 시 추가 1-2m 상승 고려

**쿼리 예시:**
```sql
-- 2050년 SSP2 시나리오 해수면 상승 조회
SELECT g.longitude, g.latitude, s.ssp2 as sea_level_rise_cm
FROM sea_level_grid g
JOIN sea_level_data s ON g.grid_id = s.grid_id
WHERE s.year = 2050
ORDER BY s.ssp2 DESC;

-- 시나리오별 연도별 해수면 상승 추이
SELECT year, ssp1, ssp2, ssp3, ssp5
FROM sea_level_data
WHERE grid_id = 5  -- 특정 해안 격자
ORDER BY year;
```

**컬럼 구조:**
- `grid_id` (INTEGER FK): sea_level_grid 참조 (1° 저해상도 격자)
- `year` (INTEGER): 관측 연도 (2015~2100)
- `ssp1~ssp5` (REAL): 각 시나리오별 해수면 상승값 (cm, 기준년도 대비)

---

### 1.4 ModelOPS Tables (5개)

ModelOPS가 **H × E × V = Risk** 공식에 따라 계산한 결과를 저장합니다.

> ⚠️ **변경 이력 (2025-12-03)**: probability_results 테이블 컬럼 수정 (probability → aal, bin_probabilities), 3개 테이블 추가 (exposure_results, vulnerability_results, aal_scaled_results)

**코드 위치 (공통):**
- **ModelOPS 저장**: `modelops/database/connection.py` (라인 1000-1500)
  - `save_probability_results()`: P(H) 확률 결과 저장
  - `save_hazard_results()`: Hazard Score 결과 저장
  - `save_exposure_results()`: Exposure 결과 저장
  - `save_vulnerability_results()`: Vulnerability 결과 저장
  - `save_aal_scaled_results()`: 최종 AAL 결과 저장
- **ModelOPS Agent**: `modelops/agents/` 디렉토리
  - `probability_agent.py`: 9개 리스크별 ProbabilityAgent 클래스
  - `hazard_agent.py`: 9개 리스크별 HazardAgent 클래스
  - `exposure_agent.py`: ExposureAgent
  - `vulnerability_agent.py`: VulnerabilityAgent
  - `aal_agent.py`: AALScalingAgent
- **FastAPI 조회**: `fastapi/ai_agent/utils/database.py` (라인 900-1100)
  - `get_probability_by_coords()`: 좌표로 P(H) 조회
  - `get_hazard_by_coords()`: 좌표로 Hazard Score 조회

**계산 흐름:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Climate Data (ta_data, rn_data, spei12_data, etc.)             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  ProbabilityAgent (9개)                                          │
│  → probability_results (P(H), bin_probabilities, aal)           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  HazardAgent (9개)                                               │
│  → hazard_results (hazard_score, hazard_score_100, level)       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           ▼                               ▼
┌───────────────────────┐      ┌───────────────────────────────┐
│  ExposureAgent        │      │  VulnerabilityAgent           │
│  → exposure_results   │      │  → vulnerability_results      │
│  (proximity, asset)   │      │  (building age, structure)    │
└──────────┬────────────┘      └──────────────┬────────────────┘
           │                                  │
           └────────────────┬─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  AALScalingAgent                                                 │
│  → aal_scaled_results (final_aal, expected_loss)                │
└─────────────────────────────────────────────────────────────────┘
```

**위험 유형 (risk_type) 9가지:**
1. `sea_level_rise` - 해수면 상승 (해안 침수, 폭풍 해일)
2. `extreme_cold` - 극심한 한파 (저온 피해)
3. `drought` - 가뭄 (SPEI, 강수량 부족)
4. `extreme_heat` - 극심한 고온 (폭염 피해)
5. `river_flood` - 하천 홍수 (하천 범람)
6. `typhoon` - 태풍 (강풍, 집중호우)
7. `urban_flood` - 도시 홍수 (내수 침수)
8. `water_stress` - 물부족 (수자원 스트레스)
9. `wildfire` - 산불 (건조, 고온)

---

#### probability_results - P(H) 확률 결과

**필요 이유:** ModelOPS가 기후 데이터 기반으로 계산한 위험 발생 확률 저장 (H × E × V 공식의 기초)

**코드 위치:**
- **저장**: `modelops/agents/probability_agent.py` (각 리스크별 Agent)
  - `ExtremeHeatProbabilityAgent.calculate()`: 폭염 P(H) 계산
  - `DroughtProbabilityAgent.calculate()`: 가뭄 P(H) 계산 (SPEI12 기반)
  - `TyphoonProbabilityAgent.calculate()`: 태풍 P(H) 계산 (과거 이력 기반)
- **조회**: `fastapi/ai_agent/utils/database.py` (라인 900-950)
  - `get_probability_by_coords()`: 사업장 좌표로 P(H) 조회

**사용처:**
- ModelOPS: 각 ProbabilityAgent가 결과 저장 (`save_probability_results()`)
- FastAPI AI Agent Node 3 (`risk_assessment_node`): P(H) 조회하여 AAL 계산
- 리포트: 위험 발생 확률 시각화 (히스토그램)

**bin_probabilities 구조:**
```json
{
  "bins": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
  "probabilities": [0.65, 0.20, 0.10, 0.04, 0.01]
}
// 해석: 0-20% 손실 확률 65%, 20-40% 손실 확률 20%, ...
```

**쿼리 예시:**
```sql
-- 특정 좌표의 9개 리스크별 P(H) 조회
SELECT risk_type, aal, bin_probabilities
FROM probability_results
WHERE latitude = 37.50 AND longitude = 127.00
ORDER BY aal DESC;

-- 가뭄 위험 높은 지역 Top 10
SELECT latitude, longitude, aal
FROM probability_results
WHERE risk_type = 'drought'
ORDER BY aal DESC
LIMIT 10;
```

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별, location_grid와 조인 | ✅ 모든 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 모든 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | **핵심** - hazard_types.code와 매핑 | ✅ 리스크별 필터링 |
| aal | REAL | 연간 평균 손실률 (0.0~1.0) | AAL 계산 기초값, aal_scaled_results.base_aal로 전달 | ✅ ModelOPS `_calculate_aal()` |
| bin_probabilities | JSONB | bin별 발생확률 배열 | 손실 확률 분포 (리스크 시각화용) | ✅ ModelOPS `base_probability_agent.py` AAL 계산 |
| bin_data | JSONB | 히스토그램 상세 | 하위 호환성 유지 (deprecated) | ⚠️ **DEPRECATED** - 저장만 하고 조회 안 함 |
| calculation_details | JSONB | 계산 상세정보 | 모델 버전, 파라미터, 입력 데이터 범위 등 | ✅ 디버깅/감사 추적 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인, 갱신 여부 판단 | ✅ 캐시 무효화 판단 |

> **bin_probabilities 사용 코드** (`modelops/agents/base_probability_agent.py`):
> ```python
> bin_probabilities = self._calculate_bin_probabilities(intensity_values)
> aal = self._calculate_aal(bin_probabilities, self.dr_intensity)
> # bins: [0, 0.2, 0.4, 0.6, 0.8, 1.0] → 5개 구간별 발생 확률
> ```

**예상 데이터 규모:** ~4.06M rows (451,351 grids × 9 risk types)

---

#### hazard_results - Hazard Score 결과

**필요 이유:** ModelOPS가 계산한 위험도 점수 저장 (H × E × V 공식의 **H** 부분)

**코드 위치:**
- **저장**: `modelops/agents/hazard_agent.py` (각 리스크별 Agent)
  - `ExtremeHeatHazardAgent.calculate()`: 폭염 Hazard Score 계산
  - `RiverFloodHazardAgent.calculate()`: 하천홍수 Hazard Score 계산
  - `TyphoonHazardAgent.calculate()`: 태풍 Hazard Score 계산
- **조회**: `fastapi/ai_agent/utils/database.py` (라인 950-1000)
  - `get_hazard_by_coords()`: 사업장 좌표로 H Score 조회

**사용처:**
- ModelOPS: 각 HazardAgent가 결과 저장 (`save_hazard_results()`)
- FastAPI AI Agent Node 3 (`risk_assessment_node`): H Score 조회 → Physical Risk = H × E × V 계산
- Frontend: 위험도 게이지, 히트맵 시각화
- 리포트: 위험 유형별 상세 분석 섹션

**계산 로직 예시:**
```python
# 폭염 Hazard Score 계산 (ExtremeHeatHazardAgent)
def calculate_hazard(self, climate_data):
    # 35°C 이상 연속 일수, 온도 편차 등을 종합하여 점수화
    extreme_days = count_days_above_threshold(climate_data['tamax'], 35)
    temp_anomaly = calc_temperature_anomaly(climate_data['ta'])
    hazard_score = normalize(extreme_days * 0.6 + temp_anomaly * 0.4)
    return hazard_score  # 0.0 ~ 1.0
```

**쿼리 예시:**
```sql
-- 특정 좌표의 9개 리스크별 Hazard Score 조회
SELECT risk_type, hazard_score_100, hazard_level
FROM hazard_results
WHERE latitude = 37.50 AND longitude = 127.00
ORDER BY hazard_score_100 DESC;

-- 폭염 위험 "매우높음" 지역 조회
SELECT latitude, longitude, hazard_score_100
FROM hazard_results
WHERE risk_type = 'extreme_heat' AND hazard_level = '매우높음'
ORDER BY hazard_score_100 DESC
LIMIT 100;
```

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 | ✅ 좌표 기반 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 좌표 기반 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | hazard_types.code와 매핑 | ✅ 리스크별 필터링 |
| hazard_score | REAL | 원본 위험도 점수 (0.0~1.0) | 모델 출력값, H × E × V 계산용 | ✅ Physical Risk 계산 |
| hazard_score_100 | REAL | 0-100 정규화 점수 | UI 표시용 (게이지, 등급 표시) | ✅ Frontend 게이지 표시 |
| hazard_level | VARCHAR(20) | 위험 등급 | VERY_LOW/LOW/MEDIUM/HIGH/VERY_HIGH | ✅ Frontend 색상 표시, 필터링 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 | ✅ 캐시 무효화 판단 |

**위험 등급 기준:**
| 점수 범위 | hazard_level | UI 색상 |
|-----------|--------------|---------|
| 0 ~ 20 | VERY_LOW | 녹색 |
| 20 ~ 40 | LOW | 청색 |
| 40 ~ 60 | MEDIUM | 황색 |
| 60 ~ 80 | HIGH | 주황색 |
| 80 ~ 100 | VERY_HIGH | 적색 |

**CHECK 제약조건:** `chk_hazard_level_score` - hazard_score_100과 hazard_level 일치 검증

**예상 데이터 규모:** ~4.06M rows (451,351 grids × 9 risk types)

---

#### exposure_results - E (노출도) 결과

**필요 이유:** ModelOPS Exposure Agent가 계산한 자산 노출 정도 저장 (H × E × V 공식의 **E** 부분)

**코드 위치:**
- **저장**: `modelops/agents/exposure_agent.py`
  - `ExposureAgent.calculate()`: 사업장의 위험원 근접성 및 자산 가치 기반 E Score 계산
- **조회**: `fastapi/ai_agent/utils/database.py` (라인 1000-1050)
  - `get_exposure_by_site()`: 사업장 ID로 E Score 조회

**사용처:**
- ModelOPS: ExposureAgent가 결과 저장 (`save_exposure_results()`)
- FastAPI AI Agent Node 4 (`impact_analysis_node`): E Score 조회 → Physical Risk = H × E × V 계산
- 리포트: 노출도 분석 섹션 (위험원 거리, 자산 규모)

**계산 요소:**
- **proximity_factor**: 위험원과의 거리
  - 하천/해안: 거리 기반 (가까울수록 높음)
  - 산림: 산림 면적 비율
  - 도시: 불투수 면적 비율
- **normalized_asset_value**: 정규화된 자산가치
  - 건물 면적 × 업종별 단가
  - 시설 가치 (전력, 냉각 등)

**쿼리 예시:**
```sql
-- 특정 사업장의 9개 리스크별 Exposure Score 조회
SELECT risk_type, exposure_score, proximity_factor, normalized_asset_value
FROM exposure_results
WHERE site_id = 'uuid-site-id'
ORDER BY exposure_score DESC;

-- 하천 홍수 노출도 높은 사업장 조회
SELECT site_id, exposure_score, proximity_factor
FROM exposure_results
WHERE risk_type = 'river_flood' AND exposure_score > 0.7
ORDER BY exposure_score DESC;
```

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 | ✅ 모든 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 모든 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 리스크별 E Score 구분 | ✅ 리스크별 필터링 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회 |
| exposure_score | REAL | 노출도 점수 (0.0~1.0) | **E 값** - H × E × V 계산용 | ✅ Physical Risk 계산 |
| proximity_factor | REAL | 근접도 계수 (0.0~1.0) | 위험원과의 거리 반영 | ✅ ModelOPS `integrated_risk_agent.py` |
| normalized_asset_value | REAL | 정규화 자산가치 (0.0~1.0) | 자산 규모 정규화 값 | ✅ E Score 계산 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 | ✅ 캐시 무효화 판단 |

> **proximity_factor 계산 코드** (`modelops/agents/integrated_risk_agent.py`):
> ```python
> # 10km 이내일수록 높은 값 (거리가 가까울수록 위험)
> proximity_factor = max(0.0, 1.0 - (distance_m / 10000.0))
> # 예: 거리 0m → 1.0, 거리 5km → 0.5, 거리 10km+ → 0.0
> ```

**노출도 계산 공식:**
```
E = w1 × proximity_factor + w2 × normalized_asset_value
(w1, w2는 리스크 타입별 가중치)
```

**예상 데이터 규모:** 사업장 수 × 9 risk types (사업장별로 저장)

---

#### vulnerability_results - V (취약성) 결과

**필요 이유:** ModelOPS Vulnerability Agent가 계산한 건물/시설 특성 기반 취약성 저장 (H × E × V 공식의 **V** 부분)

**코드 위치:**
- **저장**: `modelops/agents/vulnerability_agent.py`
  - `VulnerabilityAgent.calculate()`: 건물 특성, 업종 기반 V Score 계산
- **조회**: `fastapi/ai_agent/utils/database.py` (라인 1050-1100)
  - `get_vulnerability_by_site()`: 사업장 ID로 V Score 조회
- **건물 정보 조회**: `fastapi/ai_agent/utils/database.py`
  - `get_building_info()`: building_aggregate_cache에서 건물 정보 조회

**사용처:**
- ModelOPS: VulnerabilityAgent가 결과 저장 (`save_vulnerability_results()`)
- FastAPI AI Agent Node 2 (`building_characteristics_node`): 건물 정보 수집 → V Score 계산
- FastAPI AI Agent Node 4 (`impact_analysis_node`): V Score 조회 → Physical Risk = H × E × V 계산
- 리포트: 취약성 분석 섹션 (건물 연식, 구조, 업종 특성)

**취약성 계산 요소 (factors JSONB):**
```json
{
  "building_age": 25,           // 건물 연식 (년)
  "building_structure": "RC",   // 구조 (RC: 철근콘크리트, S: 철골, W: 목조)
  "floor_count": 5,             // 층수
  "basement_floors": 2,         // 지하층수 (홍수 취약성)
  "industry_code": "data_center", // 업종 코드 (industries.code)
  "industry_vulnerability_coefficient": 0.85, // 업종별 취약성 계수
  "drainage_capacity": "good",  // 배수 능력 (도시홍수용)
  "fire_resistance": "1st"      // 내화등급 (산불용)
}
```

**쿼리 예시:**
```sql
-- 특정 사업장의 9개 리스크별 Vulnerability Score 조회
SELECT risk_type, vulnerability_score, vulnerability_level, factors
FROM vulnerability_results
WHERE site_id = 'uuid-site-id'
ORDER BY vulnerability_score DESC;

-- 도시 홍수 취약성 높은 사업장 (지하층 있음)
SELECT site_id, vulnerability_score,
       factors->>'basement_floors' as basement
FROM vulnerability_results
WHERE risk_type = 'urban_flood'
  AND (factors->>'basement_floors')::int > 0
ORDER BY vulnerability_score DESC;
```

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 | ✅ 좌표 기반 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 좌표 기반 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 리스크별 V Score 구분 | ✅ 리스크별 필터링 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회 |
| vulnerability_score | REAL | 취약성 점수 (0~100) | **V 값** - H × E × V 계산용 | ✅ Physical Risk 계산 |
| vulnerability_level | VARCHAR(20) | 등급 | VERY_LOW/LOW/MEDIUM/HIGH/VERY_HIGH | ✅ Frontend 등급 표시 |
| factors | JSONB | 취약성 요인 상세 | 건물 연식, 구조, 업종 계수 등 | ✅ 리포트 상세 분석 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 | ✅ 캐시 무효화 판단 |

**취약성 등급 기준:**
| 점수 범위 | vulnerability_level | 설명 |
|-----------|---------------------|------|
| 0 ~ 20 | VERY_LOW | 매우 낮음 (신축, 내진설계) |
| 20 ~ 40 | LOW | 낮음 |
| 40 ~ 60 | MEDIUM | 보통 |
| 60 ~ 80 | HIGH | 높음 |
| 80 ~ 100 | VERY_HIGH | 매우 높음 (노후, 목조) |

**CHECK 제약조건:** `chk_vuln_level_score` - vulnerability_score와 vulnerability_level 일치 검증

**예상 데이터 규모:** 사업장 수 × 9 risk types (사업장별로 저장)

---

#### aal_scaled_results - AAL 최종 결과

**필요 이유:** ModelOPS AAL Scaling Agent가 계산한 취약성 보정 연간 평균 손실률(AAL) 저장 - **최종 재무적 영향 지표**

**코드 위치:**
- **저장**: `modelops/agents/aal_agent.py`
  - `AALScalingAgent.calculate()`: P(H) × V 보정 → 최종 AAL 계산
- **조회**: `fastapi/ai_agent/utils/database.py` (라인 1100-1150)
  - `get_aal_by_site()`: 사업장 ID로 최종 AAL 조회
- **리포트 생성**: `fastapi/ai_agent/nodes/report_generation_node.py`
  - AAL 기반 예상 손실액 계산 및 리포트 작성

**사용처:**
- ModelOPS: AALScalingAgent가 결과 저장 (`save_aal_scaled_results()`)
- FastAPI AI Agent Node 4 (`impact_analysis_node`): 최종 AAL 계산
- FastAPI AI Agent Node 6 (`report_generation_node`): 예상 손실액 산출
- 리포트: 재무적 영향 분석 섹션 (예상 손실액, 보험 권장)
- Frontend: 대시보드 AAL 표시, 비용-편익 분석

**계산 흐름:**
```
┌──────────────────────────────────────────────────────────────────┐
│ base_aal (probability_results.aal)                               │
│ + vulnerability_scale (F_vuln = 0.9 + V_score/100 × 0.2)         │
│ + insurance_rate (보험 가입률)                                    │
│ + asset_value (자산가치)                                          │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ final_aal = base_aal × F_vuln × (1 - insurance_rate)             │
│ expected_loss = final_aal × asset_value (원)                     │
└──────────────────────────────────────────────────────────────────┘
```

**쿼리 예시:**
```sql
-- 특정 사업장의 9개 리스크별 AAL 및 예상 손실액 조회
SELECT risk_type,
       base_aal, vulnerability_scale, final_aal,
       insurance_rate, expected_loss
FROM aal_scaled_results
WHERE site_id = 'uuid-site-id'
ORDER BY expected_loss DESC;

-- 전체 사업장의 연간 총 예상 손실액 합계
SELECT site_id, SUM(expected_loss) as total_expected_loss
FROM aal_scaled_results
GROUP BY site_id
ORDER BY total_expected_loss DESC;

-- 보험 미가입 상태에서 손실 위험 높은 사업장
SELECT site_id, risk_type, final_aal, expected_loss
FROM aal_scaled_results
WHERE insurance_rate = 0 AND final_aal > 0.1
ORDER BY expected_loss DESC;
```

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| latitude | DECIMAL(9,6) PK | 격자 위도 | 위치 식별 | ✅ 좌표 기반 조회 |
| longitude | DECIMAL(9,6) PK | 격자 경도 | 위치 식별 | ✅ 좌표 기반 조회 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 리스크별 AAL 구분 | ✅ 리스크별 필터링 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 | ✅ 사업장 조회 |
| base_aal | REAL | 기본 AAL (0.0~1.0) | probability_results.aal 참조 | ✅ AAL 계산 입력 |
| vulnerability_scale | REAL | F_vuln (0.9~1.1) | V Score 기반 스케일 계수 | ✅ AAL 보정 |
| final_aal | REAL | 최종 AAL (0.0~1.0) | **핵심** - 취약성/보험 보정된 AAL | ✅ 리포트 핵심 지표 |
| insurance_rate | REAL | 보험 보전율 (0.0~1.0) | 보험 가입률 (0=미가입, 1=완전 보전) | ⚠️ **항상 0.0** - 입력 기능 미구현 |
| expected_loss | BIGINT | 예상 손실액 (원) | **핵심** - 연간 예상 손실액 | ✅ 대시보드, 리포트 |
| calculated_at | TIMESTAMP | 계산 시점 | 데이터 신선도 확인 | ✅ 캐시 무효화 판단 |

**계산 공식 상세:**
```python
# 취약성 스케일 계수 (0.9 ~ 1.1)
F_vuln = 0.9 + (V_score / 100) * 0.2

# 최종 AAL (보험 보정)
final_aal = base_aal * F_vuln * (1 - insurance_rate)

# 예상 손실액 (원)
expected_loss = final_aal * asset_value
```

**예시:**
- base_aal = 0.05 (5% 연간 손실률)
- V_score = 75 (높은 취약성) → F_vuln = 0.9 + 0.75 × 0.2 = 1.05
- insurance_rate = 0.3 (30% 보험 보전)
- asset_value = 10억원
- **final_aal** = 0.05 × 1.05 × 0.7 = **0.03675 (3.675%)**
- **expected_loss** = 0.03675 × 10억 = **3,675만원/년**

**예상 데이터 규모:** 사업장 수 × 9 risk types (사업장별로 저장)

---

### 1.5 Raw Raster Tables (3개)

PostGIS RASTER 타입으로 저장되는 원시 래스터 데이터입니다.

**코드 위치 (공통):**
- **FastAPI**: `fastapi/ai_agent/utils/raster.py`
  - `get_elevation_at_point()`: 좌표의 고도 조회
  - `get_slope_at_point()`: 좌표의 경사도 조회
  - `get_landcover_at_point()`: 좌표의 토지피복 유형 조회
- **ModelOPS**: `modelops/utils/raster_utils.py`
  - 래스터 데이터 처리 유틸리티
- **ETL**: `modelops/etl/local/scripts/04_load_dem.py`, `05_load_drought.py`

#### raw_dem - DEM 원시 래스터

**필요 이유:** 고도/경사도 데이터로 홍수 취약성, 산불 위험도 계산에 필수

**사용처:**
- FastAPI AI Agent Node 2 (`building_characteristics_node`): 사업장 위치의 고도/경사 조회
- ModelOPS VulnerabilityAgent:
  - 저지대(홍수 취약) vs 고지대(산불 취약) 판단
  - 경사도 기반 산사태/토석류 위험 평가
- 리포트: 지형 특성 기반 위험 분석

**쿼리 예시:**
```sql
-- 특정 좌표의 고도 조회 (PostGIS Raster)
SELECT ST_Value(rast, ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 5186)) as elevation
FROM raw_dem
WHERE ST_Intersects(rast, ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 5186));

-- 고도 통계 조회
SELECT (ST_SummaryStats(rast)).*
FROM raw_dem
WHERE rid = 1;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| rid | SERIAL PK | 래스터 타일 ID | 자동 생성 |
| rast | RASTER | PostGIS RASTER | **고도 데이터** (미터 단위), EPSG:5186 |
| filename | TEXT | 원본 파일명 | 데이터 추적용 (예: dem_korea_10m.tif) |

**데이터 소스:** 국토지리정보원 수치표고모델 (10m 해상도)
**좌표계:** EPSG:5186 (Korea 2000 / Central Belt)

---

#### raw_drought - 가뭄 원시 래스터

**필요 이유:** MODIS/SMAP 위성 데이터로 토양수분 기반 실시간 가뭄 모니터링

**사용처:**
- FastAPI AI Agent Node 3 (`risk_assessment_node`): 실시간 가뭄 상황 확인
- ModelOPS DroughtAgent: SPEI12 지수와 결합하여 drought Hazard 계산
- 리포트: 현재 가뭄 상태 시각화

**쿼리 예시:**
```sql
-- 특정 좌표의 토양수분 지수 조회
SELECT ST_Value(rast, ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 4326)) as soil_moisture
FROM raw_drought
WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326));
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| rid | SERIAL PK | 래스터 타일 ID | 자동 생성 |
| rast | RASTER | PostGIS RASTER | **토양수분 지수** (0-100), 주간 업데이트 |
| filename | TEXT | 원본 HDF/H5 파일명 | 데이터 추적용 (예: SMAP_L3_SM_20241201.h5) |

**데이터 소스:** NASA SMAP (Soil Moisture Active Passive)
**갱신 주기:** 주 1회

---

#### raw_landcover - 토지피복도 래스터

**필요 이유:** 도시 불투수 면적 계산 → urban_flood Hazard/Vulnerability 계산의 핵심 데이터

**사용처:**
- FastAPI AI Agent Node 2 (`building_characteristics_node`): 사업장 주변 토지피복 분석
- ModelOPS UrbanFloodAgent: 불투수 면적 비율 → 내수 침수 위험도 계산
- ModelOPS WildfireAgent: 산림 면적 비율 → 산불 위험도 계산
- 리포트: 토지이용 현황 분석

**토지피복 분류 코드:**
| 코드 | 분류 | 설명 | urban_flood 영향 |
|------|------|------|------------------|
| 1 | 시가화/건조 | 주거, 상업, 공업 지역 | 높음 (불투수) |
| 2 | 농업지역 | 논, 밭, 시설재배지 | 중간 |
| 3 | 산림지역 | 활엽수림, 침엽수림 | 낮음 |
| 4 | 초지 | 자연초지, 골프장 | 낮음 |
| 5 | 습지 | 내륙습지, 연안습지 | 낮음 (배수 가능) |
| 6 | 나지 | 자연나지, 인공나지 | 중간 |
| 7 | 수역 | 내륙수, 해양수 | 해당없음 |

**쿼리 예시:**
```sql
-- 특정 좌표의 토지피복 유형 조회
SELECT ST_Value(rast, ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 5186)) as landcover_code
FROM raw_landcover
WHERE ST_Intersects(rast, ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 5186));

-- 반경 1km 내 불투수면 비율 계산
WITH buffer AS (
  SELECT ST_Buffer(ST_Transform(ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326), 5186), 1000) as geom
)
SELECT
  COUNT(*) FILTER (WHERE val = 1)::float / COUNT(*) as impervious_ratio
FROM buffer, raw_landcover,
     LATERAL ST_PixelAsPoints(ST_Clip(rast, geom)) as pixels(val, geom);
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| rid | SERIAL PK | 래스터 타일 ID | 자동 생성 |
| rast | RASTER | PostGIS RASTER | **토지피복 분류 코드** (1-7), EPSG:5186 |
| filename | TEXT | 원본 파일명 | 데이터 추적용 |

**데이터 소스:** 환경부 토지피복도 (30m 해상도)
**갱신 주기:** 연 1회 (Static)

---

### 1.6 Reference Data Tables (3개)

외부 데이터 소스와의 매핑 및 참조 데이터를 저장합니다.

**코드 위치 (공통):**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 700-800)
  - `get_nearest_weather_stations()`: 좌표 기준 최근접 관측소 조회
  - `get_water_stress_ranking()`: 물 스트레스 순위 조회
- **ETL**: `modelops/etl/local/scripts/02_load_weather_stations.py`, `03_create_grid_station_mapping.py`, `10_load_water_stress.py`

#### weather_stations - 기상 관측소 정보

**필요 이유:** WAMIS 유량 관측소 메타데이터 - 격자점과 관측소 매핑의 기준

**사용처:**
- ETL (`03_create_grid_station_mapping.py`): 격자-관측소 매핑 계산
- FastAPI: 관측소 기반 유량 데이터 조회
- ModelOPS RiverFloodAgent: 하천 유량 데이터 기반 홍수 위험 계산

**쿼리 예시:**
```sql
-- 특정 좌표에서 가장 가까운 관측소 3개 조회
SELECT station_id, obscd, obsnm, basin_name,
       ST_Distance(geom, ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326)) as dist_deg
FROM weather_stations
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326)
LIMIT 3;

-- 한강 유역 관측소 목록
SELECT station_id, obscd, obsnm
FROM weather_stations
WHERE basin_name = '한강' AND minyear <= 2020
ORDER BY obsnm;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| station_id | SERIAL PK | 관측소 ID | 내부 식별자 |
| obscd | VARCHAR(10) UK | 관측소 코드 | **핵심** - WAMIS API 연계 키, api_wamis.obscd 참조 |
| obsnm | VARCHAR(100) | 관측소명 | 표시용 (예: "팔당댐") |
| bbsnnm | VARCHAR(50) | 대권역 유역명 | 유역 분류 (예: "한강") |
| sbsncd | VARCHAR(20) | 소권역 유역 코드 | 상세 유역 분류 |
| mngorg | VARCHAR(100) | 관리기관 | 기관 정보 (예: "한국수자원공사") |
| minyear | INTEGER | 데이터 시작 연도 | 데이터 범위 (예: 1980) |
| maxyear | INTEGER | 데이터 종료 연도 | 데이터 범위 (예: 2023) |
| basin_code | INTEGER | 유역 코드 (1~6) | 권역별 필터링 |
| basin_name | VARCHAR(50) | 유역명 | 표시용 (한강/낙동강/금강/섬진강/영산강/제주) |
| latitude | NUMERIC(10,7) | 위도 | 공간 조인 |
| longitude | NUMERIC(11,7) | 경도 | 공간 조인 |
| geom | GEOMETRY | POINT EPSG:4326 | 공간 인덱스 (GIST) |

**예상 데이터 규모:** 1,086 rows
**데이터 소스:** 국가수자원관리종합정보시스템 (WAMIS)

---

#### grid_station_mappings - 격자-관측소 매핑

**필요 이유:** 격자점과 최근접 관측소 3개의 사전 계산된 매핑 - 역거리 가중 보간(IDW) 계산 성능 최적화

**사용처:**
- FastAPI: 격자점 기준 역거리 가중 평균 계산
- ModelOPS RiverFloodAgent: 관측소 유량 데이터 → 격자 보간

**가중치 계산:**
```python
# 역거리 가중 보간 (IDW)
def calculate_weighted_value(stations, values):
    weights = [1 / d.distance_km for d in stations]  # 역거리 가중치
    total_weight = sum(weights)
    return sum(w * v / total_weight for w, v in zip(weights, values))
```

**쿼리 예시:**
```sql
-- 특정 격자점의 최근접 관측소 3개 조회
SELECT station_rank, obscd, obsnm, distance_km
FROM grid_station_mappings
WHERE grid_lat = 37.50 AND grid_lon = 127.00
ORDER BY station_rank;

-- 역거리 가중 평균 계산 (유량 데이터)
WITH station_data AS (
  SELECT m.station_rank, m.distance_km, w.flow_rate
  FROM grid_station_mappings m
  JOIN api_wamis w ON m.obscd = w.obscd
  WHERE m.grid_lat = 37.50 AND m.grid_lon = 127.00
)
SELECT SUM(flow_rate / distance_km) / SUM(1 / distance_km) as weighted_flow
FROM station_data;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| mapping_id | SERIAL PK | 매핑 ID | 내부 식별자 |
| grid_lat | NUMERIC(8,6) | 격자점 위도 | 격자 위치 |
| grid_lon | NUMERIC(9,6) | 격자점 경도 | 격자 위치 |
| basin_code | INTEGER | 유역 코드 (1~6) | 권역 분류 |
| basin_name | VARCHAR(50) | 유역명 | 표시용 |
| station_rank | SMALLINT | 최근접 순위 (1~3) | 가중치 계산용 (1=가장 가까움) |
| obscd | VARCHAR(10) | 관측소 코드 | weather_stations.obscd 참조 |
| obsnm | VARCHAR(100) | 관측소명 | 표시용 |
| station_lat | NUMERIC(10,7) | 관측소 위도 | 관측소 위치 |
| station_lon | NUMERIC(11,7) | 관측소 경도 | 관측소 위치 |
| distance_km | NUMERIC(8,4) | 거리 (km) | **핵심** - IDW 가중치 계산 |
| geom | GEOMETRY | 격자점 POINT | 공간 조인 |

**UNIQUE 제약조건:** (grid_lat, grid_lon, station_rank)

**예상 데이터 규모:** ~292k rows (97,377 grids × 3 stations)
**데이터 생성:** ETL 시 사전 계산 (실시간 조회 성능 최적화)

---

#### water_stress_rankings - WRI Aqueduct 물 스트레스 순위

**필요 이유:** WRI Aqueduct 4.0 데이터로 전세계 물 스트레스 순위 제공 - water_stress Hazard 계산의 핵심 데이터

**사용처:**
- FastAPI AI Agent Node 3 (`risk_assessment_node`): water_stress Hazard 계산
- ModelOPS WaterStressAgent: 물 스트레스 P(H) 및 Hazard Score 계산
- 리포트: 글로벌 물부족 비교 분석 (국가 내 순위, 전세계 순위)

**스코어 해석:**
| score 범위 | cat | label | 설명 |
|------------|-----|-------|------|
| 0.0 ~ 1.0 | 0 | Low | 낮은 물 스트레스 |
| 1.0 ~ 2.0 | 1 | Low-Medium | 낮음-중간 |
| 2.0 ~ 3.0 | 2 | Medium-High | 중간-높음 |
| 3.0 ~ 4.0 | 3 | High | 높은 물 스트레스 |
| 4.0 ~ 5.0 | 4 | Extremely High | 극히 높은 물 스트레스 |

**쿼리 예시:**
```sql
-- 대한민국 경기도의 2050년 물 스트레스 조회
SELECT year, scenario, score, score_ranked, label
FROM water_stress_rankings
WHERE gid_0 = 'KOR' AND name_1 LIKE '%경기%'
  AND year = 2050 AND weight = 'Ind'
ORDER BY scenario;

-- 전세계 상위 10개 물 스트레스 지역 (2050년 비관 시나리오)
SELECT name_0, name_1, score, score_ranked, label
FROM water_stress_rankings
WHERE year = 2050 AND scenario = 'pes' AND weight = 'Ind'
ORDER BY score DESC
LIMIT 10;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| ranking_id | SERIAL PK | 순위 ID | 내부 식별자 |
| gid_0 | VARCHAR(3) | 국가 코드 (ISO) | 국가 필터링 (KOR=대한민국) |
| gid_1 | VARCHAR(20) | 지역 코드 | 국가 내 세부 지역 |
| name_0 | VARCHAR(100) | 국가명 | 표시용 (예: "South Korea") |
| name_1 | VARCHAR(200) | 지역명 | 표시용 (예: "Gyeonggi-do") |
| year | INTEGER | 전망 연도 | 2030, 2050, 2080 |
| scenario | VARCHAR(20) | 시나리오 | opt (낙관), pes (비관) |
| indicator_name | VARCHAR(50) | 지표명 | bws (baseline water stress) |
| weight | VARCHAR(20) | 가중치 유형 | Dom (가정용), Ind (산업용) |
| score | NUMERIC(12,8) | 스코어 (0~5) | **핵심** - 물 스트레스 정도 |
| score_ranked | INTEGER | 순위 | 전세계 대비 순위 (낮을수록 위험) |
| cat | SMALLINT | 카테고리 (0~4) | Hazard Level 매핑용 |
| label | VARCHAR(100) | 레이블 | 위험도 설명 (UI 표시) |
| un_region | VARCHAR(100) | UN 지역 | UN 지역 구분 |
| wb_region | VARCHAR(100) | 세계은행 지역 | WB 지역 구분 |

**예상 데이터 규모:** 161,731 rows
**데이터 소스:** WRI Aqueduct 4.0 (World Resources Institute)

---

### 1.7 Site Additional Data Tables (2개)

사업장 추가 데이터 및 배치 작업 상태를 저장합니다.

> ⚠️ **변경 이력 (2025-12-03)**: 기존 `site_dc_power_usage`, `site_campus_energy_usage` 테이블이 `site_additional_data`로 통합되었습니다.

**코드 위치 (공통):**
- **FastAPI**: `fastapi/ai_agent/utils/database.py` (라인 1200-1300)
  - `get_site_additional_data()`: 사업장 추가 데이터 조회
  - `save_site_additional_data()`: 추가 데이터 저장
- **FastAPI**: `fastapi/api/routes/batch.py`
  - 배치 작업 API 엔드포인트

#### site_additional_data - 사업장 추가 데이터

**필요 이유:** 사용자가 제공하는 추가 데이터 (전력, 보험, 건물 정보)를 범용적으로 저장 - V 계산 및 AAL 계산에 활용

**사용처:**
- FastAPI AI Agent Node 2 (`building_characteristics_node`): 건물/전력 정보 조회
- FastAPI AI Agent Node 4 (`impact_analysis_node`): 보험 정보로 AAL 보정
- ModelOPS VulnerabilityAgent: 건물 정보 기반 V Score 계산
- 리포트: 사용자 제공 데이터 기반 상세 분석

**데이터 카테고리별 structured_data 구조:**

**1. building (건물 정보):**
```json
{
  "building_name": "본사 사옥",
  "total_area_sqm": 15000,
  "floor_count": 12,
  "basement_floors": 3,
  "construction_year": 1995,
  "structure_type": "RC",
  "fire_resistance_grade": "1st"
}
```

**2. asset (자산 정보):**
```json
{
  "total_asset_value_krw": 50000000000,
  "equipment_value_krw": 10000000000,
  "inventory_value_krw": 5000000000
}
```

**3. power (전력 정보):**
```json
{
  "it_power_kwh": 25000,
  "cooling_power_kwh": 8000,
  "total_power_kwh": 40000,
  "pue": 1.5
}
```

**4. insurance (보험 정보):**
```json
{
  "insurance_provider": "삼성화재",
  "coverage_amount_krw": 30000000000,
  "coverage_rate": 0.6,
  "policy_expiry": "2025-12-31"
}
```

**쿼리 예시:**
```sql
-- 특정 사업장의 모든 추가 데이터 조회
SELECT data_category, structured_data, uploaded_at
FROM site_additional_data
WHERE site_id = 'uuid-site-id'
ORDER BY uploaded_at DESC;

-- 보험 정보가 있는 사업장 조회
SELECT site_id, structured_data->>'coverage_rate' as coverage_rate
FROM site_additional_data
WHERE data_category = 'insurance';
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 레코드 ID | 내부 식별자 |
| site_id | UUID | 사업장 ID | Application DB sites.id 참조 |
| data_category | VARCHAR(50) | 데이터 카테고리 | building/asset/power/insurance/custom |
| raw_text | TEXT | 원본 텍스트 | PDF 추출 텍스트 (OCR 결과) |
| structured_data | JSONB | 정형화된 데이터 | **핵심** - 구조화된 JSON |
| file_name | VARCHAR(255) | 업로드 파일명 | 파일 추적 |
| file_s3_key | VARCHAR(500) | S3 저장 키 | 원본 파일 위치 |
| file_size | BIGINT | 파일 크기 (bytes) | 파일 정보 |
| file_mime_type | VARCHAR(100) | MIME 타입 | application/pdf, image/png 등 |
| metadata | JSONB | 추가 메타데이터 | 확장 정보 |
| uploaded_by | UUID | 업로드 사용자 ID | 추적 (users.id) |
| uploaded_at | TIMESTAMP | 업로드 시점 | 추적 |
| expires_at | TIMESTAMP | 만료 시점 | 임시 데이터 관리 |

**UNIQUE 제약조건:** (site_id, data_category, file_name)

---

#### batch_jobs - 배치 작업 상태 추적

**필요 이유:** 후보지 추천, 대량 분석 등 장시간 비동기 작업 상태 추적

**사용처:**
- FastAPI: 배치 작업 생성/진행률 조회 (`GET /api/batch/{batch_id}/status`)
- Frontend: 작업 상태 폴링 (3초마다)
- SpringBoot: 대량 분석 요청 시 배치 작업 생성

**작업 유형 (job_type):**
- `site_recommendation`: 후보지 추천 (AI 분석)
- `bulk_analysis`: 다중 사업장 일괄 분석
- `data_export`: 분석 결과 대량 내보내기
- `report_generation`: 다중 리포트 일괄 생성

**상태 흐름:**
```
queued → running → completed/failed
                 ↳ cancelled (사용자 취소)
```

**쿼리 예시:**
```sql
-- 진행 중인 배치 작업 조회
SELECT batch_id, job_type, status, progress, total_items, completed_items
FROM batch_jobs
WHERE status = 'running'
ORDER BY created_at DESC;

-- 특정 사용자의 최근 배치 작업
SELECT batch_id, job_type, status, progress, created_at
FROM batch_jobs
WHERE created_by = 'uuid-user-id'
ORDER BY created_at DESC
LIMIT 10;
```

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| batch_id | UUID PK | 배치 작업 ID | 내부 식별자 |
| job_type | VARCHAR(50) | 작업 유형 | site_recommendation/bulk_analysis/data_export |
| status | VARCHAR(20) | 상태 | QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED |
| progress | INTEGER | 진행률 (0-100) | UI 진행바 표시 |
| total_items | INTEGER | 전체 항목 수 | 작업 규모 |
| completed_items | INTEGER | 완료 항목 수 | 진행 현황 |
| failed_items | INTEGER | 실패 항목 수 | 에러 추적 |
| input_params | JSONB | 입력 파라미터 | 재실행용 |
| results | JSONB | 결과 데이터 | 배치 결과 (완료 시) |
| error_message | TEXT | 에러 메시지 | 에러 상세 |
| error_stack_trace | TEXT | 스택 트레이스 | 디버깅 |
| estimated_duration_minutes | INTEGER | 예상 소요 시간 | UI 표시 |
| actual_duration_seconds | INTEGER | 실제 소요 시간 | 성능 추적 |
| created_at | TIMESTAMP | 생성 시점 | 기록 |
| started_at | TIMESTAMP | 시작 시점 | 기록 |
| completed_at | TIMESTAMP | 완료 시점 | 기록 |
| expires_at | TIMESTAMP | 만료 시점 | 결과 보관 (기본 7일) |
| created_by | UUID | 생성 사용자 ID | 추적 (users.id)

---

### 1.8 API Cache Tables (11개)

외부 API 데이터를 캐싱하여 저장합니다. API 호출 비용 절감 및 응답 속도 향상을 위한 로컬 캐시입니다.

**코드 위치 (공통):**
- **FastAPI**: `fastapi/ai_agent/utils/api_cache.py`
  - 각 외부 API 호출 및 캐시 관리
- **ETL**: `modelops/etl/api/scripts/` 디렉토리
  - 각 API별 ETL 스크립트

| 테이블 | API 소스 | 사용처 | ETL 스크립트 |
|--------|----------|--------|--------------|
| building_aggregate_cache | 국토교통부 건축물대장 | Vulnerability 계산 (번지 단위 집계) | `06_load_buildings.py` |
| api_wamis | WAMIS 용수이용량 | 물부족 Hazard 계산 | `05_load_wamis.py` |
| api_wamis_stations | WAMIS 관측소 | 유량 관측소 메타데이터 | `05_load_wamis.py` |
| api_river_info | 재난안전데이터 하천정보 | 하천홍수 Hazard 계산 | `01_load_river_info.py` |
| api_emergency_messages | 재난안전데이터 재난문자 | 재난 이력 추적, 리포트 | `02_load_emergency_messages.py` |
| api_typhoon_info | 기상청 태풍정보 | AAL 분석 - 태풍 메타 | `04_load_typhoon.py` |
| api_typhoon_track | 기상청 태풍경로 | AAL 분석 - 태풍 경로 | `04_load_typhoon.py` |
| api_typhoon_td | 기상청 열대저압부 | 태풍 전단계 추적 | `04_load_typhoon.py` |
| api_typhoon_besttrack | 기상청 베스트트랙 | 정밀 태풍 분석 | `09_load_typhoon_besttrack.py` |
| api_disaster_yearbook | 행정안전부 재해연보 | 과거 피해 통계 | `15_load_disaster_yearbook.py` |
| api_vworld_geocode | VWorld 역지오코딩 | 좌표 → 주소 변환 | `03_load_geocode.py` |

#### 주요 테이블 상세

**building_aggregate_cache - 건축물대장 집계 캐시**

**필요 이유:** 국토교통부 건축물대장 API 호출 결과를 번지 단위로 집계하여 캐싱 - Vulnerability 계산 최적화

**사용처:**
- FastAPI AI Agent Node 2 (`building_characteristics_node`): 건물 연식, 구조, 층수 조회
- ModelOPS VulnerabilityAgent: 건물 특성 기반 V Score 계산
- 리포트: 건물 현황 분석

**주요 컬럼:** `pnu` (필지고유번호), `avg_build_year` (평균 건축년도), `main_structure` (주요 구조), `total_floor_area` (연면적 합계), `building_count` (건물 수)

**api_vworld_geocode - VWorld 역지오코딩 캐시**

**필요 이유:** VWorld API 호출 결과 캐싱 - 동일 좌표 반복 조회 시 API 호출 비용 절감

**사용처:**
- FastAPI AI Agent Node 1 (`data_collection_node`): 좌표 → 주소 변환
- SpringBoot: 사업장 등록 시 주소 자동완성
- 리포트: 위치 정보 표시

**주요 컬럼:** `latitude`, `longitude`, `road_address` (도로명 주소), `jibun_address` (지번 주소), `sido`, `sigungu`, `dong`

**api_typhoon_* 테이블들 - 태풍 정보 캐시**

**필요 이유:** 기상청 태풍 API 데이터 캐싱 - typhoon Hazard 및 AAL 계산에 활용

**사용처:**
- ModelOPS TyphoonProbabilityAgent: 과거 태풍 이력 기반 P(H) 계산
- ModelOPS TyphoonHazardAgent: 태풍 강도/경로 기반 Hazard Score 계산
- 리포트: 태풍 이력 및 예상 피해 분석

**쿼리 예시:**
```sql
-- 특정 지역 인근 태풍 이력 조회
SELECT ti.typoon_name, ti.max_wind_speed, tt.latitude, tt.longitude
FROM api_typhoon_info ti
JOIN api_typhoon_track tt ON ti.typhoon_id = tt.typhoon_id
WHERE ST_DWithin(
  ST_SetSRID(ST_MakePoint(tt.longitude, tt.latitude), 4326),
  ST_SetSRID(ST_MakePoint(127.0, 37.5), 4326),
  2  -- 2도 반경 (~200km)
)
ORDER BY ti.start_date DESC;

-- 건축물대장 캐시에서 건물 정보 조회
SELECT pnu, avg_build_year, main_structure, total_floor_area
FROM building_aggregate_cache
WHERE pnu = '1168010100100010000';
```

---

### 1.9 Site Risk Tables (3개)

Site별 최종 리스크 분석 결과 및 이전 후보지 정보를 저장합니다.

> ⚠️ **신규 추가 (2025-12-10)**: site_risk_results, site_risk_summary, candidate_sites 테이블 추가
> ⚠️ **스키마 변경 (2025-12-10)**: 시나리오별/연도별 분석을 위해 ssp_scenario, target_year, probability 컬럼 추가

**코드 위치 (공통):**
- **FastAPI 저장**: `fastapi/ai_agent/nodes/risk_assessment_node.py`
  - `save_site_risk_results()`: H × E × V 계산 결과 저장
  - `save_site_risk_summary()`: 9개 리스크 요약 저장
- **FastAPI 조회**: `fastapi/ai_agent/utils/database.py` (라인 1300-1400)
  - `get_site_risk_results()`: 사업장 리스크 결과 조회
  - `get_site_risk_summary()`: 사업장 리스크 요약 조회
- **SpringBoot 조회**: FastAPI API 통해 간접 조회 (`GET /api/analysis/results/{site_id}`)

#### site_risk_results - Site별 시나리오/연도/리스크별 결과

**필요 이유:** FastAPI AI Agent가 계산한 site별 시나리오/연도/리스크타입별 최종 결과 저장 - **H × E × V = Physical Risk Score**

**사용처:**
- FastAPI AI Agent Node 3 (`risk_assessment_node`): H × E × V 계산 결과 저장
- FastAPI AI Agent Node 6 (`report_generation_node`): 리포트 생성 시 조회
- SpringBoot: 대시보드 리스크 조회 (FastAPI API 통해)
- Frontend: 리스크 상세 분석 페이지

**쿼리 예시:**
```sql
-- 특정 사업장의 SSP2-2050 시나리오 9개 리스크 조회
SELECT risk_type, hazard_score, exposure_score, vulnerability_score,
       physical_risk_score_100, risk_level
FROM site_risk_results
WHERE site_id = 'uuid-site-id'
  AND ssp_scenario = 'SSP2' AND target_year = 2050
ORDER BY physical_risk_score_100 DESC;

-- 가장 높은 리스크 타입 조회
SELECT risk_type, physical_risk_score_100, risk_level
FROM site_risk_results
WHERE site_id = 'uuid-site-id'
ORDER BY physical_risk_score_100 DESC
LIMIT 1;
```

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| site_id | UUID PK | 사업장 ID | Application DB sites 참조 | ✅ 사업장 조회 |
| ssp_scenario | VARCHAR(10) PK | SSP 시나리오 | SSP1/SSP2/SSP3/SSP5 | ✅ 시나리오별 필터링 |
| target_year | INTEGER PK | 분석 연도 | 2030/2050/2080 | ✅ 연도별 필터링 |
| risk_type | VARCHAR(50) PK | 위험 유형 (9가지) | 복합 PK | ✅ 리스크별 필터링 |
| hazard_score | REAL | H Score (0.0~1.0) | Hazard | ✅ H × E × V 계산 |
| exposure_score | REAL | E Score (0.0~1.0) | Exposure | ✅ H × E × V 계산 |
| vulnerability_score | REAL | V Score (0.0~1.0) | Vulnerability | ✅ H × E × V 계산 |
| probability | REAL | P(H) (0.0~1.0) | 발생 확률 | ✅ 리포트 표시 |
| aal_percentage | REAL | AAL (%) | 연평균 손실률 | ✅ 대시보드, 리포트 |
| physical_risk_score | REAL | H × E × V (0.0~1.0) | 물리적 리스크 | ✅ 정규화 전 원본값 |
| physical_risk_score_100 | REAL | 0~100 스케일 | UI 표시용 | ✅ Frontend 게이지 |
| risk_level | VARCHAR(20) | 물리적 리스크 등급 | VERY_HIGH/HIGH/MEDIUM/LOW/VERY_LOW | ✅ Frontend 색상, 필터 |
| calculation_details | JSONB | 계산 상세 | 디버깅용 | ⚠️ **제한적 사용** - 디버깅용 |
| calculated_at | TIMESTAMP | 계산 시점 | 신선도 확인 | ✅ 캐시 무효화 |
| analysis_job_id | UUID | 분석 작업 ID | 추적용 | ✅ 분석 이력 추적 |

**PK 구조:** (site_id, ssp_scenario, target_year, risk_type)

**예상 데이터 규모:** 사이트 수 × 4 시나리오 × 3 연도 × 9 리스크 = 사이트 × 108

---

#### site_risk_summary - Site별 시나리오/연도별 요약

**필요 이유:** Site별 시나리오/연도별 9개 리스크 타입을 통합한 요약 정보

**사용처:**
- FastAPI: 전체 리스크 등급 조회
- SpringBoot: 대시보드 요약

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| site_id | UUID PK | 사업장 ID | Application DB sites 참조 | ✅ 사업장 조회 |
| ssp_scenario | VARCHAR(10) PK | SSP 시나리오 | SSP1/SSP2/SSP3/SSP5 | ✅ 시나리오별 필터링 |
| target_year | INTEGER PK | 분석 연도 | 2030/2050/2080 | ✅ 연도별 필터링 |
| avg_physical_risk_score | REAL | 9개 평균 (0~100) | 전체 물리적 리스크 | ✅ 대시보드 표시 |
| total_aal_percentage | REAL | 9개 합계 (%) | 전체 AAL | ✅ 대시보드, 리포트 |
| avg_hazard_score | REAL | H 평균 (0~1) | 평균 Hazard | ✅ 리포트 요약 |
| avg_exposure_score | REAL | E 평균 (0~1) | 평균 Exposure | ✅ 리포트 요약 |
| avg_vulnerability_score | REAL | V 평균 (0~1) | 평균 Vulnerability | ✅ 리포트 요약 |
| highest_risk_type | VARCHAR(50) | 가장 높은 리스크 | 핵심 리스크 | ✅ 대시보드 하이라이트 |
| highest_risk_score | REAL | 해당 점수 | 핵심 리스크 점수 | ✅ 대시보드 하이라이트 |
| overall_risk_grade | VARCHAR(20) | 전체 등급 | A/B/C/D/F | ✅ 대시보드 뱃지 |
| calculated_at | TIMESTAMP | 계산 시점 | 신선도 확인 | ✅ 캐시 무효화 |
| analysis_job_id | UUID | 분석 작업 ID | 추적용 | ✅ 분석 이력 추적 |

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
| risk_level | VARCHAR(20) | 리스크 레벨 | VERY_LOW/LOW/MEDIUM/HIGH/VERY_HIGH |
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
| User | 5개 | 사용자 인증 (users, password_reset_tokens, refresh_tokens, google_oauth_tokens, verification_codes) |
| Site | 1개 | 사업장 관리 |
| Analysis | 1개 | AI 분석 작업 (analysis_jobs) |
| Report | 1개 | 리포트 관리 |
| Meta | 2개 | 메타데이터 (industries, hazard_types) |
| **합계** | **10개** | 생성 완료 ✓ |

> **SQL 파일:**
> - `create_springboot_tables.sql` - 10개 테이블 포함
>
> ⚠️ **삭제된 테이블 (2025-12):**
> - `analysis_results` - 미구현으로 삭제

---

### 2.2 User Tables (5개)

#### users - 사용자 정보

**필요 이유:** 사용자 인증 및 시스템 전반의 사용자 식별

**코드 위치:**
- **Entity**: `springboot/polaris_backend/src/main/java/com/skax/physicalrisk/domain/user/entity/User.java`
- **Repository**: `UserRepository.java` - `findByEmail()`, `existsByEmail()`
- **Service**: `UserService.java` - `getCurrentUser()`, `updateUser()`, `deleteUser()`
- **Controller**: `UserController.java`, `AuthController.java`

**사용처:**
- SpringBoot AuthController: 로그인 (`POST /api/auth/login`) - email로 사용자 조회 후 비밀번호 검증
- SpringBoot AuthController: 회원가입 (`POST /api/auth/register`) - existsByEmail()로 중복 검사 후 생성
- SpringBoot UserController: 내 정보 조회 (`GET /api/users/me`)
- SpringBoot UserController: 정보 수정 (`PATCH /api/users/me`) - language 설정 변경
- SpringBoot UserController: 회원 탈퇴 (`DELETE /api/users/me`) - 계층적 삭제 (sites, reports, tokens 모두 삭제)
- Frontend: `useAuthStore` - accessToken, refreshToken, userId, userName 저장

**관계:**
- `sites` (1:N): 사용자가 여러 사업장 소유
- `refresh_tokens` (1:N): 사용자가 여러 리프레시 토큰 보유 (멀티 디바이스)
- `password_reset_tokens` (1:N): 비밀번호 재설정 토큰
- `reports` (1:N): 사용자가 생성한 리포트들 (user_id 참조)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 사용자 ID | 모든 하위 테이블의 FK 참조 대상 |
| email | VARCHAR(255) UK | 이메일 | 로그인 ID, `findByEmail()`로 조회 |
| name | VARCHAR(100) | 이름 | Frontend 표시용, 리포트 생성자명 |
| password | VARCHAR(255) | 비밀번호 (암호화) | BCrypt 암호화, 로그인 시 검증 |
| language | VARCHAR(10) | 언어 (ko/en) | Frontend UI 언어, 리포트 언어 설정 |
| job_done | BOOLEAN | 분석 작업 완료 여부 | 기본값 false, 첫 분석 완료 시 true |

---

#### password_reset_tokens - 비밀번호 재설정 토큰

**필요 이유:** 이메일 기반 비밀번호 재설정 기능 (UUID 토큰 방식)

**코드 위치:**
- **Entity**: `springboot/.../domain/user/entity/PasswordResetToken.java`
- **Repository**: `PasswordResetTokenRepository.java` - `findByToken()`, `findByUserAndUsedFalseAndExpiresAtAfter()`, `deleteByExpiresAtBefore()`
- **Service**: `AuthService.java` - `confirmPasswordReset()`

**사용처:**
- SpringBoot AuthController: 비밀번호 재설정 요청 (`POST /api/auth/reset-password-request`)
  - 30분 유효 토큰 생성 후 이메일 발송
- SpringBoot AuthController: 비밀번호 변경 확인 (`POST /api/auth/confirm-password-reset`)
  - 토큰 검증 → 만료/사용 여부 확인 → 비밀번호 변경 → used=true 처리
- 스케줄러: 만료된 토큰 자동 삭제 (`deleteByExpiresAtBefore()`)

**비즈니스 로직:**
1. 사용자가 비밀번호 잊음 → UUID 기반 토큰 생성 (30분 유효)
2. 이메일로 토큰 포함 링크 발송
3. 링크 클릭 시 `findByToken()`으로 조회
4. 만료 여부 + 미사용 여부 검증
5. 유효하면 새 비밀번호로 변경 후 `used = true`

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 토큰 ID | 내부 식별자 |
| user_id | UUID FK | 사용자 ID | users 참조, 인덱스 생성됨 |
| token | VARCHAR(255) UK | 재설정 토큰 | URL 파라미터, `findByToken()`으로 조회 |
| expires_at | TIMESTAMP | 만료 시간 | 생성 후 30분, 검증 시 now()와 비교 |
| created_at | TIMESTAMP | 생성 시간 | 기본값 now(), 감사 추적용 |
| used | BOOLEAN | 사용 여부 | 기본값 false, 사용 후 true로 변경 |

---

#### refresh_tokens - 리프레시 토큰

**필요 이유:** JWT 리프레시 토큰 관리 (로그인 세션 유지, 멀티 디바이스 지원)

**코드 위치:**
- **Entity**: `springboot/.../domain/user/entity/RefreshToken.java`
- **Repository**: `RefreshTokenRepository.java` - `findByToken()`, `findByUser()`, `revokeAllByUser()`, `deleteExpiredTokens()`, `deleteRevokedTokens()`
- **Service**: `AuthService.java`

**사용처:**
- SpringBoot AuthController: 로그인 (`POST /api/auth/login`)
  - AccessToken(15분) + RefreshToken(7일) 발급, DB에 RefreshToken 저장
- SpringBoot AuthController: 토큰 갱신 (`POST /api/auth/refresh`)
  - RefreshToken 검증 → 기존 토큰 폐기 → 새 토큰 발급
- SpringBoot AuthController: 로그아웃 (`POST /api/auth/logout`)
  - `revokeAllByUser()`로 모든 RefreshToken 무효화
- Frontend: `useAuthStore` - refreshAccessToken() 자동 호출

**비즈니스 로직:**
1. 로그인 성공 → AccessToken + RefreshToken 발급, DB에 RefreshToken 저장
2. AccessToken 만료 → RefreshToken으로 새 AccessToken 요청
3. DB에서 `findByToken()` 검증 (폐기 여부, 만료 여부)
4. 유효하면 기존 토큰 폐기 후 새 토큰 발급
5. 로그아웃 시 `revokeAllByUser()`로 모든 토큰 무효화

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 토큰 ID | 내부 식별자 |
| user_id | UUID FK | 사용자 ID | users 참조 (CASCADE 삭제), 인덱스 생성됨 |
| token | VARCHAR(500) UK | JWT 리프레시 토큰 | `findByToken()`으로 검증, 인덱스 생성됨 |
| expires_at | TIMESTAMP | 만료 시간 | 기본 7일, 인덱스 생성됨 |
| created_at | TIMESTAMP | 생성 시간 | 기본값 now() |
| revoked | BOOLEAN | 무효화 여부 | 로그아웃 시 true, 토큰 갱신 시 true |
| device_info | VARCHAR(255) | User-Agent 정보 | 멀티 디바이스 추적, 보안 감사 |
| ip_address | VARCHAR(45) | 접속 IP | IPv4/IPv6 지원, 보안 감사 |

---

#### google_oauth_tokens - Google OAuth 토큰

**필요 이유:** Google Calendar, Drive 연동을 위한 OAuth 토큰 관리

**코드 위치:**
- **Entity**: `springboot/.../domain/auth/entity/GoogleOAuthToken.java` (예정)
- **Repository**: `GoogleOAuthTokenRepository.java` - `findByUserId()`

**사용처:**
- Google Calendar 일정 연동
- Google Drive 리포트 저장

**비즈니스 로직:**
1. 사용자가 Google 계정 연결 → OAuth 인증 플로우
2. refresh_token 영구 저장 (핵심)
3. access_token은 1시간마다 갱신 (캐시용)
4. API 호출 전 expires_at 확인 → 만료 시 refresh_token으로 갱신

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | OAuth 토큰 ID | 내부 식별자 |
| user_id | UUID FK | 사용자 ID | users 참조 (CASCADE 삭제), 인덱스 생성됨 |
| refresh_token | VARCHAR(500) | Google 리프레시 토큰 | **핵심** - 영구 보관, 토큰 갱신에 사용 |
| access_token | VARCHAR(500) | Google 액세스 토큰 | 캐시용, 1시간마다 갱신 |
| expires_at | TIMESTAMP | Access Token 만료 시간 | API 호출 전 만료 확인 |
| created_at | TIMESTAMP | 생성 시간 | 기본값 now() |
| updated_at | TIMESTAMP | 업데이트 시간 | 토큰 갱신 시 업데이트 |

---

#### verification_codes - 이메일 인증 코드

**필요 이유:** 회원가입, 비밀번호 재설정 시 이메일 인증번호 관리

**코드 위치:**
- **Entity**: `springboot/.../domain/auth/entity/VerificationCode.java` (예정)
- **Repository**: `VerificationCodeRepository.java` - `findByEmailAndPurposeAndVerifiedFalse()`

**사용처:**
- SpringBoot AuthController: 인증번호 발송 (`POST /api/auth/send-verification`)
- SpringBoot AuthController: 인증번호 확인 (`POST /api/auth/verify-code`)

**비즈니스 로직:**
1. 사용자가 인증번호 요청 → 6자리 랜덤 코드 생성
2. 이메일로 인증번호 발송
3. 5분 유효 (expires_at = now() + 5분)
4. 인증 성공 시 verified = true
5. 만료되거나 인증된 코드는 무시

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 인증 코드 ID | 내부 식별자 |
| email | VARCHAR(255) | 인증 대상 이메일 | 인덱스 생성됨, 조회 키 |
| code | VARCHAR(6) | 6자리 인증번호 | 100000~999999 범위 |
| purpose | VARCHAR(20) | 인증 목적 | REGISTER(회원가입) / PASSWORD_RESET(비밀번호 재설정) |
| verified | BOOLEAN | 인증 완료 여부 | 기본값 false, 인증 성공 시 true |
| expires_at | TIMESTAMP | 만료 시간 | 생성 후 5분, 인덱스 생성됨 |
| created_at | TIMESTAMP | 생성 시간 | 기본값 now() |

---

### 2.3 Site Tables (1개)

#### sites - 사업장 정보

**필요 이유:** 기후 리스크 분석 대상 사업장 정보 관리 (시스템의 핵심 도메인)

**코드 위치:**
- **Entity**: `springboot/.../domain/site/entity/Site.java`
- **Repository**: `SiteRepository.java` - `findByUser()`, `findByIdAndUser()`, `searchByUserAndKeyword()`, `countByUser()`
- **Service**: `SiteService.java` - `getSites()`, `createSite()`, `updateSite()`, `deleteSite()`
- **Controller**: `SiteController.java`

**사용처:**
- SpringBoot SiteController: 사업장 목록 조회 (`GET /api/site`) - `findByUser()`
- SpringBoot SiteController: 사업장 검색 (`GET /api/site?siteName={name}`)
- SpringBoot SiteController: 사업장 생성 (`POST /api/site`)
- SpringBoot SiteController: 사업장 수정 (`PUT /api/site?siteId={id}`)
- SpringBoot SiteController: 사업장 삭제 (`DELETE /api/site?siteId={id}`) - cascade로 analysis_jobs, reports 삭제
- Frontend: `useSitesStore` - allSites[], fetchSites(), createSite(), updateSite(), deleteSite()
- FastAPI: 분석 시작 시 latitude, longitude로 격자 매핑
- ModelOPS: 좌표 기반 location_grid 조회

**관계:**
- `User` (N:1): Site는 한 명의 User에 속함 (`findByIdAndUser()`로 권한 확인)
- `analysis_jobs` (1:N): 사업장별 분석 작업 이력

**비즈니스 로직:**
1. 사용자가 새 사업장 등록 → name, 위도, 경도, 주소 저장
2. 분석 시작 시 좌표로 FastAPI에 전달 → location_grid 매핑
3. 삭제 시 cascade로 analysis_jobs 삭제

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 사업장 ID | analysis_jobs의 FK 참조 대상 |
| user_id | UUID FK | 소유자 ID | users 참조, 인덱스 생성됨, 권한 확인에 사용 |
| name | VARCHAR(255) | 사업장 이름 | Frontend 표시용, 검색 대상 |
| road_address | VARCHAR(500) | 도로명 주소 | 위치 정보, VWorld 역지오코딩 결과 |
| jibun_address | VARCHAR(500) | 지번 주소 | 위치 정보 (레거시) |
| latitude | DECIMAL(10,8) | 위도 | **핵심** - location_grid 매핑, 복합 인덱스 |
| longitude | DECIMAL(11,8) | 경도 | **핵심** - location_grid 매핑, 복합 인덱스 |
| type | VARCHAR(100) | 업종/유형 | industries 코드 참조, V 계수 계산에 사용 |

---

### 2.4 Analysis Tables (1개)

#### analysis_jobs - AI 분석 작업

**필요 이유:** FastAPI AI Agent 분석 작업 상태 추적 (비동기 분석 진행률 모니터링)

**코드 위치:**
- **Entity**: `springboot/.../domain/analysis/entity/AnalysisJob.java`
- **Repository**: `AnalysisJobRepository.java` - `findByJobId()`, `findFirstBySite()`, `findBySiteAndStatus()`, `existsBySiteAndStatus()`
- **Service**: `AnalysisService.java` - `startAnalysis()`, `startAnalysisMultiple()`, `getAnalysisStatus()`, `getDashboardSummary()`
- **Controller**: `AnalysisController.java`

**사용처:**
- SpringBoot AnalysisController: 분석 시작 (`POST /api/analysis/start`)
  - AnalysisJob 생성 (status=QUEUED) → FastAPI 호출 → job_id 저장
- SpringBoot AnalysisController: 상태 조회 (`GET /api/analysis/status`)
  - `findByJobId()`로 조회, Frontend에서 3초마다 폴링
- SpringBoot AnalysisController: 대시보드 요약 (`GET /api/dashboard/summary`)
- Frontend: `useAnalysis` composable - startAnalysis(), pollAnalysisStatus() (3초마다 자동 폴링)

**비즈니스 로직:**
1. 사용자가 분석 시작 요청 → AnalysisJob 생성 (status=QUEUED)
2. FastAPI 서버로 REST API 호출
3. FastAPI로부터 job_id 수신 → DB에 저장
4. 주기적으로 `getAnalysisStatus()` 호출로 진행 상태 모니터링
5. 진행률 업데이트: progress, currentNode, estimatedCompletionTime 변경
6. 완료 시 status=COMPLETED, completedAt 설정
7. 실패 시 status=FAILED, errorCode, errorMessage 설정

**LangGraph 노드명 (current_node):**
- `data_collection_node` (0-10%)
- `building_characteristics_node` (10-30%)
- `risk_assessment_node` (30-50%)
- `impact_analysis_node` (50-70%)
- `strategy_generation_node` (70-85%)
- `report_generation_node` (85-100%)

| 컬럼명 | 타입 | 설명 | 역할 |
|--------|------|------|------|
| id | UUID PK | 작업 ID | 내부 식별자 |
| site_id | UUID FK | 사업장 ID | sites 참조, 인덱스 생성됨 |
| job_id | VARCHAR(100) UK | FastAPI 작업 ID | API 연동 키, `findByJobId()`로 조회, 인덱스 생성됨 |
| status | VARCHAR(20) | 상태 | QUEUED/RUNNING/COMPLETED/FAILED, 인덱스 생성됨 |
| progress | INTEGER | 진행률 (0-100) | Frontend 진행바 표시 |
| current_node | VARCHAR(100) | 현재 노드 | LangGraph 노드명, UI에 단계 표시 |
| created_at | TIMESTAMP | 생성 시간 | 작업 시작 시점 |
| started_at | TIMESTAMP | 시작 시간 | 실제 처리 시작 시점 |
| completed_at | TIMESTAMP | 완료 시간 | 작업 완료 시점 |
| estimated_completion_time | TIMESTAMP | 예상 완료 시간 | UI에 남은 시간 표시 |
| error_code | VARCHAR(50) | 에러 코드 | 에러 분류 (TIMEOUT, API_ERROR 등) |
| error_message | TEXT | 에러 메시지 | 에러 상세 내용 |
| updated_at | TIMESTAMP | 수정 시간 | 상태 변경 시점 추적 |

---

### 2.5 Report Tables

#### reports - 리포트 정보

**필요 이유:** 생성된 리포트 내용을 JSONB로 저장 (S3 제거, 단순화)

**코드 위치:**
- **Entity**: `springboot/.../domain/report/entity/Report.java`
- **Repository**: `ReportRepository.java` - `findByUserId()`
- **Controller**: `ReportController.java`

**사용처:**
- SpringBoot ReportController: 리포트 조회/저장
- Frontend: 리포트 뷰어

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| id | UUID PK | 리포트 ID | 내부 식별자 | ✅ |
| user_id | UUID FK | 사용자 ID | users 참조 | ✅ |
| report_content | JSONB | 리포트 내용 | 전체 리포트 데이터 JSON | ✅ |

> ⚠️ **변경 이력 (2025-12)**: S3 관련 컬럼 제거 (`s3_key`, `file_size`, `expires_at` 등), `site_id` 제거, JSONB로 단순화

---

### 2.6 Meta Tables

#### hazard_types - 위험 요인 메타데이터

**필요 이유:** 시스템에서 지원하는 9가지 위험 유형 정의 (마스터 데이터)

**코드 위치:**
- **Entity**: `springboot/.../domain/meta/entity/HazardType.java`
- **Repository**: `HazardTypeRepository.java` - `findByCode()`, `findAll()`
- **Service**: `MetaService.java` - `getAllHazardTypes()`
- **Controller**: `MetaController.java`

**사용처:**
- SpringBoot MetaController: 위험 유형 목록 (`GET /api/meta/hazards`)
- Frontend: `useMeta` composable - fetchHazardTypes() → 위험 유형 필터 드롭다운
- FastAPI: AI Agent에서 9개 리스크별 분석 수행 시 참조
- ModelOPS: probability_results, hazard_results의 risk_type 필드와 매핑
- Frontend AnalysisView: 위험 유형별 탭/필터 표시

**연관 테이블:**
- `probability_results.risk_type` - 해당 code와 동일한 값
- `hazard_results.risk_type` - 해당 code와 동일한 값
- `site_risk_results.risk_type` - 해당 code와 동일한 값

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| id | SERIAL PK | ID | 내부 식별자 | ✅ Spring `findAll()` |
| code | VARCHAR(50) UK | 코드 | **핵심** - risk_type 필드와 매핑, `findByCode()`로 조회 | ✅ Frontend 필터, ModelOPS Agent |
| name | VARCHAR(100) | 한글 이름 | Frontend 표시용 | ✅ Frontend `{{ hazard.name }}` 표시 |
| name_en | VARCHAR(100) | 영문 이름 | 다국어 지원, language=en일 때 사용 | ✅ Frontend (language=en) |
| category | VARCHAR(20) | 카테고리 | TEMPERATURE/WATER/WIND/OTHER, UI 그룹핑용 | ✅ Frontend 카테고리별 그룹핑 |
| description | TEXT | 설명 | 위험 유형 상세 설명 | ⚠️ **제한적 사용** - 툴팁용으로만 표시 |

**초기 데이터 (9개):**
| code | name | category | ModelOPS Agent |
|------|------|----------|----------------|
| extreme_heat | 극심한 고온 | TEMPERATURE | ExtremeHeatProbabilityAgent |
| extreme_cold | 극심한 한파 | TEMPERATURE | ExtremeColdProbabilityAgent |
| wildfire | 산불 | OTHER | WildfireProbabilityAgent |
| drought | 가뭄 | WATER | DroughtProbabilityAgent |
| water_stress | 물부족 | WATER | WaterStressProbabilityAgent |
| sea_level_rise | 해수면 상승 | WATER | SeaLevelRiseProbabilityAgent |
| river_flood | 하천 홍수 | WATER | RiverFloodProbabilityAgent |
| urban_flood | 도시 홍수 | WATER | UrbanFloodProbabilityAgent |
| typhoon | 태풍 | WIND | TyphoonProbabilityAgent |

---

#### industries - 업종 메타데이터

**필요 이유:** 업종별 취약성 계수 관리 (V 계산에 영향)

**코드 위치:**
- **Entity**: `springboot/.../domain/meta/entity/Industry.java`
- **Repository**: `IndustryRepository.java` - `findByCode()`, `findAll()`
- **Service**: `MetaService.java` - `getAllIndustries()`
- **Controller**: `MetaController.java`

**사용처:**
- SpringBoot MetaController: 업종 목록 (`GET /api/meta/industries`)
- Frontend: `useMeta` composable - fetchIndustries() → 사업장 등록 시 업종 선택 드롭다운
- Frontend SiteManagementView: 사업장 생성/수정 시 업종 선택
- FastAPI: AI Agent의 VulnerabilityAgent에서 업종별 취약성 계수 조회
- ModelOPS: vulnerability_results 계산 시 업종별 가중치 적용

**업종별 취약성 계수 예시:**
- `data_center`: 전력 중단에 매우 취약 (V 가중치 높음)
- `agriculture`: 가뭄/홍수에 매우 취약
- `manufacturing`: 홍수/태풍에 취약
- `logistics`: 태풍/홍수에 취약

| 컬럼명 | 타입 | 설명 | 역할 | 실제 사용 |
|--------|------|------|------|----------|
| id | SERIAL PK | ID | 내부 식별자 | ✅ Spring `findAll()` |
| code | VARCHAR(50) UK | 코드 | sites.type과 매핑, `findByCode()`로 조회 | ✅ Frontend 드롭다운 value, FastAPI industry 파라미터 |
| name | VARCHAR(100) | 업종 이름 | Frontend 드롭다운 표시용 | ✅ Frontend `{{ industry.name }}` 표시 |
| description | TEXT | 설명 | 업종 상세 설명, 취약성 특성 | ⚠️ **NOT_USED** - DB에 저장되지만 현재 사용처 없음 |

> ⚠️ **주의**: `description` 컬럼은 현재 Spring, FastAPI, Frontend 어디에서도 조회/사용되지 않습니다.
> `findByCode()`는 Repository에 정의되어 있지만 실제로 호출하는 코드가 없습니다.

**초기 데이터 (16개):**
| code | name | 취약성 특성 |
|------|------|------------|
| data_center | 데이터센터 | 전력 중단, 냉각 시스템 |
| manufacturing | 제조업 | 생산 라인 중단, 자재 손상 |
| logistics | 물류/창고 | 교통 마비, 재고 손상 |
| retail | 유통/판매 | 고객 접근, 재고 손실 |
| office | 사무/오피스 | 업무 연속성 |
| healthcare | 의료/복지 | 환자 안전, 의료장비 |
| education | 교육 | 학생 안전 |
| energy | 에너지/발전 | 발전 중단, 송전 피해 |
| finance | 금융 | 시스템 가용성 |
| hospitality | 숙박/관광 | 고객 안전, 예약 취소 |
| agriculture | 농업/축산 | 작물 피해, 가축 폐사 |
| chemical | 화학/정유 | 환경 오염, 폭발 위험 |
| food | 식품/음료 | 식품 안전, 냉장 |
| pharmaceutical | 제약/바이오 | 연구 중단, 의약품 손상 |
| transportation | 교통/운송 | 운행 중단 |
| other | 기타 | 일반적 취약성 |

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
   site_risk_results ← Datawarehouse 저장
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
| | analysis_jobs | AI 분석 작업 관리 |
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
*최종 수정: 2025-12-12*
