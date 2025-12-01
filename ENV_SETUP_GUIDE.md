# 환경변수 설정 가이드

> SKALA Physical Risk AI Backend AIops - 환경변수 설정 및 관리

최종 수정일: 2025-11-25

---

## 📋 목차

- [개요](#개요)
- [환경변수 로딩 방식](#환경변수-로딩-방식)
- [.env 파일 설정](#env-파일-설정)
- [시스템 환경변수 제거](#시스템-환경변수-제거)
- [연결 테스트](#연결-테스트)
- [문제 해결](#문제-해결)

---

## 개요

이 프로젝트는 **`.env` 파일에서만** 환경변수를 로드합니다.

### 왜 .env 파일만 사용하나요?

1. **일관성**: 모든 개발자가 동일한 설정 파일 사용
2. **보안**: `.gitignore`로 관리되어 민감한 정보 보호
3. **간편성**: 환경별로 다른 .env 파일 사용 가능 (.env.dev, .env.prod)
4. **명확성**: 시스템 환경변수와 충돌 방지

---

## 환경변수 로딩 방식

### 1. ETL 스크립트 (`ETL/scripts/db_config.py`)

```python
from dotenv import load_dotenv
from pathlib import Path

# 프로젝트 루트의 .env 파일 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)
```

**중요 옵션**:
- `dotenv_path`: 명시적으로 .env 파일 경로 지정
- `override=True`: 시스템 환경변수가 있어도 .env 파일 값 우선 적용

### 2. ModelOps (`modelops/config/settings.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_host: str = "localhost"
    database_port: int = 5433
    # ...

    class Config:
        env_file = ".env"
        case_sensitive = False
```

Pydantic의 `BaseSettings`가 자동으로 .env 파일 로드

---

## .env 파일 설정

### 1. .env.example 복사

```bash
cp .env.example .env
```

### 2. .env 파일 편집

프로젝트 루트에 `.env` 파일 생성:

```bash
# Data Warehouse Configuration (Primary DB for climate data)
DW_HOST=localhost
DW_PORT=5433
DW_NAME=skala_datawarehouse
DW_USER=skala_dw_user
DW_PASSWORD=1234

# Application Database Configuration (For Spring Boot - user/site data)
APP_HOST=localhost
APP_PORT=5432
APP_NAME=skala_application
APP_USER=skala_app_user
APP_PASSWORD=your_password

# Database Configuration (Legacy - for backward compatibility)
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_NAME=skala_datawarehouse
DATABASE_USER=skala_dw_user
DATABASE_PASSWORD=1234

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

### 3. 환경변수 설명

#### Data Warehouse (DW_*)
- **DW_HOST**: Data Warehouse 호스트 (기본: localhost)
- **DW_PORT**: Data Warehouse 포트 (기본: 5433)
- **DW_NAME**: 데이터베이스 이름
- **DW_USER**: 데이터베이스 사용자
- **DW_PASSWORD**: 데이터베이스 비밀번호

#### Application Database (APP_*)
- **APP_HOST**: Application DB 호스트 (기본: localhost)
- **APP_PORT**: Application DB 포트 (기본: 5432)
- **APP_NAME**: 데이터베이스 이름
- **APP_USER**: 데이터베이스 사용자
- **APP_PASSWORD**: 데이터베이스 비밀번호

#### Legacy Database (DATABASE_*)
- 하위 호환성을 위한 설정
- 기본적으로 Data Warehouse와 동일한 값 사용

#### Scheduler
- **PROBABILITY_SCHEDULE_MONTH**: P(H) 계산 실행 월 (1-12)
- **PROBABILITY_SCHEDULE_DAY**: P(H) 계산 실행 일 (1-31)
- **PROBABILITY_SCHEDULE_HOUR**: P(H) 계산 실행 시 (0-23)
- **PROBABILITY_SCHEDULE_MINUTE**: P(H) 계산 실행 분 (0-59)
- **HAZARD_SCHEDULE_***: Hazard Score 계산 스케줄

#### Performance
- **PARALLEL_WORKERS**: 병렬 처리 워커 수 (CPU 코어 수에 맞춰 조정)
- **BATCH_SIZE**: 배치 처리 크기

---

## 시스템 환경변수 제거

시스템에 DB 관련 환경변수가 설정되어 있다면, 혼란을 방지하기 위해 제거하는 것을 권장합니다.

### Windows (PowerShell)

제공된 스크립트 사용:

```powershell
# 현재 세션에서만 제거 (테스트용)
.\clear_system_env_vars.ps1

# 사용자 레벨에서 영구 제거 (스크립트 내 주석 해제 필요)
# 관리자 권한으로 실행하면 시스템 레벨에서도 제거 가능
```

### Windows (GUI)

1. `Win + Pause/Break` 키 → 고급 시스템 설정
2. 환경 변수 버튼 클릭
3. 사용자/시스템 변수에서 다음 변수 삭제:
   - `DW_HOST`, `DW_PORT`, `DW_NAME`, `DW_USER`, `DW_PASSWORD`
   - `APP_HOST`, `APP_PORT`, `APP_NAME`, `APP_USER`, `APP_PASSWORD`
   - `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`

### Linux/Mac

```bash
# ~/.bashrc 또는 ~/.zshrc 편집
vim ~/.bashrc

# 다음과 같은 줄 제거
# export DW_HOST=localhost
# export DW_PORT=5433
# ...

# 설정 다시 로드
source ~/.bashrc
```

---

## 연결 테스트

### 1. 기본 연결 테스트

```bash
python test_db_connection.py
```

**예상 출력**:
```
=== Data Warehouse Connection Test ===

Environment Variables:
  DW_HOST: localhost
  DW_PORT: 5433
  DW_NAME: skala_datawarehouse
  DW_USER: skala_dw_user
  DW_PASSWORD: ***

Connection URL:
  postgresql://skala_dw_user:***@localhost:5433/skala_datawarehouse

Connection Test:
  SUCCESS: Connected to PostgreSQL
  Version: PostgreSQL 16.4 (Debian 16.4-1.pgdg110+2) on x86_6...

  Sample tables:
    - api_buildings
    - api_coastal_infrastructure
    ...

[OK] Data Warehouse connection successful!
```

### 2. 환경변수 로딩 테스트

```bash
python test_env_simple.py
```

**확인 사항**:
- `.env` 파일에서 값이 올바르게 로드되는지
- 데이터베이스 연결이 성공하는지
- 연결된 데이터베이스와 사용자가 올바른지

### 3. 스키마 확인

```bash
python check_db_schema.py
```

**확인 사항**:
- 데이터베이스에 필요한 테이블들이 존재하는지
- 테이블 구조가 올바른지

---

## 문제 해결

### 문제 1: .env 파일을 찾을 수 없음

**증상**:
```
FileNotFoundError: [Errno 2] No such file or directory: '.env'
```

**해결**:
```bash
# 1. .env 파일이 프로젝트 루트에 있는지 확인
ls -la .env

# 2. 없다면 .env.example 복사
cp .env.example .env

# 3. 내용 편집
vim .env
```

### 문제 2: 환경변수가 로드되지 않음

**증상**:
```python
print(os.getenv('DW_HOST'))  # None
```

**해결**:
```python
# 1. .env 파일 위치 확인
from pathlib import Path
env_path = Path(__file__).parent / ".env"
print(f"Looking for .env at: {env_path}")
print(f"Exists: {env_path.exists()}")

# 2. 명시적으로 load_dotenv 호출
from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path, override=True)

# 3. 확인
print(os.getenv('DW_HOST'))
```

### 문제 3: 시스템 환경변수와 충돌

**증상**:
- .env 파일을 수정해도 값이 변경되지 않음
- 예상과 다른 값이 로드됨

**해결**:
```bash
# 1. 현재 환경변수 확인
python -c "import os; print(os.getenv('DW_HOST'))"

# 2. 시스템 환경변수 제거
# Windows
.\clear_system_env_vars.ps1

# Linux/Mac
unset DW_HOST DW_PORT DW_NAME DW_USER DW_PASSWORD

# 3. 터미널/IDE 재시작

# 4. 다시 확인
python test_env_simple.py
```

### 문제 4: 데이터베이스 연결 실패

**증상**:
```
psycopg2.OperationalError: connection to server at "localhost", port 5433 failed
```

**해결**:
```bash
# 1. 데이터베이스 실행 확인
docker ps | grep postgres

# 2. 포트 확인
netstat -an | grep 5433

# 3. 수동 연결 테스트
psql -h localhost -p 5433 -U skala_dw_user -d skala_datawarehouse

# 4. .env 파일 값 재확인
cat .env | grep DW_
```

### 문제 5: 권한 오류

**증상**:
```
psycopg2.OperationalError: FATAL: password authentication failed
```

**해결**:
```bash
# 1. .env 파일의 비밀번호 확인
cat .env | grep PASSWORD

# 2. 데이터베이스 사용자 확인
docker exec -it skala_datawarehouse psql -U postgres -c "\du"

# 3. 비밀번호 재설정 (필요시)
docker exec -it skala_datawarehouse psql -U postgres -c "ALTER USER skala_dw_user WITH PASSWORD '1234';"
```

---

## 환경별 .env 파일 관리

### 개발 환경

```bash
# .env.dev
DW_HOST=localhost
DW_PORT=5433
DW_PASSWORD=dev_password
PARALLEL_WORKERS=2
```

### 프로덕션 환경

```bash
# .env.prod
DW_HOST=prod-db.example.com
DW_PORT=5433
DW_PASSWORD=prod_secure_password
PARALLEL_WORKERS=8
```

### 사용 방법

```bash
# 개발 환경
cp .env.dev .env

# 프로덕션 환경
cp .env.prod .env

# 또는 환경변수로 지정
python -c "
from dotenv import load_dotenv
load_dotenv('.env.prod')
"
```

---

## 보안 권장사항

### 1. .env 파일 보호

```bash
# .gitignore에 추가 (이미 포함됨)
echo ".env" >> .gitignore

# 파일 권한 제한 (Linux/Mac)
chmod 600 .env
```

### 2. 비밀번호 관리

- **개발 환경**: 간단한 비밀번호 사용 가능
- **프로덕션**: 강력한 비밀번호 사용 (20자 이상, 특수문자 포함)
- **비밀번호 저장소**: HashiCorp Vault, AWS Secrets Manager 등 사용 권장

### 3. 환경변수 검증

```python
# settings.py에서 필수 환경변수 검증
from pydantic import Field

class Settings(BaseSettings):
    dw_password: str = Field(..., min_length=4)  # 최소 4자 이상
```

---

## 참고 자료

### 관련 파일
- [.env.example](.env.example) - 환경변수 템플릿
- [ETL/scripts/db_config.py](ETL/scripts/db_config.py) - DB 연결 설정
- [modelops/config/settings.py](modelops/config/settings.py) - ModelOps 설정
- [clear_system_env_vars.ps1](clear_system_env_vars.ps1) - 환경변수 제거 스크립트

### 테스트 스크립트
- [test_db_connection.py](test_db_connection.py) - 기본 연결 테스트
- [test_env_simple.py](test_env_simple.py) - 환경변수 로딩 테스트
- [check_db_schema.py](check_db_schema.py) - 스키마 확인

---

**최종 수정**: 2025-11-25
**작성자**: SKALA Physical Risk AI Team
