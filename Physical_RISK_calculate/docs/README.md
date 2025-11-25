# Physical Risk Calculate - 문서 센터

SK AX 기후리스크 분석 프로젝트의 종합 문서 저장소입니다.

## 📚 문서 구조

```
docs/
├── 01_project_overview/      # 프로젝트 개요
├── 02_data_models/            # 데이터 모델 (DBML)
├── 03_api_documentation/      # API 문서
│   ├── guides/                # API 가이드
│   ├── references/            # 참고 자료
│   └── tests/                 # 테스트 스크립트
├── 04_risk_analysis/          # 리스크 분석
│   ├── methodology/           # 분석 방법론
│   ├── hazard_types/          # 재해 유형별
│   └── legacy/                # 이전 버전
├── 05_data_management/        # 데이터 관리
└── archive/                   # 보관 파일
```

## 🚀 빠른 시작

### 1️⃣ 프로젝트 이해하기

- [프로젝트 개요](01_project_overview/) - 전체 프로젝트 구조와 ERD 이해
- [데이터 모델](02_data_models/) - 데이터베이스 스키마 확인

### 2️⃣ API 연동하기

- [API 문서](03_api_documentation/) - 외부 API 연동 가이드
- [API 테스트](03_api_documentation/tests/) - 테스트 스크립트 실행

### 3️⃣ 리스크 분석하기

- [분석 방법론](04_risk_analysis/methodology/) - SSP 시나리오 및 재해 시나리오
- [재해 유형별 분석](04_risk_analysis/hazard_types/) - 9가지 재해 유형 분석 방법

### 4️⃣ 데이터 관리하기

- [데이터 관리](05_data_management/) - 로컬 데이터 저장 및 검증

## 🌍 주요 재해 유형

프로젝트에서 다루는 9가지 물리적 리스크:

| 재해 유형          | 문서                                                                         |
| ------------------ | ---------------------------------------------------------------------------- |
| 🌊 해안 홍수       | [coastal_flood_risk.md](04_risk_analysis/hazard_types/coastal_flood_risk.md) |
| 💧 내륙 홍수       | [inland_flood_risk.md](04_risk_analysis/hazard_types/inland_flood_risk.md)   |
| 🏙️ 도시 홍수       | [urban_flood_risk.md](04_risk_analysis/hazard_types/urban_flood_risk.md)     |
| ☀️ 가뭄            | [drought_risk.md](04_risk_analysis/hazard_types/drought_risk.md)             |
| 💦 수자원 스트레스 | [water_stress_risk.md](04_risk_analysis/hazard_types/water_stress_risk.md)   |
| 🔥 극한 고온       | [extreme_heat.md](04_risk_analysis/hazard_types/extreme_heat.md)             |
| ❄️ 극한 저온       | [extreme_cold_risk.md](04_risk_analysis/hazard_types/extreme_cold_risk.md)   |
| 🌀 태풍            | [typhoon_risk.md](04_risk_analysis/hazard_types/typhoon_risk.md)             |
| 🔥 산불            | [wildfire_risk.md](04_risk_analysis/hazard_types/wildfire_risk.md)           |

## 🔧 주요 도구 및 API

### 공공데이터 API

- 공공데이터포털
- 재난안전데이터공유플랫폼
- 기상청 API

### 지도/공간 정보

- VWorld
- WMS
- SGIS

### 데이터 모델링

- DBML (Database Markup Language)
- dbdiagram.io

## 📖 추가 리소스

- [ERD 최종 가이드](01_project_overview/ERD_Final_Guide.md)
- [SSP 시나리오](04_risk_analysis/methodology/SSP_scenario_api.md)
- [API 키 관리](03_api_documentation/guides/api_key.md)

## 🤝 기여 가이드

문서 작성 시:

1. 각 폴더별 README.md를 먼저 확인
2. 일관된 마크다운 포맷 사용
3. 관련 문서 간 링크 유지

---

**Last Updated**: 2025-01-24
**Project**: SK AX 기후리스크 분석
