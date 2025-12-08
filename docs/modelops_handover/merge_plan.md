# Physical Risk Module Core Merge Plan

## 1. 개요 (Overview)
본 문서는 `physical_risk_module_core_merge`에서 개발된 고도화된 위험 계산 로직(`HazardCalculator`, `ExposureCalculator`, `VulnerabilityCalculator`)을 현재 시스템의 `modelops` 아키텍처로 통합하기 위한 계획을 정의합니다.

**목표:**
* 단일 클래스에 집중된 계산 로직을 개별 에이전트(`*Agent`)로 분산하여 모듈화 및 유지보수성 향상.
* TCFD 및 IPCC AR6 기반의 과학적 방법론이 적용된 최신 로직을 시스템에 반영.
* 데이터 수집(`DataCollector`)과 계산 로직(`Agent`)의 명확한 분리.
* 최종적으로 파일/API 기반 데이터 접근 방식을 PostgreSQL DB 기반으로 전환.

## 2. 아키텍처 변경 (Architecture Transition)

### AS-IS (Source)
* **구조:** `HazardCalculator`, `ExposureCalculator`, `VulnerabilityCalculator` (Monolithic Classes)
* **특징:**
    * 계산 로직과 데이터 접근 로직이 강하게 결합됨.
    * 외부 API 및 로컬 파일 시스템에 직접 접근.

### TO-BE (Target)
* **구조:** Agent-based Pattern
* **특징:**
    * **Agents:** `HazardHScoreAgent`, `ExposureAgent`, `VulnerabilityAgent`가 각자의 계산 로직 담당.
    * **Utility:** `HazardDataCollector`가 필요한 모든 데이터를 수집하여 정규화된 형태(`collected_data`)로 에이전트에 주입.
    * **Data Source:** 초기에는 API/File 직접 접근 방식을 유지하되, 점진적으로 DB Query 방식으로 전환.

## 3. 주요 구성 요소 (Key Components)

### 3.1. HazardDataCollector (`modelops/utils/hazard_data_collector.py`)
* **역할:** 데이터 수집 및 전처리 전담.
* **기능:** `lat`, `lon`, `risk_type`에 따라 API, 파일, 또는 DB에서 데이터를 조회하여 통합.

### 3.2. Agents
* **Hazard (H):** 9개 리스크별 `*HScoreAgent` (완료)
* **Exposure (E):** `ExposureAgent` (예정)
* **Vulnerability (V):** `VulnerabilityAgent` (예정)

## 4. 상세 이행 단계 (Migration Steps)

### Phase 1: 기반 마련 (Foundation) - ✅ Completed
* 데이터 로더 모듈(`src/data`) 이관 및 `HazardDataCollector` 구현.
* 의존성 라이브러리(`requests`, `netCDF4` 등) `pyproject.toml`에 추가.

### Phase 2: Hazard Agent 구현 (Hazard Implementation) - ✅ Completed
* 9개 리스크 유형별 `HScoreAgent` 로직 이식 완료.
* 통합 테스트(`test_hazard_integration.py`)를 통해 데이터 수집부터 점수 산출까지 검증 완료.

### Phase 3: Exposure & Vulnerability 구현 (E/V Implementation) - ⬜ Pending
1. **Exposure Agent:**
    * `physical_risk_module_core_merge/.../exposure_calculator.py` 분석.
    * `modelops/agents/risk_assessment/exposure_agent.py`로 로직 이식.
    * 자산 가치 정규화 및 근접도 계산 로직 고도화.
2. **Vulnerability Agent:**
    * `physical_risk_module_core_merge/.../vulnerability_calculator.py` 분석.
    * `modelops/agents/risk_assessment/vulnerability_agent.py`로 로직 이식.
    * 9개 리스크별 취약성 함수 통합.

### Phase 4: DB 전환 전략 (DB Transition Strategy) - ⬜ Pending
현재의 API/File 직접 접근 방식을 운영 환경에 맞는 DB 기반으로 전환.
1. **ETL 파이프라인 구축:**
    * API 데이터(건물, 재난이력 등)를 주기적으로 수집하여 PostgreSQL에 적재.
    * 대용량 파일(NetCDF, GeoTIFF)의 메타데이터 또는 통계치를 DB화.
2. **Data Loader 수정:**
    * `BuildingDataFetcher`, `DisasterAPIFetcher` 등이 외부 API 대신 DB(`modelops.database`)를 쿼리하도록 변경.
    * `HazardDataCollector`는 변경 사항 없이 `fetcher`들의 내부 구현만 교체하여 인터페이스 유지.

## 5. 데이터 매핑 전략
`HazardDataCollector`가 생성하는 `collected_data` 구조 예시:
```python
{
    "latitude": 37.5,
    "longitude": 127.0,
    "climate_data": { ... },  # 기후 데이터
    "spatial_data": { ... },  # 공간 데이터
    "building_data": { ... }, # 건물 데이터
    "disaster_data": { ... }, # 재난 이력
    # ...
}
```
각 에이전트는 위 구조에서 필요한 키를 조회하여 계산 수행.