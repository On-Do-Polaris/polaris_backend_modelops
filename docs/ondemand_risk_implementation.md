# On-Demand E/V/AAL 계산 구현 완료 보고서

**작성일**: 2025-12-03
**버전**: v1.0
**상태**: ✅ 구현 완료

---

## 1. 구현 개요

사용자 요청 시 E (Exposure), V (Vulnerability), AAL (Average Annual Loss)을 **실시간으로 계산**하고, 진행상황을 `batch_jobs` 테이블에 추적하는 On-Demand 배치 시스템을 구현하였습니다.

### 핵심 특징
- ✅ **On-Demand 실행**: API 트리거 방식 (배치 스케줄러 아님)
- ✅ **진행률 실시간 추적**: batch_jobs 테이블 (0-100%)
- ✅ **9개 리스크 지원**: 폭염, 한파, 산불, 가뭄, 물부족, 해수면상승, 하천홍수, 도시홍수, 태풍
- ✅ **에러 복구**: 중간 실패 시 상세 에러 기록
- ✅ **결과 캐싱**: DB 저장으로 재사용

---

## 2. 구현 파일

### 2.1 수정된 파일

#### `modelops/database/connection.py` (8개 메서드 추가)

**Batch Jobs 관리 메서드** (5개):
1. `create_batch_job()` - 배치 작업 생성
2. `update_batch_progress()` - 진행률 업데이트
3. `complete_batch_job()` - 완료 처리
4. `fail_batch_job()` - 실패 처리
5. `get_batch_status()` - 상태 조회

**조회 메서드** (3개):
6. `fetch_hazard_results()` - H (Hazard Score) 조회
7. `fetch_probability_results()` - P(H) (확률) 조회
8. `fetch_population_data()` - 인구 데이터 조회 (location_admin)

### 2.2 신규 생성 파일

#### `modelops/batch/ondemand_risk_batch.py`

**OnDemandRiskBatch 클래스**:
- `run()` - 전체 계산 실행 (E → V → AAL → 통합)
- `_fetch_hazard_and_probability()` - H, P(H) DB 조회
- `_calculate_exposures()` - E 계산 (10% → 50%)
- `_calculate_vulnerabilities()` - V 계산 (50% → 80%)
- `_calculate_aal_scaled()` - AAL 계산 (80% → 95%)
- `_calculate_integrated_risk()` - 통합 리스크 (95% → 100%)
- `_fetch_building_info()` - 건물 정보 조회 헬퍼

---

## 3. 실행 흐름

### 3.1 사용자 시나리오

```
[사용자] FastAPI 요청
    ↓
[FastAPI] batch_id 생성 → batch_jobs (status='queued', progress=0)
    ↓
[백그라운드 워커] OnDemandRiskBatch.run() 실행
    ↓
  ┌─────────────────────────────────────────┐
  │  0%: 시작                                │
  │ 10%: H, P(H) 조회 완료                   │
  │ 10-50%: E 계산 (9개 리스크)              │
  │ 50-80%: V 계산 (9개 리스크)              │
  │ 80-95%: AAL 계산 (9개 리스크)            │
  │ 95-100%: 통합 리스크 계산                │
  └─────────────────────────────────────────┘
    ↓
[DB 저장] exposure_results, vulnerability_results, aal_scaled_results
    ↓
[FastAPI] batch_jobs 업데이트 (status='completed', progress=100)
    ↓
[프론트엔드] /api/batch/{batch_id}/status 폴링 → 결과 표시
```

### 3.2 진행률 구간

| 구간 | 진행률 | 작업 내용 |
|------|--------|----------|
| 초기화 | 0% | 배치 작업 생성 |
| H/P(H) 조회 | 0% → 10% | DB에서 Hazard Score, 확률 조회 |
| E 계산 | 10% → 50% | 9개 리스크별 노출도 계산 (각 4.4%) |
| V 계산 | 50% → 80% | 9개 리스크별 취약성 계산 (각 3.3%) |
| AAL 계산 | 80% → 95% | 9개 리스크별 AAL 계산 (각 1.7%) |
| 통합 계산 | 95% → 100% | H × E × V 통합 리스크 |
| 완료 | 100% | 결과 저장 및 완료 처리 |

