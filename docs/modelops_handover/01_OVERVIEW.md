# ModelOps 이관 문서 - 01. 개요

**문서 버전**: 1.0
**작성일**: 2025-12-01
**작성자**: AI Agent 팀
**대상**: ModelOps 팀

---

## 1. 이관 목적

AI Agent 시스템에서 수행 중인 **물리적 리스크 계산 로직**을 ModelOps로 이관하여:
- **관심사 분리**: AI Agent는 LLM 기반 보고서 생성, ModelOps는 데이터 계산
- **성능 최적화**: 배치 처리 및 캐싱 전략으로 응답 시간 단축
- **확장성 향상**: 계산 로직 독립적 스케일링 가능

---

## 2. 이관 범위

### 2.1 이관 대상 계산 로직

| 계산 항목 | 설명 | 입력 | 출력 | 실행 방식 |
|----------|------|------|------|----------|
| **H (Hazard)** | 기후 위험도 점수 | 기후 데이터 (CMIP6) | 0-1 점수 (9개 리스크 × 4개 SSP) | 주기적 배치 |
| **P(H) (확률)** | 강도 구간별 확률 | 기후 시계열 데이터 | Bin별 확률 분포 | 주기적 배치 |
| **V (Vulnerability)** | 취약성 점수 | 건물 정보 | 0-100 점수 (9개 리스크) | 비동기 요청 |
| **E (Exposure)** | 노출도 점수 | 자산 정보, 위치 | 0-1 점수 (9개 리스크) | 비동기 요청 |
| **AAL (Average Annual Loss)** | 연평균 재무 손실률 | H, V, 자산 정보 | 백분율 (9개 리스크 × 4개 SSP) | 비동기 요청 |

### 2.2 이관 대상 파일 (총 22개)

```
ai_agent/agents/risk_analysis/physical_risk_score/  (9개 Agent)
├── extreme_heat_score_agent.py
├── extreme_cold_score_agent.py
├── wildfire_score_agent.py
├── drought_score_agent.py
├── water_stress_score_agent.py
├── sea_level_rise_score_agent.py
├── river_flood_score_agent.py
├── urban_flood_score_agent.py
└── typhoon_score_agent.py

ai_agent/agents/risk_analysis/aal_analysis/  (9개 Agent)
├── extreme_heat_aal_agent.py
├── extreme_cold_aal_agent.py
├── wildfire_aal_agent.py
├── drought_aal_agent.py
├── water_stress_aal_agent.py
├── sea_level_rise_aal_agent.py
├── river_flood_aal_agent.py
├── urban_flood_aal_agent.py
└── typhoon_aal_agent.py

ai_agent/agents/data_processing/
└── vulnerability_analysis_agent.py  (1개)

ai_agent/services/
├── aal_calculator.py  (1개)
└── exposure_calculator.py  (1개, 참조용)
```

---

## 3. 9개 물리적 리스크 정의

| 리스크 코드 | 한국어 명칭 | 영어 명칭 | 기후 변수 |
|------------|------------|-----------|----------|
| `extreme_heat` | 극한 고온 | Extreme Heat | WSDI (Warm Spell Duration Index) |
| `extreme_cold` | 극한 한파 | Extreme Cold | CSDI (Cold Spell Duration Index) |
| `wildfire` | 산불 | Wildfire | FWI (Fire Weather Index) |
| `drought` | 가뭄 | Drought | SPEI12 (12개월 SPEI) |
| `water_stress` | 물부족 | Water Stress | WSI (Water Stress Index) |
| `sea_level_rise` | 해수면 상승 | Sea Level Rise | SLR (침수 깊이) |
| `river_flood` | 하천 홍수 | River Flood | RX1DAY (일 최대 강수량) |
| `urban_flood` | 도시 홍수 | Urban Flood | RAIN80 (80mm 이상 강수일) |
| `typhoon` | 태풍 | Typhoon | TC_EXPOSURE (태풍 노출 지수) |

---

## 4. SSP 시나리오 (4개)

| 시나리오 ID | 시나리오 명 | 설명 |
|-----------|-----------|------|
| 1 | SSP1-2.6 | 지속 가능 발전 (온도 상승 1.8℃) |
| 2 | SSP2-4.5 | 중간 경로 (온도 상승 2.7℃) |
| 3 | SSP3-7.0 | 지역 경쟁 (온도 상승 3.6℃) |
| 4 | SSP5-8.5 | 화석연료 의존 (온도 상승 4.4℃) |

---

## 5. 데이터 흐름

### 5.1 현재 (AI Agent 내부 계산)

```
SpringBoot → AI Agent
                ├─ Node 1: 기후 데이터 수집
                ├─ Node 2: V 계산 (9개 Agent)
                ├─ Node 3: AAL 계산 (9개 Agent)
                ├─ Node 3a: Physical Risk Score 계산 (9개 Agent)
                └─ Node 5-11: LLM 기반 보고서 생성
```

### 5.2 이관 후 (ModelOps 연동)

```
SpringBoot → AI Agent
                ├─ Node 1: PostgreSQL에서 H, P(H) 조회 (ModelOps 배치 결과)
                ├─ Node 2: ModelOps API 호출 (V 계산)
                ├─ Node 3: ModelOps API 호출 (AAL 계산)
                ├─ Node 3a: ModelOps API 호출 (E 계산) + (H+E+V)/3 조합
                └─ Node 5-11: LLM 기반 보고서 생성 (변경 없음)

ModelOps (신규)
    ├─ 배치 작업: H, P(H) 계산 → PostgreSQL 적재 (주기적)
    └─ API 서버: V, E, AAL 계산 (실시간 요청)
```

---

## 6. 협업 일정

| Phase | 기간 | AI Agent 팀 | ModelOps 팀 |
|-------|------|------------|------------|
| **Phase 0** | 1주 | 이관 문서 작성 | 문서 검토 및 질의 |
| **Phase 1** | 2주 | Dual Mode 구현, Mock API 테스트 | API 개발 시작 |
| **Phase 2** | 2주 | ModelOps API 연동 테스트 | API 배포, 배치 작업 구현 |
| **Phase 3** | 1주 | 내부 계산 로직 제거 | 운영 모니터링 |
| **Phase 4** | 1주 | 문서화 및 프로덕션 배포 | 성능 최적화 |

**총 기간**: 6주

---

## 7. 문서 구성

| 문서 번호 | 파일명 | 내용 |
|---------|--------|------|
| 01 | 01_OVERVIEW.md | 개요 (본 문서) |
| 02 | 02_CALCULATION_LOGIC.md | V, E, H, AAL 계산 로직 상세 명세 |
| 03 | 03_DATA_SCHEMA.md | 입출력 데이터 스키마, DB 테이블 설계 |
| 04 | 04_API_SPECIFICATION.md | API 엔드포인트 스펙 (Request/Response) |
| 05 | 05_CODE_REFERENCE.md | 기존 코드 참조 (Agent 파일 경로 및 핵심 함수) |
| 06 | 06_MIGRATION_GUIDE.md | 마이그레이션 가이드 및 협업 체크리스트 |

---

## 8. 연락처 및 협업 채널

- **AI Agent 팀 담당자**: [담당자명]
- **ModelOps 팀 담당자**: [담당자명]
- **Slack 채널**: #modelops-integration
- **주간 동기화 미팅**: 매주 목요일 14:00

---

## 다음 문서

👉 [02. 계산 로직 명세](./02_CALCULATION_LOGIC.md)
