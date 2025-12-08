# 현재 데이터 연동 상태 및 Fallback 동작 현황

최종 테스트 실행(`test_risk_comparison.py`) 결과를 바탕으로, 현재 실제 데이터를 사용하지 못하고 Fallback 로직이 동작하는 부분들을 정리합니다.

## 1. API 통신 실패로 인한 Fallback

외부 API 서버와의 통신 문제로 인해, 코드에 내장된 통계 기반 기본값이 사용된 경우입니다.

-   **건축물대장 API**
    -   **로그:** `requests.exceptions.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
    -   **원인:** API 서버가 유효한 JSON 응답을 반환하지 않았습니다. (API 키 오류, 서버 점검, 네트워크 문제 등)
    -   **결과:** 건물 정보(층수, 용도 등)를 가져오지 못하고, **국토교통부 통계 기반의 기본값**으로 분석이 수행되었습니다.
    -   **해결 제안:** `.env` 파일에 유효한 `BUILDING_API_KEY`가 설정되었는지 확인합니다.

-   **V-World 하천 정보 API**
    -   **로그:** `[TCFD 경고] 하천 정보 조회 실패: Expecting value: line 1 column 1 (char 0)`
    -   **원인:** API 서버가 유효한 JSON 응답을 반환하지 않았습니다.
    -   **결과:** V-World를 통한 하천 정보 조회에 실패했습니다. (단, 다른 API를 통해 '예덕천' 정보를 가져와 일부 분석은 수행됨)
    -   **해결 제안:** `.env` 파일에 유효한 `VWORLD_API_KEY`가 설정되었는지 확인합니다.

## 2. 로컬 데이터/라이브러리 부재로 인한 Fallback

로컬 환경의 문제로 인해 실제 데이터를 사용하지 못한 경우입니다.

-   **토양 수분 (Soil Moisture)**
    -   **로그:** `UserWarning: ease-lonlat not available`
    -   **원인:** 토양 수분 데이터 처리에 필요한 `ease-lonlat` 라이브러리가 `uv` 가상환경에 설치되지 않았습니다.
    -   **결과:** 토양 수분 데이터 조회에 실패하고 **기본값(0.2)으로 대체**되었습니다.
    -   **해결 제안:** `uv pip install ease-lonlat` 명령어로 라이브러리를 설치합니다.

-   **DEM 기반 하천 차수 (Stream Order)**
    -   **로그:** `하천 차수 추출 실패: DEM 파일이 없음`
    -   **원인:** `stream_order_simple.py` 모듈 내부의 경로 설정이 리팩토링된 `src` 구조를 반영하지 못하여 DEM 파일들을 찾지 못하고 있습니다.
    -   **결과:** DEM 분석 기반의 정확한 하천 차수 대신 **통계 기반의 기본값(1차 하천)**이 사용되었습니다.
    -   **해결 제안:** `stream_order_simple.py` 파일 내부의 데이터 경로를 수정해야 합니다.

-   **기후 시나리오 데이터 (SPEI)**
    -   **로그:** `월별 파일 없음: SSP126_SPEI12_gridraw_monthly_2021-2100.nc`
    -   **원인:** `Physical_RISK_calculate/data/KMA/gridraw/SSP126/monthly/` 폴더에 해당 기후 데이터 파일이 없습니다.
    -   **결과:** 가뭄(Drought) 계산 시 `SPEI` 지수 대신, 하드코딩된 전국 평균 통계를 사용하는 **SPI 기반 Fallback 로직**이 동작했습니다.
    -   **해결 제안:** 기상청 API를 통해 필요한 NetCDF(.nc) 파일들을 다운로드하여 정확한 경로에 위치시켜야 합니다.

---

## 요약 및 권장 조치

현재 코드의 로직과 구조는 정상적으로 동작하지만, 실제 분석을 위해서는 위 문제들을 해결해야 합니다.

1.  `.env` 파일에 올바른 API 키 3개를 설정합니다.
2.  `uv pip install ease-lonlat` 명령어로 누락된 라이브러리를 설치합니다.
3.  `stream_order_simple.py`의 파일 경로를 수정합니다.
4.  필요한 모든 `.nc` 기후 데이터 파일이 `data` 폴더 내 올바른 위치에 있는지 확인합니다.
