# ModelOps 이관 문서 - 06. 마이그레이션 가이드

**문서 버전**: 1.0
**작성일**: 2025-12-01

---

## 1. 마이그레이션 개요

### 1.1 목표
- AI Agent의 계산 로직을 ModelOps로 안전하게 이관
- 서비스 중단 없이 점진적 전환
- 성능 및 품질 검증 후 최종 전환

### 1.2 전체 일정
| Phase | 기간 | 주요 작업 |
|-------|------|----------|
| Phase 0 | 1주 | 문서 검토 및 질의응답 |
| Phase 1 | 2주 | Dual Mode 구현 |
| Phase 2 | 2주 | ModelOps 연동 테스트 |
| Phase 3 | 1주 | 내부 로직 제거 |
| Phase 4 | 1주 | 문서화 및 배포 |

**총 기간**: 6주

---

## 2. Phase 0: 문서 검토 (1주)

### 2.1 AI Agent 팀 작업
- [x] 이관 문서 6개 작성 완료
- [ ] ModelOps 팀에 문서 전달
- [ ] Kick-off 미팅 일정 조율

### 2.2 ModelOps 팀 작업
- [ ] 이관 문서 검토 (01~05)
- [ ] 계산 로직 명세 검증 (02_CALCULATION_LOGIC.md)
- [ ] API 스펙 검토 (04_API_SPECIFICATION.md)
- [ ] 질문 사항 정리

### 2.3 공동 작업
- [ ] Kick-off 미팅 (1시간)
  - 이관 범위 확인
  - 일정 및 마일스톤 합의
  - 협업 채널 및 담당자 지정
- [ ] 질의응답 세션 (1-2회)

### 2.4 완료 기준
- [ ] ModelOps 팀이 모든 문서 검토 완료
- [ ] 질문 사항 모두 해소
- [ ] API 스펙 합의
- [ ] DB 스키마 합의

---

## 3. Phase 1: Dual Mode 구현 (2주)

### 3.1 AI Agent 팀 작업

#### Week 1: ModelOps 연동 준비

**3.1.1 환경 설정**
- [ ] `.env` 파일에 ModelOps 설정 추가
```bash
# ModelOps 설정
MODELOPS_ENABLED=false  # Phase 1: false
MODELOPS_API_URL=http://localhost:8001
MODELOPS_API_KEY=test-api-key
USE_INTERNAL_CALCULATION=true  # Dual Mode 활성화
```

- [ ] `ai_agent/config/settings.py` 업데이트
```python
class Config:
    # ModelOps 연동 설정
    MODELOPS_ENABLED = os.getenv('MODELOPS_ENABLED', 'False').lower() == 'true'
    MODELOPS_API_URL = os.getenv('MODELOPS_API_URL', 'http://localhost:8001')
    MODELOPS_API_KEY = os.getenv('MODELOPS_API_KEY', '')
    USE_INTERNAL_CALCULATION = os.getenv('USE_INTERNAL_CALCULATION', 'True').lower() == 'true'
```

**3.1.2 ModelOps 클라이언트 구현**
- [ ] `ai_agent/services/modelops/` 폴더 생성
- [ ] `modelops_client.py` 작성
```python
class ModelOpsClient:
    async def calculate_vulnerability(self, building_info, location):
        """V Score API 호출"""

    async def calculate_exposure(self, asset_info, location):
        """E Score API 호출"""

    async def calculate_aal(self, request_data):
        """AAL API 호출"""
```

- [ ] `schemas.py` 작성 (Pydantic 스키마)
- [ ] `cache_manager.py` 작성
- [ ] 단위 테스트 작성

**3.1.3 Dual Mode 로직 구현**
- [ ] `ai_agent/workflow/nodes.py` 수정
```python
def vulnerability_analysis_node(state, config):
    if config.USE_INTERNAL_CALCULATION:
        # 기존 로직 (VulnerabilityAnalysisAgent)
        agent = VulnerabilityAnalysisAgent()
        result = agent.calculate_vulnerability(exposure)
    else:
        # ModelOps API 호출
        client = ModelOpsClient(config)
        result = await client.calculate_vulnerability(...)

    return {'vulnerability_scores': result, ...}
```

#### Week 2: 테스트 및 검증

- [ ] Mock API 서버 구축 (FastAPI)
- [ ] Postman 테스트 컬렉션 작성
- [ ] 통합 테스트
  - [ ] `USE_INTERNAL_CALCULATION=true` 정상 동작
  - [ ] `USE_INTERNAL_CALCULATION=false` Mock API 호출 성공
  - [ ] 두 모드의 출력 형식 동일

---

### 3.2 ModelOps 팀 작업

#### Week 1: 환경 구축

- [ ] 개발 환경 구축
- [ ] PostgreSQL 데이터베이스 설정
- [ ] DB 테이블 생성 (03_DATA_SCHEMA.md 참조)
  - [ ] `modelops_hazard_scores`
  - [ ] `modelops_vulnerability_cache`
  - [ ] `modelops_aal_cache`

