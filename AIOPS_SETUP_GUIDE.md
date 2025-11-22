# Backend AIops Setup Guide

이 문서는 `backend_aiops` 저장소를 새로 생성하고 설정하는 완전한 가이드입니다.

## 1. 저장소 구조

```
backend_aiops/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── aiops/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── probability_calculate/
│   │   │   ├── __init__.py
│   │   │   ├── coastal_flood_probability_agent.py
│   │   │   ├── cold_wave_probability_agent.py
│   │   │   ├── drought_probability_agent.py
│   │   │   ├── high_temperature_probability_agent.py
│   │   │   ├── inland_flood_probability_agent.py
│   │   │   ├── typhoon_probability_agent.py
│   │   │   ├── urban_flood_probability_agent.py
│   │   │   ├── water_scarcity_probability_agent.py
│   │   │   └── wildfire_probability_agent.py
│   │   └── hazard_calculate/
│   │       ├── __init__.py
│   │       ├── coastal_flood_hscore_agent.py
│   │       ├── cold_wave_hscore_agent.py
│   │       ├── drought_hscore_agent.py
│   │       ├── high_temperature_hscore_agent.py
│   │       ├── inland_flood_hscore_agent.py
│   │       ├── typhoon_hscore_agent.py
│   │       ├── urban_flood_hscore_agent.py
│   │       ├── water_scarcity_hscore_agent.py
│   │       └── wildfire_hscore_agent.py
│   ├── batch/
│   │   ├── __init__.py
│   │   ├── probability_batch.py
│   │   ├── hazard_batch.py
│   │   ├── probability_scheduler.py
│   │   └── hazard_scheduler.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py
│   └── triggers/
│       ├── __init__.py
│       └── notify_listener.py
├── Dockerfile
├── pyproject.toml
├── main.py
├── README.md
└── .env.example
```

## 2. 필수 파일 생성

### 2.1 pyproject.toml

```toml
[project]
name = "backend-aiops"
version = "0.1.0"
description = "AIops workflow for climate risk batch processing"
requires-python = ">=3.11"
dependencies = [
    "apscheduler>=3.10.4",
    "psycopg2-binary>=2.9.9",
    "python-dotenv>=1.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
]
```

### 2.2 .env.example

```env
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=climate_risk_db
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password

# Scheduler Configuration
PROBABILITY_SCHEDULE_MONTH=1
PROBABILITY_SCHEDULE_DAY=1
PROBABILITY_SCHEDULE_HOUR=2
PROBABILITY_SCHEDULE_MINUTE=0

HAZARD_SCHEDULE_MONTH=1
HAZARD_SCHEDULE_DAY=1
HAZARD_SCHEDULE_HOUR=4
HAZARD_SCHEDULE_MINUTE=0

# Batch Processing Configuration
PARALLEL_WORKERS=4
BATCH_SIZE=1000

# PostgreSQL LISTEN/NOTIFY
NOTIFY_CHANNEL=aiops_trigger
```

### 2.3 aiops/config/settings.py

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "climate_risk_db"
    database_user: str = "postgres"
    database_password: str = ""

    # Scheduler
    probability_schedule_month: int = 1
    probability_schedule_day: int = 1
    probability_schedule_hour: int = 2
    probability_schedule_minute: int = 0

    hazard_schedule_month: int = 1
    hazard_schedule_day: int = 1
    hazard_schedule_hour: int = 4
    hazard_schedule_minute: int = 0

    # Batch Processing
    parallel_workers: int = 4
    batch_size: int = 1000

    # NOTIFY
    notify_channel: str = "aiops_trigger"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
```

### 2.4 aiops/database/connection.py

```python
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any
from ..config.settings import settings


