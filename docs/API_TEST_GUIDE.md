# ModelOps API 테스트 가이드

## 📌 목차
- [API 개요](#api-개요)
- [테스트 방법](#테스트-방법)
- [테스트 결과](#테스트-결과)
- [향후 수행 방법](#향후-수행-방법)

---

## 🎯 API 개요

### API가 하는 일

ModelOps Risk Assessment API는 **물리적 기후 리스크(Physical Climate Risk)를 계산**하는 서비스입니다.

#### 주요 기능

1. **E (Exposure) 계산** - 노출도 평가
   - 건물/자산이 기후 리스크에 얼마나 노출되어 있는지 계산

2. **V (Vulnerability) 계산** - 취약성 평가
   - 건물 구조, 연령, 인프라 상태 등을 고려한 취약성 점수 산출

3. **AAL (Average Annual Loss) 계산** - 연평균손실 계산
   - Base AAL에 취약성을 반영하여 최종 손실 확률 산출
   - 보험율을 고려한 실질 손실 계산

#### 9개 물리적 리스크

| 리스크 | 설명 | 영문 |
|--------|------|------|
| 극한 고온 | 폭염, 열파 | extreme_heat |
| 극한 한파 | 한파, 혹한 | extreme_cold |
| 산불 | 산불 발생 | wildfire |
| 가뭄 | 물 부족 | drought |
| 물 스트레스 | 수자원 고갈 | water_stress |
| 해수면 상승 | 해안 침수 | sea_level_rise |
| 하천 홍수 | 강 범람 | river_flood |
| 도시 홍수 | 도시 침수 | urban_flood |
| 태풍 | 강풍, 폭우 | typhoon |

### API 처리 방식

```
사용자 요청 (위도, 경도)
    ↓
API 큐에 등록 (queued)
    ↓
백그라운드 계산 시작 (processing)
    ↓
9개 리스크 순차 계산 (Mini-batch)
    ├─ 1/9: extreme_heat (11.1%)
    ├─ 2/9: extreme_cold (22.2%)
    ├─ 3/9: wildfire (33.3%)
    ├─ ...
    └─ 9/9: typhoon (100%)
    ↓
결과 DB 저장
    ↓
완료 (completed)
```

### 실시간 진행률 제공

프론트엔드에서 계산 진행 상황을 실시간으로 확인할 수 있습니다:

- **WebSocket 방식**: 서버가 자동으로 진행률 푸시
- **HTTP Polling 방식**: 클라이언트가 주기적으로 상태 조회

---

## 🧪 테스트 방법

### 테스트 파일 구성

프로젝트에는 3가지 테스트 파일이 있습니다:

| 파일 | 목적 | 서버 필요 | DB 필요 | WebSocket |
|------|------|----------|---------|-----------|
| `test_with_mock_data_fixed.py` | 계산 로직 검증 | ❌ | ❌ | ❌ |
| `test_api_with_mock.py` | **API 서버 테스트** | ✅ | ❌ | ✅ |
| `test_complete_system.py` | 완전한 통합 테스트 | ✅ | ✅ | ✅ |

### API 테스트 수행 방법 (test_api_with_mock.py)

#### 1단계: Mock API 서버 실행

**터미널 1**에서 실행:

```bash
python test_api_with_mock.py
```

**출력 예시:**
```
================================================================================
Mock API 서버 시작 (DB 연결 없이 동작)
================================================================================
✅ Mock DatabaseConnection 주입 완료
================================================================================
API 문서: http://localhost:8001/docs
Health Check: http://localhost:8001/health
================================================================================
서버를 종료하려면 Ctrl+C를 누르세요
================================================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

#### 2단계: API 테스트 실행

**터미널 2**에서 실행:

```bash
python test_api_with_mock.py --test
```

### 테스트 항목

#### TEST 1: Health Check API
```http
GET http://localhost:8001/health
```

**목적**: 서버가 정상 동작하는지 확인

**응답 예시**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-07T15:57:11.000Z"
}
```

#### TEST 2: Root Endpoint
```http
GET http://localhost:8001/
```

**목적**: API 정보 및 사용 가능한 엔드포인트 확인

**응답 예시**:
```json
{
  "service": "ModelOps Risk Assessment API",
  "version": "1.0.0",
  "description": "E, V, AAL 계산 API with Real-time Progress",
  "docs": "/docs",
  "health": "/health",
  "endpoints": {
    "calculate": "POST /api/v1/risk-assessment/calculate",
    "status": "GET /api/v1/risk-assessment/status/{request_id}",
    "websocket": "WS /api/v1/risk-assessment/ws/{request_id}",
    "results": "GET /api/v1/risk-assessment/results/{lat}/{lon}"
  }
}
```

#### TEST 3: Calculate API + WebSocket

**3-1. 계산 요청**

```http
POST http://localhost:8001/api/v1/risk-assessment/calculate
Content-Type: application/json

{
  "latitude": 37.5665,
  "longitude": 126.9780
}
```

**응답**:
```json
{
  "request_id": "req-c23462f5-7c26-4bb0-9d59-f69b6bf84dfb",
  "status": "queued",
  "websocket_url": "ws://localhost:8001/api/v1/risk-assessment/ws/req-c23462f5-7c26-4bb0-9d59-f69b6bf84dfb",
  "message": "계산이 큐에 등록되었습니다. WebSocket으로 실시간 진행상황을 확인하세요."
}
```

**3-2. WebSocket 진행률 모니터링**

```javascript
// 브라우저 콘솔 또는 JavaScript 코드
const ws = new WebSocket('ws://localhost:8001/api/v1/risk-assessment/ws/req-xxxxx');

ws.onmessage = (event) => {
    const progress = JSON.parse(event.data);
    const percentage = (progress.current / progress.total) * 100;

    console.log(`진행률: ${percentage.toFixed(1)}%`);
    console.log(`현재 리스크: ${progress.current_risk}`);

    if (progress.status === 'completed') {
        console.log('✅ 완료!', progress.results);
    }
};
```

**WebSocket 메시지 예시**:
```json
// 진행 중
{
  "status": "processing",
  "current": 3,
  "total": 9,
  "current_risk": "wildfire",
  "results": null,
  "error": null
}

// 완료
{
  "status": "completed",
  "current": 9,
  "total": 9,
  "current_risk": null,
  "results": {
    "exposure": { /* ... */ },
    "vulnerability": { /* ... */ },
    "aal_scaled": { /* ... */ },
    "summary": {
      "average_vulnerability": 46.0,
      "average_exposure": 0.4,
      "highest_aal_risk": {
        "risk_type": "typhoon",
        "final_aal": 0.045
      }
    }
  },
  "error": null
}
```

#### TEST 4: Status Polling API

**HTTP Polling 방식** (WebSocket 대안)

```http
GET http://localhost:8001/api/v1/risk-assessment/status/req-xxxxx
```

**응답 예시**:
```json
{
  "status": "processing",
  "current": 5,
  "total": 9,
  "current_risk": "water_stress"
}
```

**프론트엔드 구현 예시**:
```javascript
const checkProgress = async (requestId) => {
    const response = await fetch(
        `http://localhost:8001/api/v1/risk-assessment/status/${requestId}`
    );
    const progress = await response.json();

    // UI 업데이트
    updateProgressBar(progress.current / progress.total * 100);

    return progress.status;
};

// 0.5초마다 확인
const interval = setInterval(async () => {
    const status = await checkProgress(requestId);
    if (status === 'completed' || status === 'failed') {
        clearInterval(interval);
    }
}, 500);
```

---

## 📊 테스트 결과

### 실제 테스트 실행 결과

```
================================================================================
Mock API 서버 테스트 (DB 연결 불필요)
================================================================================

⚠️  Mock API 서버가 실행 중이어야 합니다!
    터미널 1: python test_api_with_mock.py
    터미널 2: python test_api_with_mock.py --test

서버 연결 확인 중...
✅ 서버 연결 확인 완료

================================================================================
TEST 1: Health Check API
================================================================================
   ✅ Health Check 성공
   Status: healthy

================================================================================
TEST 2: Root Endpoint
================================================================================
   ✅ Root 엔드포인트 성공
   Service: ModelOps Risk Assessment API
   Version: 1.0.0
   Endpoints: 4개

================================================================================
TEST 3: Calculate API + WebSocket Progress
================================================================================
1단계: 계산 요청 (POST /api/v1/risk-assessment/calculate)
   ✅ API 호출 성공
   Request ID: req-c23462f5-7c26-4bb0-9d59-f69b6bf84dfb
   Status: queued

2단계: WebSocket 실시간 진행률 모니터링
   연결 URL: ws://127.0.0.1:8001/api/v1/risk-assessment/ws/req-xxxxx
   ✅ WebSocket 연결 성공

   [진행률 모니터링]
   ----------------------------------------------------------------------
   [  0.0%] 0/9 - Status: queued       - Current: -
   [ 11.1%] 1/9 - Status: processing  - Current: extreme_heat
   [ 22.2%] 2/9 - Status: processing  - Current: extreme_cold
   [ 33.3%] 3/9 - Status: processing  - Current: wildfire
   [ 44.4%] 4/9 - Status: processing  - Current: drought
   [ 55.6%] 5/9 - Status: processing  - Current: water_stress
   [ 66.7%] 6/9 - Status: processing  - Current: sea_level_rise
   [ 77.8%] 7/9 - Status: processing  - Current: river_flood
   [ 88.9%] 8/9 - Status: processing  - Current: urban_flood
   [100.0%] 9/9 - Status: processing  - Current: typhoon
   [100.0%] 9/9 - Status: completed   - Current: -
   ----------------------------------------------------------------------
   ✅ 계산 완료!

   [계산 결과 요약]
   - 평균 취약성: 46.0
   - 평균 노출도: 0.4

================================================================================
TEST 4: Status Polling API
================================================================================
1단계: 계산 요청
   ✅ Request ID: req-fd1d200c-fe78-459f-aff0-55ede2cf886f

2단계: HTTP Polling (0.5초 간격)
   ----------------------------------------------------------------------
   [Poll #  1] 100.0% - 9/9 - completed
   ----------------------------------------------------------------------
   ✅ Polling 완료!

================================================================================
테스트 결과 요약
================================================================================
Health Check                  : ✅ PASS
Root Endpoint                 : ✅ PASS
Calculate + WebSocket         : ✅ PASS
Status Polling                : ✅ PASS
================================================================================
전체: 4 / 통과: 4 / 실패: 0
================================================================================
```

### 검증된 사항

✅ **API 서버 정상 동작**
- FastAPI 서버가 정상적으로 실행됨
- 모든 엔드포인트가 응답함

✅ **Mock DB 연동 성공**
- DB 연결 없이도 계산 로직이 동작
- Mock 데이터로 9개 리스크 계산 완료

✅ **WebSocket 실시간 통신**
- 클라이언트-서버 양방향 통신 성공
- 진행률이 0% → 100%까지 실시간 전송됨

✅ **HTTP Polling 동작**
- WebSocket 대안으로 HTTP API도 정상 동작
- 0.5초 간격 상태 조회 성공

✅ **Mini-batch 처리**
- 9개 리스크가 순차적으로 처리됨
- 각 단계마다 진행률 업데이트

✅ **계산 로직 실행**
- Exposure, Vulnerability, AAL 계산이 실제로 수행됨
- 최종 결과 반환 확인

---

## 🚀 향후 수행 방법

### 개발 단계별 테스트 전략

#### 1단계: 로컬 개발 (DB 없음)

**목적**: 계산 로직 및 API 동작 검증

```bash
# 계산 로직 테스트
python test_with_mock_data_fixed.py

# API 서버 테스트
# 터미널 1
python test_api_with_mock.py

# 터미널 2
python test_api_with_mock.py --test
```

**장점**:
- 빠른 실행
- DB 설정 불필요
- 로직 오류 빠르게 발견

#### 2단계: 통합 테스트 (실제 DB 연결)

**목적**: DB 연동 포함 전체 시스템 검증

```bash
# 1. .env 파일 설정
# DW_HOST, DW_PORT, DW_NAME 등 설정

# 2. API 서버 실행
python main.py

# 3. 통합 테스트 실행
python test_complete_system.py
```

**확인 사항**:
- DB 연결 정상
- 실제 데이터 조회
- 결과 DB 저장
- 스케줄러 동작

#### 3단계: 프로덕션 배포

**배포 전 체크리스트**:

- [ ] `.env` 파일 프로덕션 설정 확인
- [ ] DB 연결 정보 검증
- [ ] API 서버 실행 테스트
- [ ] Health Check 응답 확인
- [ ] 실제 좌표로 계산 테스트
- [ ] WebSocket 연결 확인
- [ ] 스케줄러 동작 확인

**서버 실행**:

```bash
# 개발 모드
python main.py --reload

# 프로덕션 모드
python main.py --port 8001 --log-level info
```

### 프론트엔드 연동

#### React/Vue.js 예시

**1. API 호출 및 WebSocket 연결**

```javascript
// api.js
export async function calculateRisk(latitude, longitude) {
  const response = await fetch('http://api.example.com/api/v1/risk-assessment/calculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ latitude, longitude })
  });

  return await response.json();
}

// components/RiskCalculator.jsx
import { useState, useEffect } from 'react';

function RiskCalculator() {
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);

  const handleCalculate = async () => {
    // 1. 계산 요청
    const { request_id, websocket_url } = await calculateRisk(37.5665, 126.9780);

    // 2. WebSocket 연결
    const ws = new WebSocket(websocket_url);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const percentage = (data.current / data.total) * 100;

      setProgress(percentage);

      if (data.status === 'completed') {
        setResults(data.results);
        ws.close();
      }
    };
  };

  return (
    <div>
      <button onClick={handleCalculate}>리스크 계산</button>
      <ProgressBar value={progress} />
      {results && <ResultsTable data={results} />}
    </div>
  );
}
```

**2. HTTP Polling 방식 (WebSocket 대안)**

```javascript
async function pollStatus(requestId) {
  const interval = setInterval(async () => {
    const response = await fetch(
      `http://api.example.com/api/v1/risk-assessment/status/${requestId}`
    );
    const progress = await response.json();

    const percentage = (progress.current / progress.total) * 100;
    updateUI(percentage);

    if (progress.status === 'completed') {
      clearInterval(interval);
      loadResults(requestId);
    }
  }, 500);
}
```

### 모니터링 및 디버깅

#### 로그 확인

```bash
# API 서버 로그
# 실행 중인 터미널에서 실시간 확인

