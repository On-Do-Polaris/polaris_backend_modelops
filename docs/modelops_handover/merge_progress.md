# Merge Progress Tracking

## Status Definitions
- ⬜ **Pending:** 작업 대기 중
- 🔄 **In Progress:** 작업 진행 중
- ✅ **Completed:** 작업 완료

## 1. Foundation & Utilities
- [x] ✅ **Data Modules Migration**: `physical_risk_module_core_merge`의 데이터 로더/페처 파일들을 `modelops/data_loaders` (신규 생성)로 이동 및 패키지 구조 정리.
- [x] ✅ **Dependency Setup**: 
    - `pyproject.toml`에 `requests`, `geopy`, `netCDF4`, `rasterio`, `h5py`, `geopandas`, `xmltodict` 등 필수 라이브러리 추가 완료.
    - `uv` 가상환경 설정 및 패키지 설치 완료.
- [x] ✅ **`HazardDataCollector` Implementation**: `modelops/utils/hazard_data_collector.py` 작성 완료. 외부 API 및 데이터 로더 연결.

## 2. Hazard Agents Migration (H)
각 에이전트에 대해 `HazardCalculator`의 고도화된 로직(HCI, TWI, FWI, SPEI 등) 이식 완료.

- [x] ✅ **Extreme Heat**: `extreme_heat_hscore_agent.py` (HCI 기반)
- [x] ✅ **Extreme Cold**: `extreme_cold_hscore_agent.py` (CCI 기반)
- [x] ✅ **Drought**: `drought_hscore_agent.py` (SPEI-12 기반)
- [x] ✅ **River Flood**: `river_flood_hscore_agent.py` (TWI + 강수량)
- [x] ✅ **Urban Flood**: `urban_flood_hscore_agent.py` (배수능력 + 강수초과)
- [x] ✅ **Sea Level Rise**: `sea_level_rise_hscore_agent.py` (SSP 시나리오)
- [x] ✅ **Typhoon**: `typhoon_hscore_agent.py` (TCI 기반)
- [x] ✅ **Wildfire**: `wildfire_hscore_agent.py` (Canadian FWI)
- [x] ✅ **Water Stress**: `water_stress_hscore_agent.py` (수급지수)

## 3. Exposure & Vulnerability Migration (E/V)
`ExposureCalculator`와 `VulnerabilityCalculator` 로직을 각 에이전트로 이식.

- [x] ✅ **Exposure Agent**: `modelops/agents/risk_assessment/exposure_agent.py` 업데이트 완료. `HazardDataCollector` 연동.
- [x] ✅ **Vulnerability Agent**: `modelops/agents/risk_assessment/vulnerability_agent.py` 업데이트 완료. `ExposureAgent` 결과 기반 계산.

## 4. Integration & Verification
- [x] ✅ **Hazard Integration Test**: `tests/modelops/test_hazard_integration.py` 작성 및 실행 완료. 실제 데이터 수집 및 에이전트 계산 검증 성공.
- [x] ✅ **E/V Integration Test**: `tests/modelops/test_ev_integration.py` 작성 및 실행 완료. 노출도 및 취약성 계산 흐름 검증 성공.
- [ ] ⬜ **DB Transition**: `Data Fetcher`들을 API/File 직접 접근 방식에서 DB Query 방식으로 리팩토링 (ETL 구축 후 진행).
- [ ] ⬜ **System Entry Point**: `main.py` 또는 API 라우터에서 `HazardDataCollector`와 Agent를 연동하여 서비스 엔드포인트 구현.