class DatabaseConnection:
    """PostgreSQL 데이터베이스 연결 관리"""

    @staticmethod
    def get_connection_string() -> str:
        """데이터베이스 연결 문자열 생성"""
        return (
            f"host={settings.database_host} "
            f"port={settings.database_port} "
            f"dbname={settings.database_name} "
            f"user={settings.database_user} "
            f"password={settings.database_password}"
        )

    @staticmethod
    @contextmanager
    def get_connection():
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = psycopg2.connect(
            DatabaseConnection.get_connection_string(),
            cursor_factory=RealDictCursor
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def fetch_grid_coordinates() -> List[Dict[str, float]]:
        """모든 격자 좌표 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT latitude, longitude
                FROM climate_data
                ORDER BY latitude, longitude
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def fetch_climate_data(latitude: float, longitude: float) -> Dict[str, Any]:
        """특정 격자의 기후 데이터 조회"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM climate_data
                WHERE latitude = %s AND longitude = %s
                ORDER BY year, month
            """, (latitude, longitude))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def save_probability_results(results: List[Dict[str, Any]]) -> None:
        """P(H) 계산 결과 저장"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO probability_results
                    (latitude, longitude, risk_type, probability, bin_data, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(probability)s, %(bin_data)s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        probability = EXCLUDED.probability,
                        bin_data = EXCLUDED.bin_data,
                        calculated_at = EXCLUDED.calculated_at
                """, result)

    @staticmethod
    def save_hazard_results(results: List[Dict[str, Any]]) -> None:
        """Hazard Score 계산 결과 저장"""
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute("""
                    INSERT INTO hazard_results
                    (latitude, longitude, risk_type, hazard_score,
                     hazard_score_100, hazard_level, calculated_at)
                    VALUES (%(latitude)s, %(longitude)s, %(risk_type)s,
                            %(hazard_score)s, %(hazard_score_100)s,
                            %(hazard_level)s, NOW())
                    ON CONFLICT (latitude, longitude, risk_type)
                    DO UPDATE SET
                        hazard_score = EXCLUDED.hazard_score,
                        hazard_score_100 = EXCLUDED.hazard_score_100,
                        hazard_level = EXCLUDED.hazard_level,
                        calculated_at = EXCLUDED.calculated_at
                """, result)
```

### 2.5 aiops/triggers/notify_listener.py

```python
import select
import psycopg2
import logging
from typing import Callable, Dict, Any
from ..config.settings import settings
from ..database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class NotifyListener:
    """PostgreSQL LISTEN/NOTIFY를 사용한 외부 트리거 리스너"""

    def __init__(self):
        self.conn = None
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, job_type: str, handler: Callable) -> None:
        """작업 타입별 핸들러 등록

        Args:
            job_type: 'probability' 또는 'hazard'
            handler: 실행할 핸들러 함수
        """
        self.handlers[job_type] = handler
        logger.info(f"Handler registered for job type: {job_type}")

    def start_listening(self) -> None:
        """NOTIFY 리스닝 시작"""
        connection_string = DatabaseConnection.get_connection_string()
        self.conn = psycopg2.connect(connection_string)
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = self.conn.cursor()
        cursor.execute(f"LISTEN {settings.notify_channel};")
        logger.info(f"Listening on channel: {settings.notify_channel}")

        print(f"🎧 Listening for PostgreSQL NOTIFY on channel '{settings.notify_channel}'...")

        while True:
            if select.select([self.conn], [], [], 5) == ([], [], []):
                continue
            else:
                self.conn.poll()
                while self.conn.notifies:
                    notify = self.conn.notifies.pop(0)
                    self._handle_notify(notify.payload)

    def _handle_notify(self, payload: str) -> None:
        """NOTIFY 메시지 처리

        Payload 형식: 'probability' 또는 'hazard'
        """
        logger.info(f"Received NOTIFY: {payload}")

        if payload in self.handlers:
            try:
                logger.info(f"Executing handler for: {payload}")
                self.handlers[payload]()
                logger.info(f"Handler completed for: {payload}")
            except Exception as e:
                logger.error(f"Error executing handler for {payload}: {e}")
        else:
            logger.warning(f"No handler registered for job type: {payload}")

    def stop_listening(self) -> None:
        """리스닝 중지"""
        if self.conn:
            self.conn.close()
            logger.info("Stopped listening")
```

### 2.6 aiops/batch/probability_batch.py

`backend_team/ai_agent/aiops_workflow/batch/probability_batch.py` 파일을 복사하되, 다음 수정사항 적용:

```python
# 임포트 수정
from ..agents.probability_calculate import (
    CoastalFloodProbabilityAgent,
    ColdWaveProbabilityAgent,
    # ... 나머지 agents
)
from ..database.connection import DatabaseConnection

class ProbabilityBatchProcessor:
    # ... 기존 코드 유지

    def _fetch_climate_data(self, coordinate: Dict[str, float]) -> Dict[str, Any]:
        """기후 데이터 조회 (실제 구현)"""
        return DatabaseConnection.fetch_climate_data(
            coordinate['latitude'],
            coordinate['longitude']
        )

    def _save_results(self, coordinate: Dict[str, float],
                     probabilities: Dict[str, Any]) -> None:
        """결과 저장 (실제 구현)"""
        results = []
        for risk_type, data in probabilities.items():
            results.append({
                'latitude': coordinate['latitude'],
                'longitude': coordinate['longitude'],
                'risk_type': risk_type,
                'probability': data.get('probability'),
                'bin_data': data.get('bin_data')
            })
        DatabaseConnection.save_probability_results(results)
```

### 2.7 aiops/batch/hazard_batch.py

`backend_team/ai_agent/aiops_workflow/batch/hazard_batch.py` 파일을 복사하되, 동일한 수정사항 적용:

```python
from ..agents.hazard_calculate import (
    CoastalFloodHScoreAgent,
    # ... 나머지 agents
)
from ..database.connection import DatabaseConnection

class HazardBatchProcessor:
    # ... 기존 코드 유지

    def _save_results(self, coordinate: Dict[str, float],
                     hazard_scores: Dict[str, Any]) -> None:
        """결과 저장 (실제 구현)"""
        results = []
        for risk_type, data in hazard_scores.items():
            results.append({
                'latitude': coordinate['latitude'],
                'longitude': coordinate['longitude'],
                'risk_type': risk_type,
                'hazard_score': data.get('hazard_score'),
                'hazard_score_100': data.get('hazard_score_100'),
                'hazard_level': data.get('hazard_level')
            })
        DatabaseConnection.save_hazard_results(results)
```

### 2.8 aiops/batch/probability_scheduler.py

`backend_team/ai_agent/aiops_workflow/batch/probability_scheduler.py` 파일을 복사하되, config 임포트 수정:

```python
from ..config.settings import settings

class ProbabilityScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.processor = ProbabilityBatchProcessor({
            'parallel_workers': settings.parallel_workers
        })

    def start(self, grid_coordinates_callback=None):
        trigger = CronTrigger(
            month=settings.probability_schedule_month,
            day=settings.probability_schedule_day,
            hour=settings.probability_schedule_hour,
            minute=settings.probability_schedule_minute
        )
        # ... 나머지 코드 동일
```

### 2.9 aiops/batch/hazard_scheduler.py

동일하게 수정

### 2.10 main.py

```python
import logging
import signal
import sys
from aiops.batch.probability_scheduler import ProbabilityScheduler
from aiops.batch.hazard_scheduler import HazardScheduler
from aiops.batch.probability_batch import ProbabilityBatchProcessor
from aiops.batch.hazard_batch import HazardBatchProcessor
from aiops.triggers.notify_listener import NotifyListener
from aiops.database.connection import DatabaseConnection
from aiops.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_probability_batch():
    """P(H) 배치 작업 실행"""
    logger.info("Starting Probability batch job (triggered)")
    processor = ProbabilityBatchProcessor({
        'parallel_workers': settings.parallel_workers
    })
    grid_coordinates = DatabaseConnection.fetch_grid_coordinates()
    result = processor.process_all_grids(grid_coordinates)
    logger.info(f"Probability batch completed: {result}")


def run_hazard_batch():
    """Hazard Score 배치 작업 실행"""
    logger.info("Starting Hazard Score batch job (triggered)")
    processor = HazardBatchProcessor({
        'parallel_workers': settings.parallel_workers
    })
    grid_coordinates = DatabaseConnection.fetch_grid_coordinates()
    result = processor.process_all_grids(grid_coordinates)
    logger.info(f"Hazard batch completed: {result}")


def main():
    """메인 실행 함수"""
    logger.info("Starting AIops workflow system")

    # 스케줄러 시작
    prob_scheduler = ProbabilityScheduler()
    hazard_scheduler = HazardScheduler()

    prob_scheduler.start(grid_coordinates_callback=DatabaseConnection.fetch_grid_coordinates)
    hazard_scheduler.start(grid_coordinates_callback=DatabaseConnection.fetch_grid_coordinates)

    logger.info("Schedulers started")
    logger.info(f"  - Probability: {settings.probability_schedule_month}/{settings.probability_schedule_day} {settings.probability_schedule_hour}:{settings.probability_schedule_minute:02d}")
    logger.info(f"  - Hazard: {settings.hazard_schedule_month}/{settings.hazard_schedule_day} {settings.hazard_schedule_hour}:{settings.hazard_schedule_minute:02d}")

    # NOTIFY 리스너 설정
    listener = NotifyListener()
    listener.register_handler('probability', run_probability_batch)
    listener.register_handler('hazard', run_hazard_batch)

    # Graceful shutdown 설정
    def signal_handler(sig, frame):
        logger.info("Shutting down gracefully...")
        prob_scheduler.stop()
        hazard_scheduler.stop()
        listener.stop_listening()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # NOTIFY 리스닝 시작 (blocking)
    try:
        listener.start_listening()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        signal_handler(None, None)


if __name__ == "__main__":
    main()
```

### 2.11 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY .env .env

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY aiops/ ./aiops/
COPY main.py .

# Run the application
CMD ["python", "main.py"]
```

### 2.12 .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [ develop, main ]
  pull_request:
    branches: [ develop, main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install uv
      run: pip install uv

    - name: Install dependencies
      run: uv pip install --system -e ".[dev]"

    - name: Run tests
      run: pytest --cov=aiops --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 2.13 .github/workflows/cd.yml

```yaml
name: CD - Deploy AIops

on:
  push:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/backend_team/aiops

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=sha,prefix={{branch}}-
          type=semver,pattern={{version}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest

    steps:
    - name: Deploy to server
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.SERVER_HOST }}
        username: ${{ secrets.SERVER_USER }}
        key: ${{ secrets.SSH_PRIVATE_KEY }}
        script: |
          cd /opt/backend_aiops
          docker pull ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main
          docker-compose down
          docker-compose up -d
```

### 2.14 README.md

```markdown
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
```

## 3. backend_fastapi에서 트리거 보내기

`backend_fastapi` 저장소에 다음 함수를 추가하여 AIops 배치 작업을 트리거할 수 있습니다:

### backend_fastapi/app/services/aiops_trigger.py

```python
import psycopg2
from typing import Literal
from app.core.config import settings

JobType = Literal['probability', 'hazard']


def trigger_aiops_batch(job_type: JobType) -> bool:
    """AIops 배치 작업 트리거

    Args:
        job_type: 'probability' 또는 'hazard'

    Returns:
        성공 여부
    """
    try:
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            dbname=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD
        )
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()
        cursor.execute(f"NOTIFY aiops_trigger, '{job_type}';")

        cursor.close()
        conn.close()

        return True
    except Exception as e:
        print(f"Failed to trigger AIops batch: {e}")
        return False
```

### FastAPI 엔드포인트 예시

```python
from fastapi import APIRouter, HTTPException
from app.services.aiops_trigger import trigger_aiops_batch

router = APIRouter(prefix="/admin/aiops", tags=["admin"])


@router.post("/trigger/probability")
async def trigger_probability_batch():
    """P(H) 배치 작업 수동 트리거 (관리자용)"""
    success = trigger_aiops_batch('probability')
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger batch job")
    return {"message": "Probability batch job triggered successfully"}


@router.post("/trigger/hazard")
async def trigger_hazard_batch():
    """Hazard Score 배치 작업 수동 트리거 (관리자용)"""
    success = trigger_aiops_batch('hazard')
    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger batch job")
    return {"message": "Hazard batch job triggered successfully"}
```

## 4. 데이터베이스 스키마

AIops 시스템이 사용할 테이블 스키마:

```sql
-- P(H) 결과 저장 테이블
CREATE TABLE IF NOT EXISTS probability_results (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    probability JSONB,
    bin_data JSONB,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(latitude, longitude, risk_type)
);

CREATE INDEX idx_probability_coords ON probability_results(latitude, longitude);
CREATE INDEX idx_probability_risk_type ON probability_results(risk_type);

-- Hazard Score 결과 저장 테이블
CREATE TABLE IF NOT EXISTS hazard_results (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 6) NOT NULL,
    longitude DECIMAL(10, 6) NOT NULL,
    risk_type VARCHAR(50) NOT NULL,
    hazard_score DECIMAL(10, 4),
    hazard_score_100 DECIMAL(10, 4),
    hazard_level VARCHAR(20),
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(latitude, longitude, risk_type)
);

CREATE INDEX idx_hazard_coords ON hazard_results(latitude, longitude);
CREATE INDEX idx_hazard_risk_type ON hazard_results(risk_type);

-- 배치 작업 로그 테이블 (선택사항)
CREATE TABLE IF NOT EXISTS batch_job_logs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20),
    total_grids INTEGER,
    processed_grids INTEGER,
    failed_grids INTEGER,
    success_rate DECIMAL(5, 2),
    error_message TEXT
);
```

## 5. Agent 파일 복사

`backend_team/ai_agent/agents/aiops/` 폴더의 모든 agent 파일들을 `backend_aiops/aiops/agents/`로 복사해야 합니다:

### 복사할 파일 목록

**probability_calculate/**
- coastal_flood_probability_agent.py
- cold_wave_probability_agent.py
- drought_probability_agent.py
- high_temperature_probability_agent.py
- inland_flood_probability_agent.py
- typhoon_probability_agent.py
- urban_flood_probability_agent.py
- water_scarcity_probability_agent.py
- wildfire_probability_agent.py

**hazard_calculate/**
- coastal_flood_hscore_agent.py
- cold_wave_hscore_agent.py
- drought_hscore_agent.py
- high_temperature_hscore_agent.py
- inland_flood_hscore_agent.py
- typhoon_hscore_agent.py
- urban_flood_hscore_agent.py
- water_scarcity_hscore_agent.py
- wildfire_hscore_agent.py

## 6. 배포 가이드

### Docker Compose 예시

```yaml
# docker-compose.yml
version: '3.8'

services:
  aiops:
    image: ghcr.io/your-org/backend_team/aiops:main
    container_name: backend_aiops
    env_file:
      - .env
    restart: unless-stopped
    depends_on:
      - postgres
    networks:
      - backend_network

networks:
  backend_network:
    external: true
```

### 멀티 컨테이너 배포 구조

```
서버 환경
├── backend_fastapi (컨테이너 1)
│   ├── FastAPI 서버
│   └── 포트: 8000
│
├── backend_aiops (컨테이너 2)
│   ├── 스케줄러
│   ├── NOTIFY 리스너
│   └── 배치 프로세서
│
└── PostgreSQL (컨테이너 3)
    └── 포트: 5432
```

## 7. 모니터링 및 로깅

시스템 로그는 다음과 같이 확인할 수 있습니다:

```bash
# Docker 로그 확인
docker logs backend_aiops -f

# 특정 시간대 로그
docker logs backend_aiops --since 1h

# 배치 작업 로그 (DB)
SELECT * FROM batch_job_logs ORDER BY started_at DESC LIMIT 10;
```

## 8. 트러블슈팅

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

## 9. 다음 단계

1. **새 저장소 생성**: `backend_aiops` GitHub 저장소 생성
2. **파일 복사**: Agent 파일들을 새 저장소로 복사
3. **환경 설정**: `.env` 파일 설정
4. **데이터베이스 준비**: 테이블 스키마 생성
5. **CI/CD 설정**: GitHub Actions secrets 설정
6. **배포**: Docker 이미지 빌드 및 배포
7. **테스트**: NOTIFY 트리거로 수동 실행 테스트
8. **모니터링**: 로그 및 결과 확인

---

## 참고사항

- 이 시스템은 FastAPI를 사용하지 않습니다 (APScheduler + PostgreSQL NOTIFY만 사용)
- 모든 agent 코드는 기존 `backend_team` 저장소에서 재사용
- 데이터베이스는 `backend_fastapi`와 공유
- 독립적인 배포 및 스케일링 가능