#### Week 2: API 개발 시작

- [ ] FastAPI 프로젝트 초기화
- [ ] API 엔드포인트 스텁 구현
  - [ ] `POST /api/v1/calculate/vulnerability`
  - [ ] `POST /api/v1/calculate/exposure`
  - [ ] `POST /api/v1/calculate/aal`
  - [ ] `GET /api/v1/hazard-scores`

- [ ] 입력 검증 로직 구현 (Pydantic)

---

### 3.3 완료 기준
- [ ] AI Agent Dual Mode 정상 동작
- [ ] Mock API 서버 동작 확인
- [ ] ModelOps API 스텁 배포 완료

---

## 4. Phase 2: ModelOps 연동 테스트 (2주)

### 4.1 ModelOps 팀 작업

#### Week 3: 계산 로직 구현

- [ ] Vulnerability 계산 로직 구현 (02_CALCULATION_LOGIC.md 섹션 1)
  - [ ] 9개 리스크별 함수 구현
  - [ ] 단위 테스트 작성
- [ ] Exposure 계산 로직 구현
- [ ] AAL 계산 로직 구현
  - [ ] Base AAL 계산
  - [ ] 취약성 스케일링
  - [ ] 최종 AAL 계산

#### Week 4: 배치 작업 구현

- [ ] Hazard Score 배치 작업 구현
  - [ ] CMIP6 데이터 로드
  - [ ] 백분위수 계산
  - [ ] DB 적재
- [ ] 스케줄러 설정 (주간 실행)

---

### 4.2 AI Agent 팀 작업

#### Week 3-4: 통합 테스트

- [ ] ModelOps API 연동
  - [ ] `.env` 업데이트 (`MODELOPS_ENABLED=true`)
  - [ ] API 키 발급 받기

- [ ] 배치 데이터 검증
  - [ ] H, P(H) DB 조회 테스트
  - [ ] 9개 리스크 × 4개 SSP 데이터 확인

- [ ] 실시간 API 테스트
  - [ ] 10개 다양한 건물 조건으로 V Score 테스트
  - [ ] 응답 시간 측정 (목표: < 2초)
  - [ ] AAL 계산 테스트

- [ ] 성능 테스트
  - [ ] 동시 요청 10개 부하 테스트
  - [ ] 캐시 히트율 측정
  - [ ] 메모리 사용량 모니터링

- [ ] E2E 테스트
  - [ ] 전체 워크플로우 실행 (10개 시나리오)
  - [ ] 기존 내부 계산 결과와 비교 (편차 < 5%)

---

### 4.3 완료 기준
- [ ] ModelOps API 100개 요청 성공률 > 99%
- [ ] 캐시 히트율 > 70% (재요청 시)
- [ ] 전체 워크플로우 실행 시간 < 30초
- [ ] 계산 결과 편차 < 5%

---

## 5. Phase 3: 내부 로직 제거 (1주)

### 5.1 AI Agent 팀 작업

**5.1.1 환경변수 변경**
```bash
# .env
MODELOPS_ENABLED=true
USE_INTERNAL_CALCULATION=false  # 완전 제거
```

**5.1.2 파일 삭제**
```bash
# Physical Risk Score Agents 삭제 (9개)
rm -rf ai_agent/agents/risk_analysis/physical_risk_score/

# AAL Analysis Agents 삭제 (9개)
rm -rf ai_agent/agents/risk_analysis/aal_analysis/

# Vulnerability Analysis Agent 삭제
rm ai_agent/agents/data_processing/vulnerability_analysis_agent.py

# AAL Calculator Service 삭제
rm ai_agent/services/aal_calculator.py
```

**5.1.3 Import 정리**
- [ ] `ai_agent/workflow/nodes.py`에서 삭제된 Agent import 제거
- [ ] `ai_agent/agents/__init__.py` 업데이트

**5.1.4 Dual Mode 로직 제거**
- [ ] `vulnerability_analysis_node()`: ModelOps 로직만 유지
- [ ] `aal_analysis_node()`: ModelOps 로직만 유지
- [ ] `physical_risk_score_node()`: 조합 로직만 유지

**5.1.5 회귀 테스트**
- [ ] 전체 워크플로우 재실행 (10개 테스트 케이스)
- [ ] 출력 결과 검증
- [ ] LLM 보고서 생성 정상 동작 확인

---

### 5.2 완료 기준
- [ ] 삭제된 Agent import 에러 없음
- [ ] 전체 워크플로우 정상 실행
- [ ] 코드베이스 크기 30% 감소

---

## 6. Phase 4: 문서화 및 배포 (1주)

### 6.1 AI Agent 팀 작업

**6.1.1 문서화**
- [ ] `README.md` 업데이트
  - [ ] ModelOps 연동 설명 추가
  - [ ] 아키텍처 다이어그램 업데이트
- [ ] OpenAPI 스키마 재생성
- [ ] 환경변수 가이드 작성

**6.1.2 에러 핸들링 강화**
- [ ] ModelOps API 장애 시 폴백 로직
  - [ ] 캐시 데이터 사용
  - [ ] 기본값 반환 (degraded mode)
