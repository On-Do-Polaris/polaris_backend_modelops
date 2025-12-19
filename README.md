# SKALA Physical Risk AI - ModelOps Platform

> 기후 물리적 리스크 평가 및 ESG 트렌드 분석을 위한 AI 자동화 플랫폼

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/langgraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

최종 수정일: 2025-12-18
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
  - [사업장 리스크 평가 API](#5-사업장-리스크-평가-api)
  - [사업장 이전 후보지 추천 API](#6-사업장-이전-후보지-추천-api)
- [ESG Trends Agent](#esg-trends-agent)
  - [핵심 기능](#esg-agent-핵심-기능)
  - [아키텍처](#esg-agent-아키텍처)
  - [설치 및 실행](#esg-agent-설치-및-실행)
  - [API 키 발급](#esg-agent-api-키-발급)
- [ETL 파이프라인](#etl-파이프라인)
- [환경 설정](#환경-설정)
- [API 사용 가이드](#api-사용-가이드)
- [문서](#문서)

---

## 개요

SKALA Physical Risk AI ModelOps는 **기후 물리적 리스크를 자동으로 평가하고 ESG 트렌드를 분석하는 통합 AI 운영 플랫폼**입니다.

이 시스템은 **Hazard (H) × Exposure (E) × Vulnerability (V) = Risk** 프레임워크를 기반으로 9개 기후 리스크에 대한 종합적인 평가를 제공하며, LangGraph 기반 멀티 에이전트를 통해 일간 ESG 트렌드 리포트를 자동 생성합니다.

### 무엇을 해결하는가?

**기후 리스크 평가 (ModelOps)**

- 사업장 단위 기후 리스크 정량화 및 예측
- 재무 영향 추정 (손실액, 복구비용)
- TCFD 공시 지원
- 리스크 관리 의사결정 지원

**ESG 트렌드 분석 (ESG Trends Agent)**

- 날씨 및 물리적 리스크 자동 감지
- 국내외 ESG 뉴스 수집 및 필터링
- LLM 기반 인사이트 분석
- Slack 자동 배포 리포트

### 지원 리스크 유형 (9개)

| 리스크 타입     | 영문명         | 주요 지표                                                     |
| --------------- | -------------- | ------------------------------------------------------------- |
| 극한 고온       | Extreme Heat   | WSDI (Warm Spell Duration Index)                              |
| 극한 한파       | Extreme Cold   | CSDI (Cold Spell Duration Index)                              |
| 가뭄            | Drought        | SPEI-12 (Standardized Precipitation-Evapotranspiration Index) |
| 하천 홍수       | River Flood    | RX5DAY (5-day Maximum Precipitation)                          |
| 도시 홍수       | Urban Flood    | RX1DAY (1-day Maximum Precipitation)                          |
| 해수면 상승     | Sea Level Rise | Sea Level Change (cm)                                         |
| 태풍            | Typhoon        | Wind Speed (m/s), Track Density                               |
| 산불            | Wildfire       | FWI (Fire Weather Index)                                      |
| 수자원 스트레스 | Water Stress   | Water Supply-Demand Ratio                                     |

---

## 핵심 특징

### ModelOps 기후 리스크 평가

**자동화된 배치 처리**

- 연간 자동 실행 (매년 1월 1일)
- 병렬 처리 (ProcessPoolExecutor)
- 실시간 진행률 추적

**계층적 리스크 평가**

```
H (Hazard) 기후 위험도
× E (Exposure) 노출도
× V (Vulnerability) 취약성
= P (Probability) 발생확률 (AAL)
──────────────────────────────
통합 리스크 점수 (0-100)
```

**FastAPI 기반 실시간 API**

- On-Demand 계산
- WebSocket 진행률
- 결과 캐싱

### ESG Trends Agent

**데이터 수집**

- 기상청 API (날씨 + 물리적 리스크)
- ESG 뉴스 크롤링 (국내/글로벌)
- KOTRA API 연동

**LLM 분석**

- GPT-4o-mini 기반 트렌드 분석
- ESG 키워드 필터링
- 품질 검증 및 재분석

**자동 배포**

- 8개 섹션 구조화 리포트
- Slack 자동 발송
- Cron 스케줄링 (월~금 9시)

---

## 프로젝트 구조

```
backend_aiops/
│
├── modelops/                              # ModelOps 핵심 패키지
│   ├── agents/                            # AI 에이전트 모듈
│   │   ├── probability_calculate/         # P(H) 확률 계산 (9개)
│   │   │   ├── base_probability_agent.py
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
│   │   ├── hazard_calculate/              # H 위험도 계산 (9개)
│   │   │   ├── base_hazard_hscore_agent.py
│   │   │   └── [9개 리스크별 H-Score 에이전트]
│   │   │
│   │   └── risk_assessment/               # E, V, AAL 계산
│   │       ├── exposure_agent.py
│   │       ├── vulnerability_agent.py
│   │       ├── aal_scaling_agent.py
│   │       └── integrated_risk_agent.py
│   │
│   ├── batch/                             # 배치 처리
│   │   ├── probability_batch.py
│   │   ├── probability_scheduler.py
│   │   ├── hazard_batch.py
│   │   ├── hazard_scheduler.py
│   │   └── ondemand_risk_batch.py
│   │
│   ├── preprocessing/                     # 전처리 레이어
│   │   ├── climate_indicators.py
│   │   ├── baseline_splitter.py
│   │   └── aggregators.py
│   │
│   ├── data_loaders/                      # 데이터 로더
│   │   ├── climate_data_loader.py
│   │   ├── spatial_data_loader.py
│   │   ├── building_data_fetcher.py
│   │   ├── wamis_fetcher.py
│   │   └── disaster_api_fetcher.py
│   │
│   ├── api/                               # FastAPI 서버
│   │   ├── routes/
│   │   │   ├── risk_assessment.py
│   │   │   └── health.py
│   │   └── schemas/
│   │       └── risk_models.py
│   │
│   ├── utils/                             # 유틸리티
│   │   ├── grid_mapper.py
│   │   ├── fwi_calculator.py
│   │   └── hazard_data_collector.py
│   │
│   ├── database/                          # DB 연결
│   │   └── connection.py
│   │
│   ├── config/                            # 설정
│   │   ├── settings.py
│   │   ├── hazard_config.py
│   │   └── fallback_constants.py
│   │
│   └── triggers/                          # DB NOTIFY 리스너
│       └── notify_listener.py
│
├── src/                      # ESG Trends Agent
│   └── esg_trends_agent/
│       ├── graph.py                       # LangGraph Workflow
│       ├── state.py                       # State 정의
│       ├── prompts.py                     # LLM 프롬프트
│       │
│       ├── agents/                        # 에이전트 레이어
│       │   ├── orchestrator.py            # 데이터 통합
│       │   ├── supervisor.py              # LLM 분석
│       │   ├── quality_checker.py         # 품질 검증
│       │   ├── report.py                  # 리포트 생성
│       │   └── distribution.py            # Slack 발송
│       │
│       ├── collectors/                    # 수집 레이어
│       │   ├── weather.py                 # 날씨 수집
│       │   ├── esg_domestic.py            # 국내 ESG
│       │   └── esg_global.py              # 글로벌 ESG
│       │
│       ├── tools/                         # API 통합
│       │   ├── weather_api.py             # 기상청
│       │   ├── kotra_api.py               # KOTRA
│       │   ├── scraper.py                 # 크롤러
│       │   └── search.py                  # 검색
│       │
│       └── utils/                         # 유틸리티
│           ├── config.py
│           └── logging.py
│
├── scripts/                               # 실행 스크립트
│   └── run_esg_agent.py                   # ESG Agent 실행
│
├── system_setting/                        # 시스템 설정 (ESG Agent)
│   ├── make_sys.sh                        # Docker 빌드 + Cron
│   ├── run.sh                             # Docker 실행
│   └── setup_cron.sh                      # Cron 등록
│
├── ETL/                                   # 데이터 로딩
│   ├── scripts/
│   │   ├── load_admin_regions.py
│   │   ├── load_monthly_grid_data.py
│   │   ├── load_yearly_grid_data.py
│   │   └── load_sea_level_netcdf.py
│   ├── pyproject.toml
│   └── README.md
│
├── docs/                                  # 문서
├── tests/                                 # 테스트
├── logs/                                  # 로그
├── main.py                                # ⚡ FastAPI 진입점
├── pyproject.toml                         # Python 의존성
├── Dockerfile                             # Docker 이미지
├── .env                                   # 환경변수
├── .gitignore
└── README.md                              # 본 문서
```

## ModelOps 데이터 플로우

외부 데이터 소스 (NetCDF, GeoTIFF, 재해 API)
↓ ETL (최초 1회)
Datawarehouse (PostgreSQL + PostGIS, 포트 5433)
↓
ModelOps Engine

- Probability Agents (9개)
- Hazard Agents (9개)
- Risk Assessment Agents (4개)
  ↓
  Application DB (PostgreSQL, 포트 5432)
  ↓
  FastAPI Server (포트 8001)
  ↓
  프론트엔드 / 외부 시스템

## ESG Trends Agent Workflow

START
↓
Weather Collector (기상청 API)
↓
Domestic Collector (esgeconomy.com)
↓
Global Collector (KOTRA API)
↓
Orchestrator (데이터 통합)
↓
Supervisor (ESG 필터링 + LLM 분석)
↓
Quality Checker (품질 검증)
↓ (품질 미달 시 재분석)
Report Agent (8개 섹션 리포트 생성)
↓
Distribution Agent (Slack 발송)
↓
END

## 시작 가이드

사전 요구사항

- Python 3.11+
- PostgreSQL 16 (Application DB - 포트 5432)
- PostgreSQL 16 + PostGIS 3.4 (Datawarehouse - 포트 5433)
- Docker 20.10+ (선택)
- 8GB+ RAM
- 100GB+ 디스크 공간

### 설치

```
# 1. 저장소 클론
git clone https://github.com/On-Do-Polaris/polaris_backend_modelops.git
cd polaris_backend_modelops

# 2. 가상환경 생성 및 의존성 설치
uv sync

# 또는 pip 사용
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -e .
```

## 환경 설정

.env 파일 생성

```
# ModelOps - Datawarehouse (기후 데이터)
DW_HOST=localhost
DW_PORT=5433
DW_NAME=skala_datawarehouse
DW_USER=skala_dw_user
DW_PASSWORD=your_dw_password

# ModelOps - Application DB (계산 결과)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=skala_application
DATABASE_USER=skala_app_user
DATABASE_PASSWORD=your_app_password

# ModelOps - 배치 스케줄
PROBABILITY_SCHEDULE_MONTH=1
PROBABILITY_SCHEDULE_DAY=1
PROBABILITY_SCHEDULE_HOUR=2
PROBABILITY_SCHEDULE_MINUTE=0

HAZARD_SCHEDULE_MONTH=1
HAZARD_SCHEDULE_DAY=1
HAZARD_SCHEDULE_HOUR=4
HAZARD_SCHEDULE_MINUTE=0

# ModelOps - 성능
PARALLEL_WORKERS=4
BATCH_SIZE=1000

# ESG Trends Agent - APIs
KMA_API_KEY=your_kma_api_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
KOTRA_API_KEY=your_kotra_api_key          # 선택
TAVILY_API_KEY=your_tavily_api_key        # 선택

# ESG Trends Agent - Settings
WEATHER_LOCATIONS=서울,성남,대전
SLACK_CHANNEL=auto
ESG_LOG_LEVEL=INFO

# LangSmith (선택)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langsmith_api_key
```

## 실행 순서

### 1단계: ETL 실행 (ModelOps 최초 1회 필수)

```
cd ETL

전체 데이터 로드 (약 12-15시간)
python scripts/load_admin_regions.py
python scripts/load_monthly_grid_data.py
python scripts/load_yearly_grid_data.py
python scripts/load_sea_level_netcdf.py
```

### 2단계: FastAPI 서버 실행 (ModelOps)

```
cd ..

개발 모드
python main.py

프로덕션 모드
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

서버 접속:

- API 문서: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

### 3단계: ESG Trends Agent 실행

```
전체 시스템 설정 (권장)
./system_setting/make_sys.sh

Agent만 실행
./system_setting/run.sh

Cron 확인
crontab -l
tail -f logs/cron.log
```

---

## ModelOps 구성요소

### 1. Probability (P) 계산 파이프라인

**목적**: 리스크 발생확률 및 AAL (연간 평균 손실률) 계산

**실행 방식**:

- 연간 자동 배치 (매년 1월 1일 02:00)
- 전체 격자 (451,351개) 대상

**처리 흐름**:

```
기후 데이터 조회 (Datawarehouse)
↓

전처리 레이어

리스크별 파생 지표 계산

기준/미래 기간 분리
↓

9개 Probability Agent 실행

강도지표 X(t) 계산

Bin 분류 및 확률 추정

AAL = Σ(P[i] × DR[i])
↓

Application DB 저장

probability_results 테이블
```

**에이전트 목록**:

| 리스크          | 에이전트 클래스              | 강도지표       |
| --------------- | ---------------------------- | -------------- |
| 극한 고온       | ExtremeHeatProbabilityAgent  | WSDI           |
| 극한 한파       | ExtremeColdProbabilityAgent  | CSDI           |
| 가뭄            | DroughtProbabilityAgent      | SPEI-12        |
| 하천 홍수       | RiverFloodProbabilityAgent   | RX5DAY         |
| 도시 홍수       | UrbanFloodProbabilityAgent   | RX1DAY         |
| 해수면 상승     | SeaLevelRiseProbabilityAgent | Sea Level      |
| 태풍            | TyphoonProbabilityAgent      | Wind Speed     |
| 산불            | WildfireProbabilityAgent     | FWI            |
| 수자원 스트레스 | WaterStressProbabilityAgent  | 공급/수요 비율 |

### 2. Hazard (H) 계산 파이프라인

**목적**: 기후 위험도 점수 및 등급 계산

**실행 방식**:

- 연간 자동 배치 (매년 1월 1일 04:00)
- Probability 배치 2시간 후 실행

**위험도 등급**:

- MINIMAL: 0-20
- LOW: 20-40
- MEDIUM: 40-60
- HIGH: 60-80
- CRITICAL: 80-100

### 3. Exposure (E) & Vulnerability (V) 계산

**목적**: 노출도 및 취약성 평가

**실행 방식**:

- On-Demand (사용자 API 요청 시)
- 사업장 단위 실시간 계산

**Exposure (E)**:

- 건물 정보 (용도, 층수, 면적)
- 인구 밀도
- 자산 가치

**Vulnerability (V)**:

- 건물 구조 (내진, 내화 등급)
- 건축 연도
- 방재 시설 유무

### 4. 통합 리스크 평가 API

**FastAPI 엔드포인트**:

```
POST /api/v1/risk-assessment/calculate
→ 리스크 계산 시작

GET /api/v1/risk-assessment/status/{request_id}
→ 진행률 조회

WS /api/v1/risk-assessment/ws/{request_id}
→ 실시간 진행률 (WebSocket)

GET /api/v1/risk-assessment/results/{lat}/{lon}
→ 최종 결과 조회
```

### 5. 사업장 리스크 평가 API

**목적**: 여러 사업장에 대한 종합 리스크 계산 (E, V, AAL)

**FastAPI 엔드포인트**:

```
POST /api/site-assessment/calculate
→ 사업장 리스크 계산 시작 (백그라운드 처리)

GET /api/site-assessment/task-status/{task_id}
→ 작업 진행률 조회

GET /api/site-assessment/tasks
→ 모든 작업 상태 조회

DELETE /api/site-assessment/task/{task_id}
→ 작업 삭제
```

**처리 흐름**:

```
API 요청 (N개 사업장)
↓
백그라운드 작업 생성 (task_id)
↓
병렬 처리 (ThreadPoolExecutor, max_workers=8)
├─ 사업장 1 → 4개 시나리오 × 80개 연도 (2021-2100) = 320개 계산
├─ 사업장 2 → 320개 계산
└─ 사업장 N → 320개 계산
↓
각 계산마다 9개 리스크 타입 평가
├─ H (Hazard) - DB 조회
├─ E (Exposure) - 건물 정보 기반
├─ V (Vulnerability) - 건물 구조 기반
└─ AAL (Annual Average Loss) - P × DR 계산
↓
Application DB 저장 (evaal_results 테이블)
↓
진행률 실시간 업데이트
```

**병렬 처리 전략**:

- **최대 워커 수**: 8개
- **시나리오**: SSP126, SSP245, SSP370, SSP585 (4개)
- **연도 범위**: 2021-2100 (80년)
- **리스크 타입**: 9개 (극한 고온, 극한 한파, 가뭄, 하천홍수, 도시홍수, 해수면상승, 태풍, 산불, 수자원 스트레스)
- **총 계산 수**: `사업장 수 × 4 × 80 × 9`

**실시간 로깅**:

```
logs/task_[task_id]/
├── [site_id]_start.log          # 시작 로그
├── [site_id]_[year]_[scenario].log  # 연도별 완료 로그
└── [site_id]_summary.log        # 요약 로그
```

### 6. 사업장 이전 후보지 추천 API

**목적**: 사업장 이전을 위한 최적 후보지 평가 및 추천

**FastAPI 엔드포인트**:

```
POST /api/site-assessment/recommend-locations
→ 후보지 추천 작업 시작 (백그라운드 처리)

GET /api/site-assessment/task-status/{task_id}
→ 작업 진행률 조회
```

**처리 흐름**:

```
API 요청
├─ N개 사업장 정보
├─ M개 후보지 좌표 (또는 고정 10개 위치 사용)
├─ 검색 기준 (시나리오, 목표연도)
└─ 건물/자산 정보
↓
Early Callback 체크
├─ DB에 후보지 데이터 90% 이상 존재?
│   ├─ YES → 즉시 FastAPI 서버에 콜백 호출
│   └─ NO → 계산 진행
↓
병렬 처리 (ThreadPoolExecutor, max_workers=8)
├─ 사업장 1 → M개 후보지 평가
├─ 사업장 2 → M개 후보지 평가
└─ 사업장 N → M개 후보지 평가
↓
각 후보지마다
├─ 이미 DB에 존재? → 건너뛰기
├─ E, V, AAL 온디맨드 계산
├─ 통합 리스크 점수 계산 (H × E × V / 10000)
└─ candidate_sites 테이블에 저장
    ├─ latitude, longitude
    ├─ risk_score (0-100)
    ├─ total_aal
    ├─ aal_by_risk (9개 리스크별)
    └─ risks (9개 리스크별 점수)
↓
계산 완료 후 콜백 호출 (Early Callback 미호출 시)
↓
FastAPI 서버에 완료 알림
```

**병렬 처리 전략**:

- **최대 워커 수**: 8개
- **후보지 수**: 사용자 제공 또는 고정 10개 위치
- **시나리오**: 단일 (기본 SSP245)
- **목표연도**: 단일 (기본 2040)
- **리스크 타입**: 9개
- **총 계산 수**: `사업장 수 × 후보지 수 × 9`

**Early Callback 최적화**:

- DB에 후보지 데이터가 90% 이상 존재하면 즉시 콜백 호출
- 불필요한 재계산 방지
- 프론트엔드 응답 시간 단축

**고정 후보지 위치** (LOCATION_MAP):

```python
# 10개 고정 후보지 좌표
[
  {"lat": 37.5665, "lng": 126.9780},  # 서울
  {"lat": 35.1796, "lng": 129.0756},  # 부산
  # ... 총 10개
]
```

---

## ESG Trends Agent

### ESG Agent 핵심 기능

**데이터 수집**

- 기상청 단기예보 API (지역별 실시간 날씨)
- 9대 물리적 리스크 자동 감지
- esgeconomy.com 웹 크롤링 (국내 ESG)
- KOTRA ESG 동향뉴스 API (글로벌 ESG)
- Fallback: Tavily/DuckDuckGo 검색

**LLM 분석**

- ESG 키워드 필터링 (E, S, G 카테고리)
- GPT-4o-mini 기반 트렌드 분석
- 급변 이슈 탐지 및 권고사항 생성
- 데이터 품질 검증 (최대 2회 재시도)

**리포트 생성**

- 8개 섹션 구조화 리포트
- Slack 자동 발송 (페이지네이션)
- 마크다운 형식 메시지

### 9대 물리적 리스크

| 리스크      | 감지 조건                                        |
| ----------- | ------------------------------------------------ |
| 극심한 고온 | 기온 33°C 이상                                   |
| 극심한 한파 | 기온 -12°C 이하                                  |
| 해안 홍수   | 해안 지역 침수 위험                              |
| 도시 홍수   | 강수확률 80% 이상 + 강수량 30mm 이상             |
| 가뭄        | 장기 건조 조건                                   |
| 물 부족     | 수자원 고갈 위험                                 |
| 해수면 상승 | 장기적 해안 위험                                 |
| 태풍        | 강풍 + 폭풍 피해                                 |
| 산불        | 기온 30°C 이상 + 습도 30% 이하 + 풍속 10m/s 이상 |

### ESG 필터링 키워드

**환경(E)**: 환경, 탄소, 기후, 친환경, 재생에너지, 태양광, 풍력, 전기차, EV, 탈탄소, 넷제로, 온실가스, 배출, CBAM, 탄소국경, RE100, 그린

**사회(S)**: 사회, 인권, 노동, 안전, 보건, 다양성, 포용, 공급망, 협력사

**지배구조(G)**: 지배구조, 이사회, 주주, 투명성, 공시, 윤리, 반부패, 컴플라이언스

**일반 ESG**: ESG, 지속가능경영, 사회적책임, CSR, CSV, 임팩트, 스튜어드십

### ESG Agent API 키 발급

**기상청 API (필수)**

1. [공공데이터포털](https://www.data.go.kr/data/15084084/openapi.do) 접속
2. 활용신청 후 일반 인증키(Decoding) 복사
3. `.env`에 `KMA_API_KEY` 추가

**OpenAI API (필수)**

1. [OpenAI Platform](https://platform.openai.com/) 회원가입
2. API Keys 메뉴에서 새 키 생성
3. `.env`에 `OPENAI_API_KEY` 추가

**Slack Bot Token (필수)**

1. [Slack API](https://api.slack.com/apps) 접속
2. "Create New App" → "From scratch" 선택
3. OAuth & Permissions에서 권한 추가:
   - `channels:read`, `chat:write`, `files:write`, `groups:read`
4. Install to Workspace 클릭
5. Bot User OAuth Token 복사
6. `.env`에 `SLACK_BOT_TOKEN` 추가
7. 채널에 Bot 초대: `/invite @봇이름`

**KOTRA API (선택)**

1. [공공데이터포털](https://www.data.go.kr/data/15146894/openapi.do) 접속
2. 활용신청 후 일반 인증키(Decoding) 복사
3. `.env`에 `KOTRA_API_KEY` 추가
4. 미설정 시 검색 API로 대체

**Tavily Search API (선택)**

1. [Tavily](https://tavily.com/) 회원가입
2. API Key 발급
3. `.env`에 `TAVILY_API_KEY` 추가
4. 미설정 시 DuckDuckGo로 대체

---

## ETL 파이프라인

### 역할

Datawarehouse에 기후 데이터를 로드하는 일회성 작업

### 주요 스크립트

| 스크립트                  | 입력      | 출력 테이블             | 시간  | 행 수       |
| ------------------------- | --------- | ----------------------- | ----- | ----------- |
| load_admin_regions.py     | Shapefile | location_admin          | 2분   | 5,259       |
| load_monthly_grid_data.py | NetCDF    | ta_data, rn_data 등     | 3시간 | 433M/테이블 |
| load_yearly_grid_data.py  | NetCDF    | wsdi_data, csdi_data 등 | 2시간 | 36M/테이블  |
| load_sea_level_netcdf.py  | NetCDF    | sea_level_data          | 5분   | 6,880       |

### 실행

```
cd ETL
uv sync
python scripts/load_admin_regions.py
python scripts/load_monthly_grid_data.py
python scripts/load_yearly_grid_data.py
python scripts/load_sea_level_netcdf.py

```

---

## API 사용 가이드

### ModelOps 리스크 계산

**1. 계산 시작**

```
curl -X POST "http://localhost:8001/api/v1/risk-assessment/calculate"
-H "Content-Type: application/json"
-d '{
"latitude": 37.5665,
"longitude": 126.9780,
"risk_types": ["extreme_heat", "typhoon", "urban_flood"]
}'
```

**응답**:

```
{
"request_id": "req_20250108_123456",
"status": "queued",
"message": "Risk calculation started"
}
```

**2. 진행률 조회**

```
curl "http://localhost:8001/api/v1/risk-assessment/status/req_20250108_123456"
```

**3. 결과 조회**

```
curl "http://localhost:8001/api/v1/risk-assessment/results/37.5665/126.9780"
```

---

## 문서

**ModelOps 관련**:

- [erd.md](docs/erd.md) - 데이터베이스 ERD
- [modelops_implementation_summary.md](docs/modelops_implementation_summary.md) - ModelOps 구현 요약
- [ondemand_risk_implementation.md](docs/ondemand_risk_implementation.md) - On-Demand API
- [API_TEST_GUIDE.md](docs/API_TEST_GUIDE.md) - API 테스트
- [database_operations.md](docs/database_operations.md) - DB 운영

**ETL 관련**:

- [ETL/README.md](ETL/README.md) - ETL 파이프라인
- [ETL/USAGE.md](ETL/USAGE.md) - ETL 사용법

---

## 주요 기술 스택

| 카테고리          | 기술                                     |
| ----------------- | ---------------------------------------- |
| **언어**          | Python 3.11+                             |
| **웹 프레임워크** | FastAPI, Uvicorn                         |
| **AI/LLM**        | LangGraph, LangChain, OpenAI GPT-4o-mini |
| **데이터베이스**  | PostgreSQL 16, PostGIS 3.4               |
| **과학 컴퓨팅**   | NumPy, SciPy, Pandas, GeoPandas          |
| **지리 공간**     | Rasterio, Shapely                        |
| **웹 스크래핑**   | BeautifulSoup4, lxml                     |
| **배치 처리**     | APScheduler, ProcessPoolExecutor, Cron   |
| **메시징**        | Slack SDK                                |
| **컨테이너**      | Docker, Docker Compose                   |
| **패키지 관리**   | uv                                       |

---

## 라이선스

MIT License

---

## 프로젝트 정보

**프로젝트**: SKALA Physical Risk AI - ModelOps & ESG Trends Platform  
**버전**: v1.1  
**최종 수정**: 2025-12-18  
**팀**: SKALA Physical Risk AI Team  
**저장소**: https://github.com/On-Do-Polaris/polaris_backend_modelops

---

**Built with ❤️ by SKALA Physical Risk AI Team**