---

## 4. 사용 예시

### 4.1 FastAPI에서 배치 시작

```python
from modelops.batch.ondemand_risk_batch import OnDemandRiskBatch
from modelops.database.connection import DatabaseConnection
from concurrent.futures import ThreadPoolExecutor

# 백그라운드 실행기
executor = ThreadPoolExecutor(max_workers=5)

@app.post("/api/risk/calculate")
def calculate_risk(latitude: float, longitude: float, risk_types: List[str] = None):
    # 1. 배치 작업 생성
    batch_id = DatabaseConnection.create_batch_job(
        job_type='ondemand_risk_calculation',
        input_params={
            'latitude': latitude,
            'longitude': longitude,
            'risk_types': risk_types
        }
    )

    # 2. 백그라운드에서 배치 실행
    def run_batch():
        processor = OnDemandRiskBatch(batch_id)
        result = processor.run(latitude, longitude, risk_types)

    executor.submit(run_batch)

    # 3. 즉시 반환 (비동기)
    return {
        "batch_id": batch_id,
        "status": "queued",
        "message": "Risk calculation started"
    }
```

### 4.2 진행률 조회 API

```python
@app.get("/api/batch/{batch_id}/status")
def get_batch_status(batch_id: str):
    status = DatabaseConnection.get_batch_status(batch_id)

    if not status:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": status['batch_id'],
        "status": status['status'],  # 'queued', 'running', 'completed', 'failed'
        "progress": status['progress'],  # 0-100
        "results": status.get('results'),
        "error_message": status.get('error_message'),
        "created_at": status['created_at'],
        "completed_at": status.get('completed_at')
    }
```

### 4.3 프론트엔드 폴링

```javascript
async function pollBatchStatus(batchId) {
    const interval = setInterval(async () => {
        const response = await fetch(`/api/batch/${batchId}/status`);
        const data = await response.json();

        // 진행률 업데이트
        updateProgressBar(data.progress);

        // 완료 또는 실패 시 폴링 종료
        if (data.status === 'completed') {
            clearInterval(interval);
            displayResults(data.results);
        } else if (data.status === 'failed') {
            clearInterval(interval);
            displayError(data.error_message);
        }
    }, 2000);  // 2초마다 폴링
}
```

---

## 5. 계산 로직

### 5.1 E (Exposure) 계산

**사용 Agent**: `ExposureAgent`

**입력**:
- 좌표 (latitude, longitude)
- 리스크 타입 (9가지)
- 건물 정보 (BuildingClient 조회)

**출력**:
```python
{
    'exposure_score': 0.0 ~ 1.0,        # 노출도 점수
    'proximity_factor': 0.0 ~ 1.0,      # 근접도 계수
    'normalized_asset_value': 0.0 ~ 1.0 # 정규화 자산가치
}
```

**저장 테이블**: `exposure_results`

### 5.2 V (Vulnerability) 계산

**사용 Agent**: `VulnerabilityAgent`

**입력**:
- 리스크 타입
- 건물 정보 (연식, 구조, 용도 등)

**출력**:
```python
{
    'vulnerability_score': 0 ~ 100,        # 취약성 점수
    'vulnerability_level': 'very_low' ~ 'very_high',
    'factors': {                           # 세부 요인
        'building_age_score': float,
        'structure_type_score': float,
        ...
    }
}
```

**저장 테이블**: `vulnerability_results`

### 5.3 AAL (Average Annual Loss) 계산

**사용 Agent**: `AALScalingAgent`

**입력**:
- base_aal (P(H) 결과의 aal 값)
- v_score (취약성 점수)
- insurance_rate (보험 보전율, 기본 0.0)

**계산 공식**:
```
F_vuln = 0.9 + (V_score / 100) × 0.2  (범위: 0.9 ~ 1.1)
final_aal = base_aal × F_vuln × (1 - insurance_rate)
```

