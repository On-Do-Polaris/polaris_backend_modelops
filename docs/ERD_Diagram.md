# SKALA Physical Risk AI - ERD 다이어그램

> SKALA Physical Risk AI System의 전체 데이터베이스 ERD
>
> 최종 수정일: 2025-11-25
> 버전: v03.0 (Wide Format 전환 - 기후 데이터 14개 테이블)

---

## 📋 목차

1. [개요](#개요)
2. [데이터베이스 아키텍처](#데이터베이스-아키텍처)
3. [Application Database ERD](#application-database-erd)
4. [Datawarehouse ERD](#datawarehouse-erd)
5. [데이터베이스 간 참조](#데이터베이스-간-참조)

---

## 개요
     
SKALA Physical Risk AI 시스템은 **이중 데이터베이스 아키텍처**를 사용합니다:

- **Application DB** (포트 5432): Spring Boot 애플리케이션용 - 사용자, 사업장, 분석, 리포트 관리
- **Datawarehouse** (포트 5433): FastAPI AI Agent용 - 기후 데이터, 공간 데이터, API 캐시

---

## 데이터베이스 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  SKALA Physical Risk AI                 │
├─────────────────────┬───────────────────────────────────┤
│  Application DB     │        Datawarehouse              │
│  (PostgreSQL 16)    │        (PostGIS 16-3.4)           │
│                     │                                   │
│  포트: 5432         │  포트: 5433                        │
│  테이블: 14개        │  테이블: 62개                      │
│  크기: ~100 GB      │  크기: ~2-3 TB                     │
└─────────────────────┴───────────────────────────────────┘
```

---

## Application Database ERD

### 개요
- **데이터베이스명**: `skala_application`
- **포트**: 5432
- **엔진**: PostgreSQL 16
- **Extension**: uuid-ossp
- **테이블 수**: 14개
- **주요 기능**: 사용자 관리, 사업장 관리, 분석 추적, 리포트 생성

### ERD (Mermaid)

```mermaid
erDiagram
    %% Application Database (skala_application)

    users ||--o{ sites : "has"
    users {
        uuid user_id PK
        varchar email UK
        varchar password_hash
        varchar name
        varchar organization
        varchar language
        varchar role
        timestamptz created_at
        timestamptz last_login_at
        timestamptz updated_at
    }

    sites ||--o{ analysis_jobs : "has"
    sites ||--o{ physical_risk_scores : "has"
    sites ||--o{ reports : "has"
    sites {
        uuid site_id PK
        uuid user_id FK
        varchar name
        varchar address
        varchar city
        numeric latitude
        numeric longitude
        varchar admin_code "Ref:DW.location_admin"
        varchar industry
        integer building_age
        varchar building_type
        boolean seismic_design
        numeric floor_area
        bigint asset_value
        integer employee_count
        varchar main_hazard
        integer risk_score
        varchar risk_level
        timestamptz last_analyzed_at
        timestamptz created_at
        timestamptz updated_at
    }

    analysis_jobs ||--o{ physical_risk_scores : "produces"
    analysis_jobs {
        uuid analysis_job_id PK
        uuid site_id FK
        varchar status
        integer progress
        varchar current_node
        varchar current_hazard
        timestamptz started_at
        timestamptz completed_at
        timestamptz estimated_completion_time
        text error_message
        timestamptz created_at
    }

    physical_risk_scores {
        uuid score_id PK
        uuid analysis_job_id FK
        uuid site_id FK
        varchar hazard_type
        real hazard_score
        real exposure_score
        real vulnerability_score
        integer overall_score
        varchar risk_level
        varchar risk_calculation_method
        timestamptz analyzed_at
    }

    reports {
        uuid report_id PK
        uuid site_id FK
        varchar report_type
        varchar status
        text download_url
        bigint file_size
        varchar language
        boolean include_charts
        timestamptz created_at
        timestamptz completed_at
        timestamptz expires_at
    }

    probability_results {
        numeric latitude PK
        numeric longitude PK
        varchar risk_type PK
        real probability "AAL=Σ(P[i]×DR[i])"
        jsonb bin_data "bin별 확률/손상률"
        timestamptz calculated_at
    }

    hazard_results {
        numeric latitude PK
        numeric longitude PK
        varchar risk_type PK
        real hazard_score
        real hazard_score_100
        varchar hazard_level
        timestamptz calculated_at
    }
```

### 테이블 목록

| 테이블명 | 설명 | 주요 컬럼 | 예상 행 수 |
|---------|------|----------|-----------|
| `users` | 사용자 정보 | email, password_hash, role | ~10,000 |
| `sites` | 사업장 정보 | latitude, longitude, admin_code | ~100,000 |
| `analysis_jobs` | AI 분석 작업 추적 | status, progress, current_node | ~1,000,000 |
| `physical_risk_scores` | 물리적 리스크 점수 캐싱 | hazard_score, exposure_score, vulnerability_score | ~10,000,000 |
| `reports` | 생성된 리포트 | report_type, download_url | ~500,000 |
| `probability_results` | ModelOps 확률 결과 (AAL) | latitude, longitude, risk_type, probability (AAL), bin_data | ~5,000,000 |
| `hazard_results` | ModelOps 위험도 결과 | latitude, longitude, hazard_score, hazard_level | ~5,000,000 |

#### probability_results 테이블 상세

**probability 컬럼**: AAL (Annual Average Loss, 연간 평균 손실률)
- 공식: `AAL = Σ(P[i] × DR[i])`
  - `P[i]`: bin i의 발생확률
  - `DR[i]`: bin i의 기본 손상률
- 범위: 0.0 ~ 1.0 (0% ~ 100%)
- 예시: 0.0025 = 0.25% (연간 평균 0.25%의 손실 발생)

**bin_data 컬럼**: JSONB 형태의 bin별 상세 정보
```json
[
  {
    "bin": 1,
    "range": "0 ~ 3",
    "probability": 0.8000,
    "base_damage_rate": 0.0010
  },
  {
    "bin": 2,
    "range": "3 ~ 8",
    "probability": 0.1200,
    "base_damage_rate": 0.0030
  },
  ...
]
```

---

## Datawarehouse ERD

### 개요
- **데이터베이스명**: `skala_datawarehouse`
- **포트**: 5433
- **엔진**: PostgreSQL 16 + PostGIS 3.4
- **Extension**: postgis, postgis_raster, uuid-ossp
- **테이블 수**: 62개
- **주요 기능**: 기후 데이터, 공간 데이터, API 캐시, 래스터 데이터, 참조 데이터, 사이트 에너지 데이터

### ERD - Part 1: 위치 및 기후 메타데이터

```mermaid
erDiagram
    %% Datawarehouse - Location & Climate Metadata

    location_admin {
        serial admin_id PK
        varchar admin_code UK
        varchar admin_name
        varchar sido_code
        varchar sigungu_code
        varchar emd_code
        smallint level
        geometry geom "MULTIPOLYGON,5174"
        geometry centroid "POINT,5174"
        integer population_2020
        integer population_2050
        timestamptz created_at
    }

    location_grid {
        serial grid_id PK
        numeric longitude
        numeric latitude
        geometry geom "POINT,4326"
        timestamptz created_at
    }

    sea_level_grid {
        serial grid_id PK
        numeric longitude
        numeric latitude
        geometry geom "POINT,4326"
        timestamptz created_at
    }

    scenario {
        smallserial scenario_id PK
        varchar scenario_code UK
        varchar scenario_name
        varchar scenario_type
        text description
        numeric rcp_value
        timestamptz created_at
    }

    climate_variable {
        varchar variable_code PK
        varchar variable_name
        varchar variable_name_en
        varchar table_name
        varchar unit
        text description
        varchar time_resolution
        varchar spatial_type
        varchar risk_category
        varchar source
        timestamptz created_at
    }
```

### ERD - Part 2: 기후 데이터 테이블

```mermaid
erDiagram
    %% Datawarehouse - Climate Data Tables

    location_admin ||--o{ tamax_data : "has"
    location_admin ||--o{ tamin_data : "has"

    tamax_data {
        date time PK
        integer admin_id PK,FK
        real ssp1
        real ssp2
        real ssp3
        real ssp5
    }

    tamin_data {
        date time PK
        integer admin_id PK,FK
        real ssp1
        real ssp2
        real ssp3
        real ssp5
    }

    location_grid ||--o{ ta_data : "has"
    location_grid ||--o{ rn_data : "has"
    location_grid ||--o{ ws_data : "has"
    location_grid ||--o{ rhm_data : "has"
    location_grid ||--o{ si_data : "has"
    location_grid ||--o{ spei12_data : "has"

    ta_data {
        date observation_date PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    rn_data {
        date observation_date PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    ws_data {
        date observation_date PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    rhm_data {
        date observation_date PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    si_data {
        date observation_date PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    spei12_data {
        date observation_date PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }
```

### ERD - Part 3: 연별 기후 데이터

```mermaid
erDiagram
    %% Datawarehouse - Yearly Climate Data

    location_grid ||--o{ csdi_data : "has"
    location_grid ||--o{ wsdi_data : "has"
    location_grid ||--o{ rx1day_data : "has"
    location_grid ||--o{ rx5day_data : "has"
    location_grid ||--o{ cdd_data : "has"
    location_grid ||--o{ rain80_data : "has"
    location_grid ||--o{ sdii_data : "has"

    csdi_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    wsdi_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    rx1day_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    rx5day_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    cdd_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    rain80_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    sdii_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    location_grid ||--o{ ta_yearly_data : "has"

    ta_yearly_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }

    sea_level_grid ||--o{ sea_level_data : "has"

    sea_level_data {
        integer year PK
        integer grid_id PK,FK
        real ssp1 "SSP1-2.6"
        real ssp2 "SSP2-4.5"
        real ssp3 "SSP3-7.0"
        real ssp5 "SSP5-8.5"
    }
```

### ERD - Part 4: 래스터 데이터

```mermaid
erDiagram
    %% Datawarehouse - Raster Data

    raster_metadata ||--o{ soil_moisture_tiles : "describes"
    raster_metadata ||--o{ ndvi_tiles : "describes"

    raster_metadata {
        serial raster_id PK
        varchar data_type
        varchar file_name
        integer original_srid
        integer target_srid
        double_precision pixel_width
        double_precision pixel_height
        geometry extent "POLYGON,5174"
        integer num_bands
        double_precision nodata_value
        integer tile_size_x
        integer tile_size_y
        integer total_tiles
        timestamp upload_date
        jsonb metadata
    }

    raw_dem {
        serial rid PK
        raster rast
        text filename
    }

    raw_landcover {
        serial rid PK
        raster rast
        text filename
    }

    raw_drought {
        serial rid PK
        raster rast
        text filename
    }

    raw_ndvi {
        serial id PK
        varchar satellite_product
        varchar file_name
        date acquisition_date
        integer quality_flag
        raster raster_data
        jsonb metadata
        timestamptz loaded_at
    }

    raw_soil_moisture {
        serial id PK
        varchar data_source
        varchar file_name
        date measurement_date
        integer soil_depth_cm
        raster raster_data
        jsonb metadata
        timestamptz loaded_at
    }

    raw_coastline {
        serial id PK
        varchar region_name
        geometry geom "MULTILINESTRING,4326"
        numeric coast_length_km
        varchar erosion_risk_level
        boolean sea_level_rise_vulnerable
        varchar data_source
        date acquisition_date
        jsonb metadata
        timestamptz loaded_at
    }

    soil_moisture_tiles {
        serial tile_id PK
        integer raster_id FK
        date observation_date
        varchar satellite
        integer tile_index
        raster raster
        jsonb stats
        timestamp created_at
    }

    ndvi_tiles {
        serial tile_id PK
        integer raster_id FK
        date observation_date
        varchar satellite
        varchar product
        integer tile_index
        raster raster
        jsonb stats
        jsonb quality_flags
        timestamp created_at
    }

    coastline_data {
        serial coastline_id PK
        varchar region_code
        varchar region_name
        varchar coast_type
        geometry geometry "MULTILINESTRING,5174"
        double_precision length_km
        varchar data_source
        integer observation_year
        timestamp created_at
        jsonb metadata
    }
```

### ERD - Part 5: API 캐시 테이블 (1/2)

```mermaid
erDiagram
    %% Datawarehouse - API Cache Tables Part 1

    api_hospitals {
        serial hospital_id PK
        varchar yadm_nm
        varchar addr
        varchar clcd_nm
        varchar sidocd
        varchar sigungucd
        varchar emdongcd
        varchar post_no
        varchar tel_no
        varchar hos_url
        double_precision x_pos
        double_precision y_pos
        geography location "POINT,4326"
        timestamp cached_at
        jsonb api_response
    }

    api_buildings {
        serial building_id PK
        varchar mgm_bld_pk UK
        varchar sigungu_cd
        varchar bjdong_cd
        varchar strct_cd
        varchar strct_nm
        varchar main_purp_cd_nm
        date use_apr_day
        date pmsday
        double_precision plat_area
        double_precision arch_area
        double_precision tot_area
        integer grnd_flr_cnt
        integer ugrnd_flr_cnt
        double_precision heit
        integer hh_cnt
        timestamp cached_at
        jsonb api_response
    }

    api_firestations {
        serial firestation_id PK
        varchar sido_nm
        varchar sigungu_nm
        varchar firestation_nm
        varchar addr
        varchar tel_no
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        timestamp cached_at
        jsonb api_response
    }

    api_shelters {
        serial shelter_id PK
        integer bas_yy
        varchar regi
        integer target_popl
        double_precision accpt_rt
        integer shelt_abl_popl_smry
        integer shelt_abl_popl_gov_shelts
        integer shelt_abl_popl_pub_shelts
        integer gov_shelts_shelts
        double_precision gov_shelts_area
        integer pub_shelts_shelts
        double_precision pub_shelts_area
        timestamp cached_at
        jsonb api_response
    }

    api_watertanks {
        serial watertank_id PK
        varchar fclt_nm
        varchar ctpv_nm
        varchar sgg_nm
        varchar lctn_road_nm_addr
        varchar lctn_lotno_addr
        double_precision tpndg
        double_precision vld_pndg
        double_precision rcfv_area
        integer cmcn_yr
        varchar mng_inst_nm
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        timestamp cached_at
        jsonb api_response
    }
```

### ERD - Part 6: API 캐시 테이블 (2/2)

```mermaid
erDiagram
    %% Datawarehouse - API Cache Tables Part 2

    api_groundwater {
        serial groundwater_id PK
        varchar ctpv
        varchar sgg
        varchar se
        varchar usage_type
        integer total_plc_co
        double_precision total_utztn_qy
        timestamp cached_at
        jsonb api_response
    }

    api_coastal_infrastructure {
        serial coastal_infra_id PK
        varchar space_info_seq UK
        varchar district_nm
        varchar coastal_project_type
        varchar dept_nm
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        timestamp cached_at
        jsonb api_response
    }

    api_heating {
        serial heating_id PK
        varchar issue_date
        varchar branch_id
        varchar day_name
        integer load_01h
        integer load_02h
        integer load_12h
        integer load_24h
        timestamp cached_at
        jsonb api_response
    }

    api_wildfire {
        serial wildfire_id PK
        date analdate
        varchar doname
        varchar regioncode
        double_precision maxi
        double_precision meanavg
        double_precision d1_area
        double_precision d2_area
        double_precision d3_area
        double_precision d4_area
        integer forecast_hour
        timestamp cached_at
        jsonb api_response
    }

    api_wamis {
        serial id PK
        varchar api_type
        varchar api_endpoint
        varchar admcd
        varchar basin
        varchar obscd
        varchar year
        varchar output_format
        jsonb response_data
        timestamptz cached_at
        timestamptz expires_at
        integer http_status
        text error_message
    }

    api_typhoon {
        serial id PK
        varchar api_type
        varchar api_endpoint
        varchar year
        varchar typ
        varchar tcid
        varchar td
        varchar seq
        varchar mode
        varchar tm
        varchar grade
        jsonb response_data
        timestamptz cached_at
        timestamptz expires_at
        integer http_status
        text error_message
    }
```

### ERD - Part 7: 추가 기상 및 공간 데이터

```mermaid
erDiagram
    %% Datawarehouse - Additional Weather & Spatial Data

    wamis_water_usage {
        serial usage_id PK
        varchar admin_code
        varchar admin_name
        varchar basin_code
        varchar basin_name
        integer observation_year
        varchar water_usage_type
        double_precision usage_amount
        varchar unit
        varchar data_source
        timestamp api_call_date
        jsonb raw_data
    }

    wamis_daily_flow {
        serial flow_id PK
        varchar obs_code
        varchar obs_name
        date observation_date
        double_precision daily_flow
        double_precision max_flow
        double_precision min_flow
        double_precision avg_flow
        double_precision water_level
        varchar unit
        varchar quality_code
        varchar data_source
        timestamp api_call_date
        jsonb raw_data
    }

    typhoon_info {
        serial typhoon_info_id PK
        integer typhoon_year
        integer typhoon_number
        varchar typhoon_name_kr
        varchar typhoon_name_en
        integer sequence_number
        timestamp forecast_time
        timestamp observation_time
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        double_precision central_pressure
        double_precision max_wind_speed
        double_precision strong_wind_radius
        varchar typhoon_grade
        varchar moving_direction
        double_precision moving_speed
        varchar forecast_type
        varchar data_source
        timestamp api_call_date
        jsonb raw_data
    }

    typhoon_besttrack {
        serial besttrack_id PK
        integer typhoon_year
        varchar typhoon_id
        varchar typhoon_name
        timestamp observation_time
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        double_precision central_pressure
        double_precision max_wind_speed
        varchar grade
        double_precision moving_direction
        double_precision moving_speed
        varchar data_source
        timestamp api_call_date
        jsonb raw_data
    }

    td_info {
        serial td_info_id PK
        integer td_year
        integer td_number
        integer sequence_number
        timestamp forecast_time
        timestamp observation_time
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        double_precision central_pressure
        double_precision max_wind_speed
        varchar moving_direction
        double_precision moving_speed
        varchar forecast_type
        varchar data_source
        timestamp api_call_date
        jsonb raw_data
    }
```

### ERD - Part 8: 공간 캐시 테이블

```mermaid
erDiagram
    %% Datawarehouse - Spatial Cache Tables

    spatial_landcover {
        serial cache_id PK
        uuid site_id "Ref:App.sites"
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        integer buffer_radius
        double_precision urban_ratio
        double_precision forest_ratio
        double_precision agriculture_ratio
        double_precision water_ratio
        double_precision grassland_ratio
        double_precision wetland_ratio
        double_precision barren_ratio
        integer landcover_year
        varchar landcover_file
        integer pixel_count
        double_precision resolution
        timestamp analyzed_at
        boolean is_valid
        jsonb analysis_metadata
    }

    spatial_dem {
        serial cache_id PK
        uuid site_id "Ref:App.sites"
        double_precision latitude
        double_precision longitude
        geography location "POINT,4326"
        integer buffer_radius
        double_precision elevation_point
        double_precision elevation_mean
        double_precision elevation_min
        double_precision elevation_max
        double_precision elevation_stddev
        double_precision elevation_range
        double_precision slope_point
        double_precision slope_mean
        double_precision slope_max
        double_precision slope_stddev
        double_precision aspect_point
        varchar aspect_dominant
        varchar terrain_class
        varchar flood_risk_terrain
        varchar dem_file
        integer pixel_count
        double_precision resolution
        timestamp analyzed_at
        boolean is_valid
        jsonb analysis_metadata
    }

    api_waterroad {
        serial waterroad_id PK
        varchar water_provider_code
        varchar water_provider_name
        varchar region_code
        varchar region_name
        integer data_year
        double_precision raw_water_amount
        double_precision total_supply
        double_precision revenue_water_ratio
        double_precision non_revenue_water_ratio
        double_precision leakage_ratio
        double_precision loss_amount
        double_precision billed_amount
        double_precision volume_collection_ratio
        double_precision unmetered_ratio
        double_precision water_efficiency_score
        varchar data_source
        timestamp cached_at
        jsonb api_response
    }
```

### ERD - Part 9: 참조 데이터 (Reference Data)

```mermaid
erDiagram
    %% Datawarehouse - Reference Data Tables

    weather_stations {
        serial station_id PK
        varchar obscd UK
        varchar obsnm
        varchar bbsnnm
        varchar sbsncd
        varchar mngorg
        integer minyear
        integer maxyear
        integer basin_code
        varchar basin_name
        numeric latitude
        numeric longitude
        geometry geom "POINT,4326"
        timestamptz created_at
    }

    grid_station_mappings {
        serial mapping_id PK
        numeric grid_lat
        numeric grid_lon
        integer basin_code
        varchar basin_name
        smallint station_rank
        varchar obscd
        varchar obsnm
        numeric station_lat
        numeric station_lon
        numeric distance_km
        geometry geom "POINT,4326"
        timestamptz created_at
    }

    water_stress_rankings {
        serial ranking_id PK
        varchar gid_0
        varchar gid_1
        varchar name_0
        varchar name_1
        integer year
        varchar scenario
        varchar indicator_name
        varchar weight
        numeric score
        integer score_ranked
        smallint cat
        varchar label
        varchar un_region
        varchar wb_region
        timestamptz created_at
    }
```

### 테이블 목록 (Datawarehouse)

#### 위치 테이블 (3개)
| 테이블명 | 설명 | 주요 컬럼 | 예상 행 수 |
|---------|------|----------|-----------|
| `location_admin` | 행정구역 위치 정보 | admin_code, geom, population | 5,259 |
| `location_grid` | 격자점 위치 정보 | longitude, latitude, geom | 451,351 |
| `sea_level_grid` | 해수면 격자점 위치 | longitude, latitude, geom | 80 |

#### 기후 메타데이터 (2개)
| 테이블명 | 설명 | 주요 컬럼 | 예상 행 수 |
|---------|------|----------|-----------|
| `scenario` | SSP 기후 시나리오 | scenario_code, rcp_value | 4 |
| `climate_variable` | 기후 변수 메타데이터 | variable_code, time_resolution | 16 |

#### 기후 데이터 테이블 (15개) - **Wide Format ✨**
| 테이블명 | 설명 | 시간 해상도 | 공간 유형 | 예상 행 수 (Wide Format) | 스토리지 절감 |
|---------|------|------------|----------|------------------------|-------------|
| `tamax_data` | 일 최고기온 | Daily | Admin | ~1.84M (4 SSP 컬럼) | 75% ↓ |
| `tamin_data` | 일 최저기온 | Daily | Admin | ~1.84M (4 SSP 컬럼) | 75% ↓ |
| `ta_data` | 평균기온 | Monthly | Grid | ~433M (4 SSP 컬럼) | 75% ↓ |
| `rn_data` | 강수량 | Monthly | Grid | ~433M (4 SSP 컬럼) | 75% ↓ |
| `ws_data` | 풍속 | Monthly | Grid | ~433M (4 SSP 컬럼) | 75% ↓ |
| `rhm_data` | 상대습도 | Monthly | Grid | ~433M (4 SSP 컬럼) | 75% ↓ |
| `si_data` | 일사량 | Monthly | Grid | ~433M (4 SSP 컬럼) | 75% ↓ |
| `spei12_data` | SPEI 12개월 | Monthly | Grid | ~433M (4 SSP 컬럼) | 75% ↓ |
| `csdi_data` | 한랭야 지수 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `wsdi_data` | 온난야 지수 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `rx1day_data` | 1일 최다강수량 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `rx5day_data` | 5일 최다강수량 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `cdd_data` | 연속 무강수일 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `rain80_data` | 80mm 이상 강수일수 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `sdii_data` | 강수강도 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `ta_yearly_data` | 연평균 기온 | Yearly | Grid | ~36M (4 SSP 컬럼) | 75% ↓ |
| `sea_level_data` | 해수면 상승 | Yearly | Sea Grid | ~6,880 (4 SSP 컬럼) | 75% ↓ |

#### 래스터 데이터 (11개)
| 테이블명 | 설명 | 데이터 타입 | 예상 크기 |
|---------|------|-----------|----------|
| `raw_dem` | DEM 래스터 | RASTER | ~100 GB |
| `raw_landcover` | 토지피복 래스터 | RASTER | ~50 GB |
| `raw_drought` | 가뭄 래스터 | RASTER | ~200 GB |
| `raw_ndvi` | NDVI 래스터 | RASTER | ~100 GB |
| `raw_soil_moisture` | 토양수분 래스터 | RASTER | ~150 GB |
| `raw_coastline` | 해안선 벡터 | MULTILINESTRING | ~1 GB |
| `raster_metadata` | 래스터 메타데이터 | - | ~1,000 rows |
| `coastline_data` | 해안선 데이터 | MULTILINESTRING | ~10,000 rows |
| `soil_moisture_tiles` | 토양수분 타일 | RASTER | ~1M rows |
| `ndvi_tiles` | NDVI 타일 | RASTER | ~1M rows |

#### API 캐시 테이블 (11개)
| 테이블명 | 설명 | 데이터 출처 | 용도 |
|---------|------|-----------|------|
| `api_hospitals` | 요양기관 정보 | 국민건강보험공단 | 폭염/한파 의료접근성 |
| `api_buildings` | 건축물대장 정보 | 국토교통부 | 건물 노후도 분석 |
| `api_firestations` | 소방서 정보 | 소방청 | 화재 대응 접근성 |
| `api_shelters` | 주민대피시설 | 행정안전부 | 재난 대피 인프라 |
| `api_watertanks` | 저수지/댐 | 표준데이터 | 가뭄 수자원 가용성 |
| `api_groundwater` | 지하수 이용 현황 | 한국수자원공사 | 가뭄 지하수 의존도 |
| `api_coastal_infrastructure` | 연안정비 시설 | 해양수산부 | 태풍/해안홍수 방재 |
| `api_heating` | 난방지수 | 한국지역난방공사 | 한파 난방 인프라 |
| `api_wildfire` | 산불위험지역 | 산림청 | 산불 리스크 |
| `api_wamis` | 용수이용량/유량 | WAMIS | 홍수/가뭄 |
| `api_typhoon` | 태풍 정보 | 기상청 | 태풍 위험 |

#### 추가 기상 데이터 (5개)
| 테이블명 | 설명 | 데이터 출처 | 예상 행 수 |
|---------|------|-----------|-----------|
| `wamis_water_usage` | 용수이용량 | WAMIS | ~100,000 |
| `wamis_daily_flow` | 실시간 일유량 | WAMIS | ~10M |
| `typhoon_info` | 태풍 정보 | 기상청 | ~100,000 |
| `typhoon_besttrack` | 태풍 베스트트랙 | 기상청 | ~50,000 |
| `td_info` | 열대저기압 정보 | 기상청 | ~20,000 |

#### 공간 캐시 테이블 (3개)
| 테이블명 | 설명 | 용도 | 예상 행 수 |
|---------|------|------|-----------|
| `spatial_landcover` | 토지피복 분석 캐시 | E(노출도) 계산 | ~1M |
| `spatial_dem` | DEM 분석 캐시 | E(노출도) 계산 | ~1M |
| `api_waterroad` | 상수도 수량분석 | V(취약성) 계산 | ~10,000 |

#### 참조 데이터 테이블 (3개)
| 테이블명 | 설명 | 주요 컬럼 | 예상 행 수 |
|---------|------|----------|-----------|
| `weather_stations` | 기상 관측소 정보 | obscd, obsnm, latitude, longitude, basin_code | 1,086 |
| `grid_station_mappings` | 격자 → 최근접 관측소 매핑 | grid_lat, grid_lon, station_rank, obscd, distance_km | ~292,000 |
| `water_stress_rankings` | WRI Aqueduct 4.0 물 스트레스 순위 | gid_0, year, scenario, indicator_name, score, cat | 161,731 |

---

## 데이터베이스 간 참조

### Application → Datawarehouse 참조

**중요**: 두 데이터베이스 간 외래 키(FK)는 **존재하지 않습니다**. 애플리케이션 레벨에서 참조합니다.

| Application DB | Datawarehouse | 참조 방법 |
|---------------|---------------|----------|
| `sites.admin_code` | `location_admin.admin_code` | Application-level join |
| `sites.latitude, longitude` | `location_grid.latitude, longitude` | PostGIS spatial query |
| `analysis_jobs.site_id` | `spatial_landcover.site_id` | UUID matching |
| `analysis_jobs.site_id` | `spatial_dem.site_id` | UUID matching |

### 참조 예시 (Python)

```python
# Application DB에서 사업장 조회
site = get_site_from_application_db(site_id)
admin_code = site.admin_code  # 예: "1101010100"
latitude = site.latitude
longitude = site.longitude

# Datawarehouse에서 행정구역 정보 조회
admin_info = query_datawarehouse("""
    SELECT admin_name, population_2020, geom
    FROM location_admin
    WHERE admin_code = %s
""", (admin_code,))

# Datawarehouse에서 가장 가까운 격자점 조회
nearest_grid = query_datawarehouse("""
    SELECT grid_id, ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as distance
    FROM location_grid
    ORDER BY distance
    LIMIT 1
""", (longitude, latitude))
```

---

## 통계 요약

### Application Database
- **테이블 수**: 14개
- **총 예상 행 수**: ~21,610,000 행
- **예상 크기**: ~100 GB
- **주요 관계**: users → sites → analysis_jobs → physical_risk_scores, reports, probability_results, hazard_results

### Datawarehouse
- **테이블 수**: 62개 (기후/공간: 55개 + 참조 데이터: 3개 + 사이트 에너지: 2개 + ModelOps: 2개)
- **총 예상 행 수**: ~4,300,000,000+ 행 (43억+ 행) + 참조 데이터 ~454,000 행 + 에너지 데이터 ~20,000 행
- **예상 크기**: ~2-3 TB (래스터 포함)
- **주요 관계**:
  - location_grid → 기후 데이터 (15개 테이블)
  - location_admin → 일별 기후 데이터 (2개 테이블)
  - raster_metadata → 래스터 타일 (2개 테이블)
  - grid_station_mappings → weather_stations (참조 데이터)
  - site_dc_power_usage, site_campus_energy_usage (Application DB sites 참조)

---

## ERD 시각화 도구

이 ERD는 다음 도구로 시각화할 수 있습니다:

1. **Mermaid Live Editor**: https://mermaid.live/
2. **dbdiagram.io**: https://dbdiagram.io/
3. **DBeaver**: Database 클라이언트 도구의 ER Diagram 기능
4. **pgAdmin**: PostgreSQL 관리 도구의 ERD 기능

---

**문서 작성**: SKALA Physical Risk AI Team
**최종 수정**: 2025-11-25
**버전**: v03.0 (Wide Format 전환 - 기후 데이터 14개 테이블)