- [ ] 재시도 로직 (Exponential Backoff, 최대 3회)

**6.1.3 모니터링 설정**
- [ ] LangSmith 트레이싱 태그 추가
  - [ ] `modelops_api_call`
  - [ ] `cache_hit` / `cache_miss`
- [ ] 성능 메트릭 로깅

**6.1.4 배포 준비**
- [ ] Docker 이미지 빌드 테스트
- [ ] 프로덕션 설정 파일 작성
- [ ] CI/CD 파이프라인 업데이트

---

### 6.2 ModelOps 팀 작업

**6.2.1 운영 준비**
- [ ] 프로덕션 환경 배포
- [ ] 로드 밸런서 설정
- [ ] 모니터링 대시보드 구축

**6.2.2 성능 최적화**
- [ ] DB 인덱스 최적화
- [ ] API 응답 시간 개선
- [ ] 캐싱 전략 최적화

---

### 6.3 완료 기준
- [ ] 모든 문서 작성 완료
- [ ] 프로덕션 배포 체크리스트 100% 완료
- [ ] 팀 리뷰 승인

---

## 7. 협업 체크리스트

### 7.1 정기 미팅
- [ ] Kick-off 미팅 (Phase 0)
- [ ] 주간 동기화 미팅 (매주 목요일 14:00)
- [ ] Phase 완료 리뷰 미팅 (각 Phase 종료 시)

### 7.2 커뮤니케이션 채널
- **Slack**: #modelops-integration
- **이슈 트래킹**: Jira 프로젝트 생성
- **문서 공유**: Confluence

### 7.3 담당자
| 역할 | AI Agent 팀 | ModelOps 팀 |
|------|------------|------------|
| 프로젝트 매니저 | [이름] | [이름] |
| 기술 리드 | [이름] | [이름] |
| 개발자 | [이름] | [이름] |

---

## 8. 리스크 관리

### 8.1 기술적 리스크

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| ModelOps API 장애 | 높음 | - 캐시 폴백<br>- Degraded Mode<br>- SLA 99.9% 협의 |
| 응답 시간 초과 | 중간 | - 비동기 처리<br>- 타임아웃 60초<br>- 캐싱 적극 활용 |
| 데이터 불일치 | 중간 | - 검증 로직 강화<br>- 편차 모니터링 |

### 8.2 일정 리스크
- **지연 발생 시**: 주간 미팅에서 조기 보고
- **우선순위 조정**: Phase 2와 3 병합 가능
- **롤백 계획**: Dual Mode 유지 가능

---

## 9. SLA (Service Level Agreement)

### 9.1 API 성능
- **응답 시간** (95th percentile):
  - Vulnerability: < 2초
  - Exposure: < 1초
  - AAL: < 3초
  - Hazard Score 조회: < 100ms

- **Uptime**: 99.9%
- **동시 처리**: 10개 요청
- **Rate Limit**: 100 req/min

### 9.2 데이터 품질
- **정확도**: 기존 계산 대비 편차 < 5%
- **완전성**: 9개 리스크 × 4개 SSP 모두 제공
- **신선도**: 배치 데이터 주 1회 갱신

---

## 10. 최종 체크리스트

### Phase 0
- [ ] 문서 6개 작성 완료
- [ ] ModelOps 팀 검토 완료
- [ ] Kick-off 미팅 완료

### Phase 1
- [ ] Dual Mode 구현 완료
- [ ] Mock API 테스트 성공
- [ ] ModelOps API 스텁 완료

### Phase 2
- [ ] ModelOps API 연동 성공
- [ ] 성능 테스트 통과
- [ ] E2E 테스트 통과

### Phase 3
- [ ] 22개 파일 삭제 완료
- [ ] 회귀 테스트 통과
- [ ] Import 에러 없음

### Phase 4
- [ ] 문서화 완료
- [ ] 프로덕션 배포 완료
- [ ] 모니터링 설정 완료

---

## 11. 연락처

### AI Agent 팀
- **프로젝트 매니저**: [이름] / [이메일]
- **기술 리드**: [이름] / [이메일]

### ModelOps 팀
- **프로젝트 매니저**: [이름] / [이메일]
- **기술 리드**: [이름] / [이메일]

---

## 부록: 유용한 명령어

### 환경변수 설정 (개발)
```bash
export MODELOPS_ENABLED=false
export USE_INTERNAL_CALCULATION=true
```

### 환경변수 설정 (운영)
```bash
export MODELOPS_ENABLED=true
export USE_INTERNAL_CALCULATION=false
```

### Docker 빌드
```bash
docker build -t ai-agent:latest .
docker run -p 8000:8000 --env-file .env ai-agent:latest
```

### 테스트 실행
```bash
# 단위 테스트
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# E2E 테스트
pytest tests/e2e/
```

---

**문서 종료**

이관 과정에서 질문이나 이슈가 발생하면 Slack #modelops-integration 채널로 문의해주세요.
