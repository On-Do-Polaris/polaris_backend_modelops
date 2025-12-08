# SKALA Physical Risk AI - ModelOps Platform

> 기후 물리적 리스크 평가를 위한 AI 자동화 파이프라인

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

최종 수정일: 2025-12-08
버전: v1.1

---

## 📋 목차

- [개요](#개요)
- [핵심 특징](#핵심-특징)
- [프로젝트 구조](#프로젝트-구조)
- [시스템 아키텍처](#시스템-아키텍처)
- [빠른 시작](#빠른-시작)
- [ModelOps 구성요소](#modelops-구성요소)
  - [Probability (P) 계산 파이프라인](#1-probability-p-계산-파이프라인)
  - [Hazard (H) 계산 파이프라인](#2-hazard-h-계산-파이프라인)
  - [Exposure (E) & Vulnerability (V) 계산](#3-exposure-e--vulnerability-v-계산)
  - [통합 리스크 평가 API](#4-통합-리스크-평가-api)
- [ETL 파이프라인](#etl-파이프라인)
- [환경 설정](#환경-설정)
- [API 사용 가이드](#api-사용-가이드)
- [문서](#문서)

---

## 개요

SKALA Physical Risk AI ModelOps는 **기후 물리적 리스크를 자동으로 평가하는 AI 운영 플랫폼**입니다.

이 시스템은 **Hazard (H) × Exposure (E) × Vulnerability (V) = Risk** 프레임워크를 기반으로 9개 기후 리스크에 대한 종합적인 평가를 제공합니다.

### 무엇을 해결하는가?

기후 변화로 인한 물리적 리스크를 정량화하고 예측하여:
- 사업장 단위 기후 리스크 평가
- 재무 영향 추정 (손실액, 복구비용)
- TCFD 공시 지원
- 리스크 관리 의사결정 지원

### 지원 리스크 유형 (9개)

| 리스크 타입 | 영문명 | 주요 지표 |
|------------|--------|----------|
| 극한 고온 | Extreme Heat | WSDI (Warm Spell Duration Index) |
| 극한 한파 | Extreme Cold | CSDI (Cold Spell Duration Index) |
| 가뭄 | Drought | SPEI-12 (Standardized Precipitation-Evapotranspiration Index) |
| 하천 홍수 | River Flood | RX5DAY (5-day Maximum Precipitation) |
| 도시 홍수 | Urban Flood | RX1DAY (1-day Maximum Precipitation) |
| 해수면 상승 | Sea Level Rise | Sea Level Change (cm) |
| 태풍 | Typhoon | Wind Speed (m/s), Track Density |
| 산불 | Wildfire | FWI (Fire Weather Index) |
| 수자원 스트레스 | Water Stress | Water Supply-Demand Ratio |

---

## 핵심 특징

### 1. 자동화된 배치 처리
- **연간 자동 실행**: 매년 1월 1일 Hazard/Probability 자동 계산
- **병렬 처리**: ProcessPoolExecutor 기반 멀티프로세싱
- **진행률 추적**: 실시간 배치 작업 상태 모니터링

### 2. 계층적 리스크 평가

```
H (Hazard)          기후 위험도 (자동 배치 계산)
× E (Exposure)      노출도 (건물, 인구, 자산)
× V (Vulnerability) 취약성 (건물 구조, 방재시설)
= P (Probability)   발생확률 (AAL: 연간 평균 손실률)
──────────────────────────────────────────
  통합 리스크 점수 (0-100)
```

### 3. FastAPI 기반 실시간 API
- **On-Demand 계산**: 사용자 요청 시 즉시 계산
- **WebSocket 진행률**: 실시간 계산 진행 상황 제공
- **결과 캐싱**: DB 저장으로 빠른 재조회

### 4. 전처리 레이어
- 원시 기후 데이터 → 파생 지표 자동 계산
- 기준기간(2021-2040) vs 미래기간(2081-2100) 자동 분할
- 리스크별 특화 지표 생성 (FWI, ET0, Heatwave days 등)

---

## 프로젝트 구조

```
backend_aiops/
│
├── modelops/                              # 🚀 ModelOps 핵심 패키지
│   │
│   ├── agents/                            # AI 에이전트 모듈
│   │   ├── probability_calculate/         # P(H) 확률 계산 (9개 에이전트)
│   │   │   ├── base_probability_agent.py      # 기본 확률 에이전트
│   │   │   ├── extreme_heat_probability_agent.py
│   │   │   ├── extreme_cold_probability_agent.py
│   │   │   ├── drought_probability_agent.py
│   │   │   ├── river_flood_probability_agent.py
│   │   │   ├── urban_flood_probability_agent.py
│   │   │   ├── sea_level_rise_probability_agent.py
│   │   │   ├── typhoon_probability_agent.py
│   │   │   ├── wildfire_probability_agent.py
│   │   │   └── water_stress_probability_agent.py
│   │   │
│   │   ├── hazard_calculate/              # H 위험도 계산 (9개 에이전트)
│   │   │   ├── base_hazard_hscore_agent.py    # 기본 위험도 에이전트
│   │   │   └── [9개 리스크별 H-Score 에이전트]
│   │   │
│   │   └── risk_assessment/               # E, V, AAL 계산 에이전트 (신규)
│   │       ├── exposure_agent.py              # E (노출도) 계산
│   │       ├── vulnerability_agent.py         # V (취약성) 계산
│   │       ├── aal_scaling_agent.py           # AAL (손실액) 계산
│   │       └── integrated_risk_agent.py       # 통합 리스크 계산
│   │
│   ├── batch/                             # 배치 처리 모듈
│   │   ├── probability_batch.py               # P(H) 배치 (연간 자동)
│   │   ├── probability_scheduler.py           # P(H) 스케줄러
│   │   ├── hazard_batch.py                    # H 배치 (연간 자동)
│   │   ├── hazard_scheduler.py                # H 스케줄러
│   │   └── ondemand_risk_batch.py             # E×V×AAL 온디맨드 배치 (신규)
│   │
│   ├── preprocessing/                     # 전처리 레이어 (신규)
│   │   ├── climate_indicators.py              # 기후 지표 계산 (FWI, ET0 등)
│   │   ├── baseline_splitter.py               # 기준/미래 기간 분할
│   │   └── aggregators.py                     # 통계 집계 함수
│   │
│   ├── data_loaders/                      # 데이터 로더 (신규)
│   │   ├── climate_data_loader.py             # 기후 데이터 조회
│   │   ├── spatial_data_loader.py             # 공간 데이터 조회
│   │   ├── building_data_fetcher.py           # 건물 정보 조회
│   │   ├── wamis_fetcher.py                   # WAMIS API 연동
│   │   └── disaster_api_fetcher.py            # 재해 API 연동
│   │
│   ├── api/                               # FastAPI 서버 (신규)
│   │   ├── routes/
│   │   │   ├── risk_assessment.py             # 리스크 평가 API
│   │   │   └── health.py                      # 헬스체크 API
│   │   └── schemas/
│   │       └── risk_models.py                 # Pydantic 모델
│   │
│   ├── utils/                             # 유틸리티
│   │   ├── grid_mapper.py                     # 좌표 → 격자 매핑
│   │   ├── fwi_calculator.py                  # FWI 계산기
│   │   └── hazard_data_collector.py           # 위험도 데이터 수집
│   │
│   ├── database/                          # 데이터베이스 연결
│   │   └── connection.py                      # DB 커넥션 및 쿼리
│   │
│   ├── config/                            # 설정
│   │   ├── settings.py                        # 환경 설정
│   │   ├── hazard_config.py                   # 위험도 설정
│   │   └── fallback_constants.py              # 폴백 상수
│   │
│   └── triggers/                          # DB NOTIFY 리스너
│       └── notify_listener.py
│
├── ETL/                                   # 📦 데이터 로딩 파이프라인 (일회성)
│   ├── scripts/                           # 기후 데이터 로딩 스크립트
│   │   ├── load_admin_regions.py
│   │   ├── load_monthly_grid_data.py
│   │   ├── load_yearly_grid_data.py
│   │   └── load_sea_level_netcdf.py
│   ├── pyproject.toml
│   └── README.md
│
├── docs/                                  # 📚 문서
│   ├── erd.md                             # ERD 다이어그램
│   ├── modelops_implementation_summary.md # ModelOps 구현 요약
│   ├── ondemand_risk_implementation.md    # On-Demand API 구현
│   ├── API_TEST_GUIDE.md                  # API 테스트 가이드
│   └── database_operations.md             # DB 운영 가이드
│
├── tests/                                 # 테스트
│   └── [테스트 파일들]
│
├── main.py                                # ⚡ FastAPI 서버 진입점
├── pyproject.toml                         # Python 의존성 관리
├── Dockerfile                             # Docker 이미지
├── .env.example                           # 환경 변수 예시
└── README.md                              # 본 문서
```

### 주요 디렉토리 설명

| 디렉토리 | 역할 | 업데이트 주기 |
|---------|------|--------------|
| `modelops/agents/probability_calculate/` | P(H) 확률 계산 로직 | 연 1회 (1월) |
| `modelops/agents/hazard_calculate/` | H 위험도 계산 로직 | 연 1회 (1월) |
| `modelops/agents/risk_assessment/` | E, V, AAL 계산 로직 | On-Demand |
| `modelops/batch/` | 배치 스케줄러 및 프로세서 | 항시 실행 |
| `modelops/preprocessing/` | 전처리 레이어 (파생 지표) | 자동 호출 |
| `modelops/api/` | FastAPI REST/WebSocket API | 항시 실행 |
| `ETL/` | 기후 데이터 초기 로딩 | 최초 1회 |

---

## 시스템 아키텍처

### 전체 데이터 플로우

```
┌─────────────────────────────────────────────────────────────┐
│                    외부 데이터 소스                          │
│  - NetCDF 기후 데이터 (CORDEX)                              │
│  - GeoTIFF 지형/토지피복                                     │
│  - 재해 API (WAMIS, 태풍 DB)                                │
└────────────────────┬────────────────────────────────────────┘
                     │ ETL (최초 1회)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Datawarehouse (PostgreSQL + PostGIS)            │
│              포트: 5433                                      │
│  - location_grid (451,351개 격자)                           │
│  - ta_data, rn_data, wsdi_data 등 (14개 기후 테이블)        │
│  - raw_dem, raw_landcover (래스터)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ↓                         ↓
┌──────────────────┐    ┌──────────────────────┐
│  연간 배치 스케줄러  │    │  On-Demand API 요청  │
│  (매년 1월 1일)     │    │  (사용자 트리거)      │
└────────┬─────────┘    └──────────┬───────────┘
         │                         │
         ↓                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    ModelOps Engine                           │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │ Probability    │  │ Hazard         │  │ Risk          │ │
│  │ Agents (9개)   │  │ Agents (9개)   │  │ Agents (4개)  │ │
│  │                │  │                │  │               │ │
│  │ - P(H) 계산    │  │ - H 점수 계산  │  │ - E 계산      │ │
│  │ - AAL 산출     │  │ - 등급 분류    │  │ - V 계산      │ │
│  │ - Bin 확률     │  │ - 0-100 정규화 │  │ - AAL 스케일링│ │
│  │                │  │                │  │ - 통합 리스크 │ │
│  └────────────────┘  └────────────────┘  └───────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           전처리 레이어 (Preprocessing)              │  │
│  │  - 기후 지표 계산 (FWI, ET0, Heatwave days)         │  │
│  │  - 기준/미래 기간 분할                               │  │
│  │  - 통계 집계 (평균, 백분위수, 추세)                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ 결과 저장
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Application DB (PostgreSQL)                     │
│              포트: 5432                                      │
│  - probability_results (P, AAL, bin_data)                   │
│  - hazard_results (H, 등급)                                 │
│  - exposure_results (E)                                     │
│  - vulnerability_results (V)                                │
│  - aal_scaled_results (금액)                                │
│  - batch_jobs (진행률 추적)                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Server (main.py)                    │
│                  포트: 8001                                  │
│                                                              │
│  - POST /api/v1/risk-assessment/calculate                   │
│  - GET  /api/v1/risk-assessment/status/{request_id}         │
│  - WS   /api/v1/risk-assessment/ws/{request_id}             │
│  - GET  /api/v1/risk-assessment/results/{lat}/{lon}         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
              프론트엔드 / 외부 시스템
```

### 데이터베이스 구조

**Datawarehouse (5433 포트)**: 기후 원시 데이터
- `location_grid`: 451,351개 격자 (0.01° 해상도)
- `ta_data`, `rn_data` 등: 월별 기후 데이터 (433M rows)
- `wsdi_data`, `csdi_data` 등: 연별 기후 지표 (36M rows)

**Application DB (5432 포트)**: 계산 결과 및 사용자 데이터
- `probability_results`: P(H), AAL
- `hazard_results`: H, 등급
- `exposure_results`: E (노출도)
- `vulnerability_results`: V (취약성)
- `aal_scaled_results`: 금액 환산 손실액
- `batch_jobs`: 배치 진행률

---

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- PostgreSQL 16 (Application DB - 포트 5432)
- PostgreSQL 16 + PostGIS 3.4 (Datawarehouse - 포트 5433)
- 8GB+ RAM
- 100GB+ 디스크 공간

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/On-Do-Polaris/backend_aiops.git
cd backend_aiops

# 2. 가상환경 생성 및 의존성 설치 (UV 권장)
uv sync

# 또는 pip 사용
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -e .
```

### 환경 설정

`.env` 파일을 생성하고 데이터베이스 정보를 입력하세요:

```bash
# Datawarehouse (기후 데이터 - Primary)
DW_HOST=localhost
DW_PORT=5433
DW_NAME=skala_datawarehouse
DW_USER=skala_dw_user
DW_PASSWORD=your_dw_password

# Application Database (계산 결과 저장)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=skala_application
DATABASE_USER=skala_app_user
DATABASE_PASSWORD=your_app_password

# Scheduler Settings (연간 배치)
PROBABILITY_SCHEDULE_MONTH=1
PROBABILITY_SCHEDULE_DAY=1
PROBABILITY_SCHEDULE_HOUR=2
PROBABILITY_SCHEDULE_MINUTE=0

HAZARD_SCHEDULE_MONTH=1
HAZARD_SCHEDULE_DAY=1
HAZARD_SCHEDULE_HOUR=4
HAZARD_SCHEDULE_MINUTE=0

# Performance
PARALLEL_WORKERS=4
BATCH_SIZE=1000
```

### 실행 순서

#### 1단계: ETL 실행 (최초 1회 필수!)

데이터웨어하우스에 기후 데이터를 로드합니다.

```bash
cd ETL

# 전체 데이터 로드 (약 12-15시간 소요)
python scripts/load_admin_regions.py       # 행정구역
python scripts/load_monthly_grid_data.py   # 월별 기후 데이터
python scripts/load_yearly_grid_data.py    # 연별 기후 지표
python scripts/load_sea_level_netcdf.py    # 해수면 상승 데이터
```

자세한 내용은 [ETL/README.md](ETL/README.md)를 참고하세요.

#### 2단계: FastAPI 서버 실행

```bash
cd ..

# 개발 모드
python main.py

# 프로덕션 모드
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

서버가 시작되면:
- API 문서: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

---

## ModelOps 구성요소

ModelOps는 **4개의 주요 파이프라인**으로 구성됩니다:

### 1. Probability (P) 계산 파이프라인

**목적**: 리스크 발생확률 및 AAL (연간 평균 손실률) 계산

**실행 방식**:
- 연간 자동 배치 (매년 1월 1일 02:00)
- 전체 격자(451,351개) 대상

**처리 흐름**:
```
1. 기후 데이터 조회 (Datawarehouse)
   ↓
2. 전처리 레이어
   - 리스크별 파생 지표 계산
   - 기준/미래 기간 분리
   ↓
3. 9개 Probability Agent 실행
   - 강도지표 X(t) 계산
   - Bin 분류 및 확률 추정
   - AAL = Σ(P[i] × DR[i])
   ↓
4. Application DB 저장
   - probability_results 테이블
```

**에이전트 목록 및 지표**:

| 리스크 | 에이전트 클래스 | 강도지표 | Bin 분류 기준 |
|-------|---------------|----------|--------------|
| 극한 고온 | `ExtremeHeatProbabilityAgent` | WSDI | 분위수 (Q80, Q90, Q95, Q99) |
| 극한 한파 | `ExtremeColdProbabilityAgent` | CSDI | 분위수 기반 |
| 가뭄 | `DroughtProbabilityAgent` | SPEI-12 | 가뭄 등급 (-2, -1.5, -1, -0.5) |
| 하천 홍수 | `RiverFloodProbabilityAgent` | RX5DAY | 강수량 (100, 150, 200, 300mm) |
| 도시 홍수 | `UrbanFloodProbabilityAgent` | RX1DAY | 강수량 (50, 80, 120, 200mm) |
| 해수면 상승 | `SeaLevelRiseProbabilityAgent` | Sea Level (cm) | 높이 (20, 40, 60, 100cm) |
| 태풍 | `TyphoonProbabilityAgent` | Wind Speed | 등급 (17, 25, 33, 44 m/s) |
| 산불 | `WildfireProbabilityAgent` | FWI | 위험도 (low→extreme) |
| 수자원 스트레스 | `WaterStressProbabilityAgent` | 공급/수요 비율 | 스트레스 (0.8, 0.6, 0.4, 0.2) |

**결과 스키마** (`probability_results`):
```sql
latitude        NUMERIC       -- 위도
longitude       NUMERIC       -- 경도
risk_type       VARCHAR(50)   -- 리스크 타입
aal             REAL          -- AAL (연간 평균 손실률)
bin_probabilities JSONB       -- Bin별 확률
calculation_details JSONB     -- 계산 상세 정보
calculated_at   TIMESTAMPTZ   -- 계산 시각
```

### 2. Hazard (H) 계산 파이프라인

**목적**: 기후 위험도 점수 및 등급 계산

**실행 방식**:
- 연간 자동 배치 (매년 1월 1일 04:00)
- Probability 배치 2시간 후 실행

**처리 흐름**:
```
1. 기후 데이터 조회 (Datawarehouse)
   ↓
2. 전처리 레이어
   - 리스크별 특화 지표 계산
   - 통계 집계 (평균, 추세)
   ↓
3. 9개 Hazard Agent 실행
   - H-Score 계산
   - 0-100 정규화
   - 등급 분류
   ↓
4. Application DB 저장
   - hazard_results 테이블
```

**위험도 등급 분류**:
- `MINIMAL`: 0-20
- `LOW`: 20-40
- `MEDIUM`: 40-60
- `HIGH`: 60-80
- `CRITICAL`: 80-100

**결과 스키마** (`hazard_results`):
```sql
latitude        NUMERIC       -- 위도
longitude       NUMERIC       -- 경도
risk_type       VARCHAR(50)   -- 리스크 타입
hazard_score    REAL          -- 원본 점수
hazard_score_100 REAL         -- 0-100 정규화 점수
hazard_level    VARCHAR(20)   -- 등급 (MINIMAL~CRITICAL)
calculated_at   TIMESTAMPTZ   -- 계산 시각
```

### 3. Exposure (E) & Vulnerability (V) 계산

**목적**: 노출도 및 취약성 평가

**실행 방식**:
- On-Demand (사용자 API 요청 시)
- 사업장 단위 실시간 계산

**Exposure (E) - 노출도**:
- 건물 정보 (용도, 층수, 면적)
- 인구 밀도
- 자산 가치

**Vulnerability (V) - 취약성**:
- 건물 구조 (내진, 내화 등급)
- 건축 연도
- 방재 시설 유무

**에이전트**:
- `ExposureAgent`: 노출도 계산
- `VulnerabilityAgent`: 취약성 계산
- `AALScalingAgent`: AAL → 금액 환산
- `IntegratedRiskAgent`: H × E × V 통합

**결과 테이블**:
- `exposure_results`: E 점수 (0-100)
- `vulnerability_results`: V 점수 (0-100)
- `aal_scaled_results`: 예상 손실액 (원)

### 4. 통합 리스크 평가 API

**FastAPI 엔드포인트**:

```
POST /api/v1/risk-assessment/calculate
  → 리스크 계산 시작 (비동기)

GET /api/v1/risk-assessment/status/{request_id}
  → 진행률 조회 (0-100%)

WS /api/v1/risk-assessment/ws/{request_id}
  → 실시간 진행률 (WebSocket)

GET /api/v1/risk-assessment/results/{lat}/{lon}
  → 최종 결과 조회
```

**계산 흐름**:
```
0%: 배치 작업 생성
  ↓
10%: H, P(H) DB 조회
  ↓
50%: E 계산 (9개 리스크)
  ↓
80%: V 계산 (9개 리스크)
  ↓
95%: AAL 금액 환산
  ↓
100%: 통합 리스크 계산 완료
```

**최종 결과**:
```json
{
  "latitude": 37.5,
  "longitude": 127.0,
  "risks": {
    "extreme_heat": {
      "H": 75.5,
      "E": 68.2,
      "V": 45.3,
      "P": 0.0025,
      "AAL_scaled": 12500000,
      "integrated_risk": 62.8
    },
    ...
  },
  "total_risk_score": 58.4
}
```

---

## ETL 파이프라인

### 역할

**Datawarehouse에 기후 데이터를 로드하는 일회성 작업**

- 외부 NetCDF, Shapefile, GeoTIFF → PostgreSQL
- ModelOps의 **전제조건** (데이터가 없으면 작동 불가)

### 주요 스크립트

| 스크립트 | 입력 | 출력 테이블 | 시간 | 행 수 |
|---------|------|-----------|------|------|
| `load_admin_regions.py` | Shapefile | `location_admin` | 2분 | 5,259 |
| `load_monthly_grid_data.py` | NetCDF | `ta_data`, `rn_data` 등 | 3시간 | 433M/테이블 |
| `load_yearly_grid_data.py` | NetCDF | `wsdi_data`, `csdi_data` 등 | 2시간 | 36M/테이블 |
| `load_sea_level_netcdf.py` | NetCDF | `sea_level_data` | 5분 | 6,880 |
| `load_landcover.py` | GeoTIFF | `raw_landcover` (래스터) | 3시간 | ~500 GB |

### 실행

```bash
cd ETL
uv sync
python scripts/load_admin_regions.py
python scripts/load_monthly_grid_data.py
# ... (자세한 내용은 ETL/README.md 참조)
```

**상세 문서**: [ETL/README.md](ETL/README.md), [ETL/USAGE.md](ETL/USAGE.md)

---

## 환경 설정

### 환경 변수

`.env` 파일을 생성하고 필요한 변수를 설정하세요. `.env.example` 파일을 참고할 수 있습니다.

**주요 환경 변수**:

```bash
# Datawarehouse (기후 데이터 저장소)
DW_HOST=localhost
DW_PORT=5433
DW_NAME=skala_datawarehouse
DW_USER=skala_dw_user
DW_PASSWORD=your_dw_password

# Application DB (계산 결과 저장)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=skala_application
DATABASE_USER=skala_app_user
DATABASE_PASSWORD=your_app_password

# 배치 스케줄 (연간 자동 실행)
PROBABILITY_SCHEDULE_MONTH=1    # 매년 1월
PROBABILITY_SCHEDULE_DAY=1      # 1일
PROBABILITY_SCHEDULE_HOUR=2     # 02:00
PROBABILITY_SCHEDULE_MINUTE=0

HAZARD_SCHEDULE_MONTH=1
HAZARD_SCHEDULE_DAY=1
HAZARD_SCHEDULE_HOUR=4          # 04:00 (Probability 2시간 후)
HAZARD_SCHEDULE_MINUTE=0

# 성능 설정
PARALLEL_WORKERS=4              # 병렬 워커 수
BATCH_SIZE=1000                 # 배치 크기
```

---

## API 사용 가이드

### 리스크 계산 요청

**1. 계산 시작**

```bash
curl -X POST "http://localhost:8001/api/v1/risk-assessment/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 37.5665,
    "longitude": 126.9780,
    "risk_types": ["extreme_heat", "typhoon", "urban_flood"]
  }'
```

**응답**:
```json
{
  "request_id": "req_20250108_123456",
  "status": "queued",
  "message": "Risk calculation started"
}
```

**2. 진행률 조회**

```bash
curl "http://localhost:8001/api/v1/risk-assessment/status/req_20250108_123456"
```

**응답**:
```json
{
  "request_id": "req_20250108_123456",
  "status": "running",
  "progress": 45,
  "message": "Calculating vulnerability for 9 risks"
}
```

**3. WebSocket 실시간 진행률**

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/risk-assessment/ws/req_20250108_123456');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}% - ${data.message}`);
};
```

**4. 결과 조회**

```bash
curl "http://localhost:8001/api/v1/risk-assessment/results/37.5665/126.9780"
```

**응답**:
```json
{
  "latitude": 37.5665,
  "longitude": 126.9780,
  "calculated_at": "2025-01-08T12:45:00Z",
  "risks": {
    "extreme_heat": {
      "hazard_score": 75.5,
      "exposure": 68.2,
      "vulnerability": 45.3,
      "probability": 0.0025,
      "aal_scaled": 12500000,
      "integrated_risk": 62.8
    },
    "typhoon": {
      "hazard_score": 42.1,
      "exposure": 68.2,
      "vulnerability": 38.7,
      "probability": 0.0015,
      "aal_scaled": 8300000,
      "integrated_risk": 41.5
    },
    "urban_flood": {
      "hazard_score": 58.3,
      "exposure": 72.5,
      "vulnerability": 52.1,
      "probability": 0.0032,
      "aal_scaled": 18700000,
      "integrated_risk": 55.2
    }
  },
  "total_risk_score": 53.2
}
```

### Health Check

```bash
# 서버 상태 확인
curl "http://localhost:8001/health"

# 데이터베이스 연결 확인
curl "http://localhost:8001/health/db"
```

---

## 배포

### Docker 배포

```bash
# 이미지 빌드
docker build -t skala-modelops:latest .

# 컨테이너 실행
docker run -d \
  --name modelops \
  -p 8001:8001 \
  --env-file .env \
  --restart unless-stopped \
  skala-modelops:latest

# 로그 확인
docker logs -f modelops
```

### Docker Compose

```yaml
version: '3.8'

services:
  modelops:
    build: .
    container_name: modelops
    ports:
      - "8001:8001"
    env_file:
      - .env
    restart: unless-stopped
    depends_on:
      - postgres_app
      - postgres_dw
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 데이터베이스 스키마

### Application DB 테이블

#### probability_results

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `latitude` | NUMERIC | 위도 (PK) |
| `longitude` | NUMERIC | 경도 (PK) |
| `risk_type` | VARCHAR | 리스크 타입 (PK) |
| `probability` | REAL | **AAL** = Σ(P[i] × DR[i]) |
| `bin_data` | JSONB | bin별 확률/손상률 배열 |
| `calculated_at` | TIMESTAMPTZ | 계산 시각 |

**probability 컬럼**: AAL (Annual Average Loss, 연간 평균 손실률)
- 공식: `AAL = Σ(P[i] × DR[i])`
- 범위: 0.0 ~ 1.0 (0% ~ 100%)
- 예시: 0.0025 = 0.25%

#### hazard_results

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `latitude` | NUMERIC | 위도 (PK) |
| `longitude` | NUMERIC | 경도 (PK) |
| `risk_type` | VARCHAR | 리스크 타입 (PK) |
| `hazard_score` | REAL | 원본 위험도 점수 |
| `hazard_score_100` | REAL | 0-100 정규화 점수 |
| `hazard_level` | VARCHAR | 위험 등급 |
| `calculated_at` | TIMESTAMPTZ | 계산 시각 |

**hazard_level 등급**:
- `MINIMAL`: < 20
- `LOW`: 20-40
- `MEDIUM`: 40-60
- `HIGH`: 60-80
- `CRITICAL`: 80+

**상세 ERD**: [docs/ERD_Diagram.md](docs/ERD_Diagram.md)

---

## 모니터링 및 로깅

### 로그 확인

```bash
# 실시간 로그 모니터링
tail -f logs/modelops.log

# 에러 검색
grep -i "error\|failed" logs/modelops.log

# 완료 확인
grep -i "completed" logs/modelops.log
```

### 배치 진행 상황 확인

```sql
-- 계산된 격자 수 확인
SELECT
    risk_type,
    COUNT(*) AS calculated_grids,
    MAX(calculated_at) AS last_update
FROM probability_results
GROUP BY risk_type
ORDER BY risk_type;

-- Hazard Score 완료 상황
SELECT
    risk_type,
    COUNT(*) AS calculated_grids,
    AVG(hazard_score_100) AS avg_score,
    MAX(calculated_at) AS last_update
FROM hazard_results
GROUP BY risk_type
ORDER BY risk_type;
```

### 성능 모니터링

```bash
# 시스템 리소스
htop

# 데이터베이스 연결
docker exec skala_application psql -U skala_app_user -d skala_application -c "
SELECT count(*) FROM pg_stat_activity WHERE state = 'active'
"

# 데이터베이스 크기
docker exec skala_application psql -U skala_app_user -d skala_application -c "
SELECT pg_size_pretty(pg_database_size('skala_application'))
"
```

---

## 성능 최적화

### 병렬 워커 수 조정

```bash
# .env 파일에서
PARALLEL_WORKERS=8  # CPU 코어 수에 맞춰 조정
```

### 데이터베이스 튜닝

```sql
-- work_mem 증가
ALTER SYSTEM SET work_mem = '256MB';

-- maintenance_work_mem 증가
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- 재시작
SELECT pg_reload_conf();
```

### 배치 크기 조정

```python
# probability_batch.py 또는 hazard_batch.py
# ProcessPoolExecutor의 max_workers 조정
```

---

## 문제 해결

### 문제 1: 데이터베이스 연결 실패

```bash
# 증상
psycopg2.OperationalError: could not connect to server

# 해결
# 1. 데이터베이스 실행 확인
docker ps | grep skala

# 2. 연결 테스트
psql -h localhost -p 5432 -U skala_app_user -d skala_application
psql -h localhost -p 5433 -U skala_dw_user -d skala_datawarehouse

# 3. .env 파일 확인
cat .env
```

### 문제 2: ETL 데이터 없음

```bash
# 증상
ERROR: fetch_climate_data returned empty result

# 해결
# Datawarehouse에 데이터가 로드되었는지 확인
docker exec skala_datawarehouse psql -U skala_dw_user -d skala_datawarehouse -c "
SELECT COUNT(*) FROM wsdi_data;
"

# 데이터가 없으면 ETL 먼저 실행
cd ETL
python scripts/load_yearly_grid_data.py
```

### 문제 3: 메모리 부족

```bash
# 증상
MemoryError: Unable to allocate array

# 해결
# 1. 병렬 워커 수 줄이기
PARALLEL_WORKERS=2

# 2. Docker 메모리 증가
# Docker Desktop → Settings → Resources → Memory: 8GB+
```

### 문제 4: 스케줄러 작동 안 함

```python
# 로그 확인
tail -f logs/modelops.log

# 스케줄 확인
# main.py 실행 시 출력되는 스케줄 시간 확인
# Schedulers started
#   - Probability: 1/1 02:00
#   - Hazard: 1/1 04:00

# 수동 트리거로 테스트
# psql에서: NOTIFY probability;
```

---

## 개발

### 개발 환경 설정

```bash
# 개발 의존성 설치
uv sync --dev

# 또는
pip install -e ".[dev]"

# 테스트 실행
pytest

# 코드 포맷팅
black modelops/

# Linting
ruff check modelops/

# 타입 체킹
mypy modelops/
```

### 테스트

```bash
# 전체 테스트
pytest tests/

# 커버리지 포함
pytest --cov=modelops --cov-report=html

# 특정 모듈 테스트
pytest tests/test_probability_agents.py
pytest tests/test_hazard_agents.py
```

### 새로운 리스크 에이전트 추가

1. **Probability Agent 생성**:
```python
# modelops/agents/probability_calculate/new_risk_probability_agent.py
from .base_probability_agent import BaseProbabilityAgent

class NewRiskProbabilityAgent(BaseProbabilityAgent):
    def calculate_probability(self, climate_data):
        # 구현
        pass
```

2. **Hazard Agent 생성**:
```python
# modelops/agents/hazard_calculate/new_risk_hscore_agent.py
from .base_hazard_hscore_agent import BaseHazardHScoreAgent

class NewRiskHScoreAgent(BaseHazardHScoreAgent):
    def calculate_hazard_score(self, climate_data):
        # 구현
        pass
```

3. **배치 프로세서에 등록**:
```python
# modelops/batch/probability_batch.py, hazard_batch.py
agents = {
    ...
    "new_risk": NewRiskProbabilityAgent()
}
```

---

## 문서

### 📚 주요 문서

**ModelOps 관련**:
- [erd.md](docs/erd.md) - 데이터베이스 ERD 및 스키마
- [modelops_implementation_summary.md](docs/modelops_implementation_summary.md) - ModelOps 구현 요약
- [ondemand_risk_implementation.md](docs/ondemand_risk_implementation.md) - On-Demand API 구현 가이드
- [API_TEST_GUIDE.md](docs/API_TEST_GUIDE.md) - API 테스트 가이드
- [database_operations.md](docs/database_operations.md) - 데이터베이스 운영 가이드

**ETL 관련**:
- [ETL/README.md](ETL/README.md) - ETL 파이프라인 개요
- [ETL/USAGE.md](ETL/USAGE.md) - ETL 사용 가이드

**개발 가이드**:
- [commit_convention.md](docs/commit_convention.md) - 커밋 컨벤션
- [branch_convention.md](docs/branch_convention.md) - 브랜치 전략
- [repository_naming_convention.md](docs/repository_naming_convention.md) - 리포지토리 네이밍

---

## 주요 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **언어** | Python 3.11+ |
| **웹 프레임워크** | FastAPI, Uvicorn |
| **데이터베이스** | PostgreSQL 16, PostGIS 3.4 |
| **과학 컴퓨팅** | NumPy, SciPy, Pandas |
| **지리 공간** | GeoPandas, Rasterio, Shapely |
| **배치 처리** | APScheduler, ProcessPoolExecutor |
| **설정 관리** | Pydantic Settings, python-dotenv |
| **테스트** | pytest, pytest-cov |
| **컨테이너** | Docker, Docker Compose |

---

## 주요 특징 요약

✅ **자동화된 연간 배치**: Probability 및 Hazard 계산 자동 실행
✅ **On-Demand API**: 사용자 요청 시 실시간 리스크 계산
✅ **전처리 레이어**: 원시 기후 데이터 → 파생 지표 자동 변환
✅ **병렬 처리**: ProcessPoolExecutor 기반 고성능 계산
✅ **WebSocket 진행률**: 실시간 계산 진행 상황 추적
✅ **9개 리스크 지원**: 폭염, 한파, 가뭄, 홍수, 태풍, 산불, 해수면 상승, 수자원 스트레스
✅ **H × E × V 프레임워크**: 과학적 리스크 평가 방법론

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

## 지원 및 문의

**이슈 보고**: [GitHub Issues](https://github.com/On-Do-Polaris/backend_aiops/issues)
**팀 문의**: SKALA Physical Risk AI Team

---

## 프로젝트 정보

**프로젝트**: SKALA Physical Risk AI - ModelOps Platform
**버전**: v1.1
**최종 수정**: 2025-12-08
**개발**: SKALA Physical Risk AI Team
**저장소**: https://github.com/On-Do-Polaris/backend_aiops

---

**Built with ❤️ by SKALA Physical Risk AI Team**