**출력**:
```python
{
    'base_aal': float,                  # 기본 AAL
    'vulnerability_scale': 0.9 ~ 1.1,   # F_vuln
    'final_aal': float,                 # 최종 AAL
    'insurance_rate': 0.0 ~ 1.0,        # 보험 보전율
    'expected_loss': int | None         # 예상 손실액 (원)
}
```

**저장 테이블**: `aal_scaled_results`

### 5.4 통합 리스크 계산

**사용 Agent**: `IntegratedRiskAgent`

**입력**:
- H (Hazard Score) 결과
- E (Exposure) 결과
- V (Vulnerability) 결과
- AAL 결과

**출력**:
```python
{
    'total_risk_score': float,          # 전체 리스크 점수
    'risk_level': str,                  # 위험 등급
    'risk_breakdown': {                 # 리스크별 세부
        'extreme_heat': {
            'risk_score': float,
            'contribution_percent': float
        },
        ...
    }
}
```

---

## 6. 에러 처리

### 6.1 중간 단계 실패

```python
try:
    exposures = self._calculate_exposures(...)
except Exception as e:
    # batch_jobs 테이블에 실패 기록
    DatabaseConnection.fail_batch_job(
        self.batch_id,
        error_message=str(e),
        error_stack_trace=traceback.format_exc()
    )
    raise
```

### 6.2 개별 리스크 실패

개별 리스크 계산 실패 시:
- 해당 리스크는 기본값으로 처리
- 나머지 리스크는 계속 진행
- 로그에 경고 기록

```python
try:
    e_result = self.exposure_agent.calculate_exposure(...)
except Exception as e:
    logger.error(f"E calculation failed for {risk_type}: {e}")
    # 기본값으로 처리
    results.append({
        'risk_type': risk_type,
        'exposure_score': 0.0,
        'proximity_factor': 0.0,
        'normalized_asset_value': 0.0
    })
```

### 6.3 건물 정보 조회 실패

건물 정보를 찾지 못한 경우:
- 기본값 사용 (면적 1000㎡, 연식 20년, RC 구조 등)
- 계산은 계속 진행

---

## 7. 데이터 소스

### 7.1 DB 테이블

| 테이블 | 용도 | 사용 시점 |
|--------|------|----------|
| `hazard_results` | H (Hazard Score) 조회 | Step 1 (0-10%) |
| `probability_results` | P(H), AAL 조회 | Step 1 (0-10%) |
| `api_buildings` | 건물 정보 조회 | Step 2, 3 (E, V 계산) |
| `location_admin` | 인구 데이터 조회 | Step 2, 3 (E, V 계산) |
| `location_grid` | 좌표→격자 매핑 | 건물 정보 조회 시 |
| `exposure_results` | E 결과 저장 | Step 2 완료 (50%) |
| `vulnerability_results` | V 결과 저장 | Step 3 완료 (80%) |
| `aal_scaled_results` | AAL 결과 저장 | Step 4 완료 (95%) |
| `batch_jobs` | 배치 상태 추적 | 전체 과정 |

### 7.2 외부 Agent

| Agent | 파일 경로 | 용도 |
|-------|----------|------|
| ExposureAgent | `agents/risk_assessment/exposure_agent.py` | E 계산 |
| VulnerabilityAgent | `agents/risk_assessment/vulnerability_agent.py` | V 계산 |
| AALScalingAgent | `agents/risk_assessment/aal_scaling_agent.py` | AAL 계산 |
| IntegratedRiskAgent | `agents/risk_assessment/integrated_risk_agent.py` | 통합 리스크 |

### 7.3 유틸리티

| 유틸리티 | 파일 경로 | 용도 |
|---------|----------|------|
| BuildingClient | `api_clients/building_client.py` | 건물 정보 조회 |
| GridMapper | `utils/grid_mapper.py` | 좌표→격자 매핑 |

---

## 8. 성능 고려사항

### 8.1 예상 실행 시간

