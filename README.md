# Backend AIops

Climate Risk AIops Workflow - Probability 및 Hazard Score 배치 계산 시스템

## 개요

이 시스템은 기후 위험 분석을 위한 AI Operations 워크플로우를 제공합니다:

- **P(H) 계산**: 9대 기후 리스크별 확률 및 Bin별 기본 손상률 계산
- **Hazard Score 계산**: 9대 기후 리스크별 위험도 점수 계산
- **스케줄링**: 연 1회 자동 실행 (1월 1일)
- **수동 트리거**: PostgreSQL NOTIFY를 통한 즉시 실행

## 9대 기후 리스크

1. Coastal Flood (해안 홍수)
2. Cold Wave (한파)
3. Drought (가뭄)
4. High Temperature (고온)
5. Inland Flood (내륙 홍수)
6. Typhoon (태풍)
7. Urban Flood (도시 홍수)
8. Water Scarcity (물 부족)
9. Wildfire (산불)

## 설치

```bash
# 저장소 클론
git clone https://github.com/your-org/backend_aiops.git
cd backend_aiops

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 데이터베이스 정보 입력

# uv 설치 (없는 경우)
pip install uv

# 의존성 설치
uv pip install -e .
```

## 실행

### 로컬 실행

```bash
python main.py
```

### Docker 실행

```bash
docker build -t backend-aiops .
docker run -d --env-file .env backend-aiops
```

## 수동 트리거

PostgreSQL에서 NOTIFY 명령을 사용하여 배치 작업을 수동으로 트리거할 수 있습니다:

```sql
-- P(H) 배치 실행
NOTIFY aiops_trigger, 'probability';

-- Hazard Score 배치 실행
NOTIFY aiops_trigger, 'hazard';
```

## 스케줄

- **P(H) 계산**: 매년 1월 1일 02:00 (KST)
- **Hazard Score 계산**: 매년 1월 1일 04:00 (KST)

## 아키텍처

```
backend_aiops (이 저장소)
├── 스케줄러 (APScheduler)
├── NOTIFY 리스너 (PostgreSQL)
└── 배치 프로세서 (멀티프로세싱)

backend_fastapi (별도 저장소)
├── FastAPI 서버
└── AAL 분석 API (실시간)

공유 리소스:
└── PostgreSQL Database
    ├── climate_data (입력)
    ├── probability_results (P(H) 출력)
    └── hazard_results (Hazard 출력)
```

## 환경 변수

`.env` 파일 참조:

- `DATABASE_*`: PostgreSQL 연결 정보
- `PROBABILITY_SCHEDULE_*`: P(H) 스케줄 설정
- `HAZARD_SCHEDULE_*`: Hazard 스케줄 설정
- `PARALLEL_WORKERS`: 병렬 처리 워커 수

## 개발

```bash
# 개발 의존성 설치
uv pip install -e ".[dev]"

# 테스트 실행
pytest

# 커버리지 확인
pytest --cov=aiops
```

## 모니터링 및 로깅

시스템 로그는 다음과 같이 확인할 수 있습니다:

```bash
# Docker 로그 확인
docker logs backend_aiops -f

# 특정 시간대 로그
docker logs backend_aiops --since 1h

# 배치 작업 로그 (DB)
SELECT * FROM batch_job_logs ORDER BY started_at DESC LIMIT 10;
```

## 트러블슈팅

### NOTIFY가 수신되지 않는 경우

1. PostgreSQL 연결 확인
2. LISTEN 채널명 확인 (기본값: `aiops_trigger`)
3. 방화벽 설정 확인

### 배치 작업이 실패하는 경우

1. `batch_job_logs` 테이블에서 에러 메시지 확인
2. Docker 로그 확인
3. 데이터베이스 연결 및 격자 좌표 데이터 확인

### 스케줄러가 작동하지 않는 경우

1. 타임존 설정 확인
2. APScheduler 로그 확인
3. cron 표현식 검증