# 특정 request_id 추적
grep "req-xxxxx" logs/api.log
```

#### Swagger UI 활용

브라우저에서 접속:
```
http://localhost:8001/docs
```

- 모든 API 엔드포인트 확인
- 직접 테스트 가능
- 요청/응답 스키마 확인

#### 문제 해결

**문제**: WebSocket 연결 실패
```
해결:
1. 서버가 실행 중인지 확인
2. 포트 8001이 열려있는지 확인
3. 방화벽 설정 확인
```

**문제**: 계산이 완료되지 않음
```
해결:
1. 서버 로그 확인
2. DB 연결 상태 확인
3. Mock 모드로 테스트하여 로직 오류 확인
```

**문제**: 진행률이 업데이트되지 않음
```
해결:
1. progress_callback이 호출되는지 확인
2. progress_store 업데이트 로그 확인
3. WebSocket 연결 상태 확인
```

### 성능 최적화

**현재 구성**:
- Mini-batch: 9개 리스크 순차 처리
- 예상 시간: 약 5-10초 (Mock 데이터 기준)

**최적화 방안**:
1. 병렬 처리 (향후 개선)
2. Redis 캐싱 (결과 저장)
3. DB 인덱스 최적화

---

## 📚 참고 자료

### API 문서
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### 테스트 파일
- `test_with_mock_data_fixed.py` - 계산 로직 단위 테스트
- `test_api_with_mock.py` - API 서버 통합 테스트 (Mock DB)
- `test_complete_system.py` - 완전한 통합 테스트 (실제 DB)

### 주요 코드 위치
- API 라우터: `modelops/api/routes/risk_assessment.py`
- IntegratedRiskAgent: `modelops/agents/risk_assessment/integrated_risk_agent.py`
- DatabaseConnection: `modelops/database/connection.py`
- 설정 파일: `.env.example` → `.env`

---

## ✅ 체크리스트

### 개발자용 체크리스트

- [ ] Mock 데이터로 계산 로직 테스트 완료
- [ ] Mock API 서버 테스트 통과 (4/4)
- [ ] WebSocket 연결 확인
- [ ] HTTP Polling 동작 확인
- [ ] 9개 리스크 모두 계산 성공
- [ ] 진행률 0% → 100% 업데이트 확인

### 배포 전 체크리스트

- [ ] 실제 DB 연결 테스트
- [ ] API 서버 Health Check 정상
- [ ] 프로덕션 환경 변수 설정
- [ ] CORS 설정 확인
- [ ] 로그 레벨 설정
- [ ] 에러 핸들링 검증
- [ ] 성능 테스트 (부하 테스트)

---

**작성일**: 2025-12-07
**버전**: 1.0.0
**작성자**: Claude Code (Anthropic)