| 작업 | 예상 시간 | 비고 |
|------|----------|------|
| H/P(H) 조회 | ~1초 | DB 조회 |
| E 계산 (9개) | ~3초 | 건물 정보 조회 포함 |
| V 계산 (9개) | ~2초 | 계산 로직만 |
| AAL 계산 (9개) | ~1초 | 계산 로직만 |
| 통합 계산 | ~1초 | 계산 로직만 |
| **전체** | **~8초** | 단일 좌표 기준 |

### 8.2 최적화 전략

1. **캐싱**: 동일 좌표 재요청 시 DB에서 바로 조회
2. **병렬 처리**: 여러 좌표 동시 계산 (ThreadPoolExecutor)
3. **선택적 계산**: 특정 리스크만 계산 가능 (risk_types 파라미터)

---

## 9. 테스트 시나리오

### 9.1 단일 리스크 테스트

```python
def test_single_risk():
    batch_id = DatabaseConnection.create_batch_job(
        'test', {'latitude': 37.5665, 'longitude': 126.9780}
    )

    processor = OnDemandRiskBatch(batch_id)
    result = processor.run(37.5665, 126.9780, ['extreme_heat'])

    assert result['status'] == 'success'
    assert 'extreme_heat' in result['integrated_risk']['risk_breakdown']

    # 진행률 100% 확인
    status = DatabaseConnection.get_batch_status(batch_id)
    assert status['progress'] == 100
    assert status['status'] == 'completed'
```

### 9.2 전체 리스크 테스트

```python
def test_all_risks():
    batch_id = DatabaseConnection.create_batch_job(
        'test', {'latitude': 37.5665, 'longitude': 126.9780}
    )

    processor = OnDemandRiskBatch(batch_id)
    result = processor.run(37.5665, 126.9780)  # None = 전체 9개

    assert result['status'] == 'success'
    assert len(result['risk_types']) == 9
```

### 9.3 진행률 추적 테스트

```python
def test_progress_tracking():
    import time

    batch_id = DatabaseConnection.create_batch_job(
        'test', {'latitude': 37.5665, 'longitude': 126.9780}
    )

    # 백그라운드에서 실행
    executor.submit(lambda: OnDemandRiskBatch(batch_id).run(37.5665, 126.9780))

    # 폴링 시뮬레이션
    progress_history = []
    for _ in range(10):
        time.sleep(1)
        status = DatabaseConnection.get_batch_status(batch_id)
        progress_history.append(status['progress'])

        if status['status'] == 'completed':
            break

    # 진행률이 증가하는지 확인
    assert progress_history[-1] == 100
    assert all(progress_history[i] <= progress_history[i+1]
              for i in range(len(progress_history)-1))
```

---

## 10. 추후 개선 사항

### 10.1 성능 개선
- [ ] Redis 캐싱: 건물 정보, 인구 데이터 캐싱
- [ ] 배치 큐: Celery 도입으로 대량 요청 처리
- [ ] 병렬 E/V/AAL 계산: 리스크별 독립 계산 시 병렬화

### 10.2 기능 추가
- [ ] 부분 재계산: E만, V만, AAL만 재계산 옵션
- [ ] 이력 관리: 동일 좌표 이전 계산 결과 비교
- [ ] 알림: 계산 완료 시 이메일/웹훅 알림

### 10.3 에러 처리 강화
- [ ] 재시도 로직: 일시적 실패 시 자동 재시도
- [ ] 부분 실패 허용: 일부 리스크 실패 시에도 진행
- [ ] 상세 로깅: 각 단계별 소요 시간 기록

---

## 11. 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| 구현 계획 | `.claude/plans/structured-brewing-feigenbaum.md` | 상세 구현 계획서 |
| ERD | `docs/erd (1).md` | 최신 ERD (v07) |
| DB팀 요청사항 | `docs/DB팀_전달_요청사항.md` | 스키마 수정 요청서 |
| Phase 1-3 구현 요약 | `docs/modelops_implementation_summary.md` | 전처리 레이어 구현 요약 |

---

**작성자**: ModelOps 팀
**최종 업데이트**: 2025-12-03
**문서 버전**: v1.0
