# 로컬 Docker CI/CD 테스트 가이드

GitHub Actions에 Push하기 전에 로컬 환경에서 Docker 빌드 및 배포를 테스트하는 가이드입니다.

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [로컬 CI 테스트 (빌드 & Push)](#로컬-ci-테스트-빌드--push)
3. [로컬 CD 테스트 (배포)](#로컬-cd-테스트-배포)
4. [전체 CI/CD 플로우 테스트](#전체-cicd-플로우-테스트)
5. [트러블슈팅](#트러블슈팅)

---

## 사전 요구사항

### 1. Docker 설치 확인

```bash
docker --version
# Docker version 24.0.0 이상

docker info
# Docker가 실행 중이어야 함
```

### 2. 환경 변수 파일 준비

`.env.example`을 복사하여 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 편집:
```bash
# Database Configuration
DATABASE_HOST=your_db_host
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

### 3. 스크립트 실행 권한 부여

```bash
chmod +x docker-build.sh
chmod +x docker-deploy.sh
```

---

## 로컬 CI 테스트 (빌드 & Push)

CI 파이프라인은 **Docker 이미지를 빌드하고 GitHub Container Registry(ghcr.io)에 Push**하는 단계입니다.

### 1. 로컬 빌드만 테스트 (Registry Push 없음)

**가장 간단한 테스트 방법:**

```bash
./docker-build.sh local
```

**결과:**
- Docker 이미지가 로컬에 빌드됨
- 이미지 태그: `backend-aiops:latest`
- Registry에 Push하지 않음 (로컬 테스트용)

**확인:**
```bash
docker images | grep backend-aiops
# backend-aiops   latest   abc123def456   2 minutes ago   200MB
```

### 2. CI 전체 플로우 테스트 (Build + Push)

**실제 CI와 동일하게 Registry에 Push까지 테스트:**

#### 2-1. GitHub Container Registry 로그인

```bash
# Personal Access Token 생성 (GitHub)
# Settings → Developer settings → Personal access tokens → Tokens (classic)
# Scope: write:packages, read:packages

# 로그인
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

#### 2-2. 환경 변수 설정

```bash
export REGISTRY="ghcr.io"
export IMAGE_NAME="backend-aiops"
export TAG="local-test"
export GITHUB_REPOSITORY="your-org/backend_aiops"
export GITHUB_SHA="local-$(date +%s)"
export REGISTRY_USERNAME="YOUR_GITHUB_USERNAME"
export REGISTRY_PASSWORD="YOUR_GITHUB_TOKEN"
```

#### 2-3. CI 빌드 실행

```bash
./docker-build.sh ci
```

**결과:**
- Docker 이미지 빌드
- `ghcr.io/your-org/backend_aiops/backend-aiops:local-test` 태그로 Push
- `ghcr.io/your-org/backend_aiops/backend-aiops:latest` 태그로 Push

**확인:**
```bash
# GitHub Packages 페이지에서 확인
# https://github.com/your-org?tab=packages
```

---

## 로컬 CD 테스트 (배포)

CD 파이프라인은 **서버에 Docker 컨테이너를 배포**하는 단계입니다.

### 1. 로컬 배포 테스트

**로컬 머신에서 전체 배포 플로우 테스트:**

```bash
./docker-deploy.sh deploy
```

**실행 순서:**
1. Docker 실행 확인
2. 이미지 빌드 (`backend-aiops:latest`)
3. 기존 컨테이너 중지 및 삭제
4. 새 컨테이너 실행 (`.env` 파일 사용)
5. 컨테이너 상태 확인

**결과:**
```
[INFO] Starting full deployment...
[INFO] Docker is running
[INFO] Building Docker image: backend-aiops...
[INFO] Build completed successfully
[INFO] Stopping existing container: backend-aiops...
[INFO] Container stopped and removed
[INFO] Starting container: backend-aiops...
[INFO] Using environment file: .env
[INFO] Container started
[INFO] Deployment completed successfully!
[INFO] Container backend-aiops is running
CONTAINER ID   STATUS
abc123def456   Up 5 seconds
```

### 2. 개별 명령 테스트

#### 빌드만 실행
```bash
./docker-deploy.sh build
```

#### 컨테이너 중지
```bash
./docker-deploy.sh stop
```

#### 컨테이너 실행
```bash
./docker-deploy.sh run
```

#### 로그 확인
```bash
./docker-deploy.sh logs
```

#### 상태 확인
```bash
./docker-deploy.sh status
```

---

## 전체 CI/CD 플로우 테스트

### 시나리오 1: 로컬 개발 환경 테스트

```bash
# 1. 로컬 빌드 테스트
./docker-build.sh local

# 2. 로컬 배포 테스트
./docker-deploy.sh deploy

# 3. 로그 확인
./docker-deploy.sh logs

# 4. 컨테이너 상태 확인
docker ps | grep backend-aiops
```

### 시나리오 2: CI/CD 전체 시뮬레이션

```bash
# 1. CI 단계: 빌드 & Push
export REGISTRY="ghcr.io"
export REGISTRY_USERNAME="your-username"
export REGISTRY_PASSWORD="your-token"
export GITHUB_REPOSITORY="your-org/backend_aiops"
export GITHUB_SHA="$(git rev-parse HEAD)"
export TAG="$GITHUB_SHA"

./docker-build.sh ci

# 2. CD 단계: 서버 배포 (로컬 시뮬레이션)
./docker-deploy.sh deploy

# 3. 검증
./docker-deploy.sh status
./docker-deploy.sh logs
```

---

## Docker Compose를 사용한 테스트

### docker-compose.yml 생성 (선택사항)

```yaml
version: '3.8'

services:
  backend-aiops:
    build: .
    container_name: backend-aiops
    env_file:
      - .env
    restart: unless-stopped
```

### 실행

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

---

## 테스트 체크리스트

### CI 테스트 체크리스트

- [ ] `./docker-build.sh local` 성공
- [ ] Docker 이미지가 로컬에 생성됨 (`docker images` 확인)
- [ ] 이미지 크기가 적절한가? (500MB 이하 권장)
- [ ] Multi-stage build가 작동하는가?

### CD 테스트 체크리스트

- [ ] `.env` 파일이 존재하는가?
- [ ] `./docker-deploy.sh deploy` 성공
- [ ] 컨테이너가 실행 중인가? (`docker ps` 확인)
- [ ] 로그에 에러가 없는가? (`./docker-deploy.sh logs`)
- [ ] APScheduler가 시작되었는가? (로그 확인)
- [ ] PostgreSQL NOTIFY 리스너가 작동하는가? (로그 확인)

### 통합 테스트 체크리스트

- [ ] 컨테이너가 자동으로 재시작되는가? (`docker restart backend-aiops`)
- [ ] Health check가 정상인가? (`docker inspect backend-aiops`)
- [ ] PostgreSQL 연결이 되는가? (컨테이너 로그 확인)
- [ ] 환경 변수가 제대로 로드되는가?

---

## 트러블슈팅

### 문제 1: 빌드 실패 - "No module named 'modelops'"

**원인:** 프로젝트 구조 또는 `pyproject.toml` 설정 문제

**해결:**
```bash
# pyproject.toml 확인
cat pyproject.toml | grep packages
# 출력: packages = ["modelops"]

# modelops 폴더 존재 확인
ls -la modelops/
```

### 문제 2: 컨테이너 즉시 종료

**원인:** 환경 변수 누락 또는 데이터베이스 연결 실패

**해결:**
```bash
# 로그 확인
docker logs backend-aiops

# .env 파일 확인
cat .env

# 수동으로 컨테이너 실행하여 디버깅
docker run -it --rm --env-file .env backend-aiops:latest python -c "from modelops.config.settings import settings; print(settings)"
```

### 문제 3: "Permission denied" 에러

**원인:** 스크립트 실행 권한 없음

**해결:**
```bash
chmod +x docker-build.sh
chmod +x docker-deploy.sh
```

### 문제 4: PostgreSQL 연결 실패

**원인:** DATABASE_HOST가 `localhost`로 설정되어 있으나 컨테이너에서 접근 불가

**해결:**
```bash
# .env 파일에서 DATABASE_HOST를 Docker 네트워크에서 접근 가능한 주소로 변경
# 예: host.docker.internal (Docker Desktop)
#     172.17.0.1 (Linux)
#     실제 서버 IP (운영 환경)
```

### 문제 5: Registry Push 실패 - "denied: permission denied"

**원인:** GitHub Container Registry 인증 실패

**해결:**
```bash
# 로그아웃 후 재로그인
docker logout ghcr.io

# Personal Access Token 재생성 (write:packages 권한 확인)
echo "NEW_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

---

## 유용한 Docker 명령어

### 이미지 관리

```bash
# 모든 이미지 확인
docker images

# 특정 이미지 삭제
docker rmi backend-aiops:latest

# 사용하지 않는 이미지 정리
docker image prune -a
```

### 컨테이너 관리

```bash
# 실행 중인 컨테이너 확인
docker ps

# 모든 컨테이너 확인 (중지된 것 포함)
docker ps -a

# 컨테이너 로그 실시간 확인
docker logs -f backend-aiops

# 컨테이너 내부 접속
docker exec -it backend-aiops bash

# 컨테이너 재시작
docker restart backend-aiops

# 컨테이너 중지
docker stop backend-aiops

# 컨테이너 삭제
docker rm backend-aiops
```

### 디버깅

```bash
# 컨테이너 상세 정보 확인
docker inspect backend-aiops

# Health check 상태 확인
docker inspect --format='{{.State.Health.Status}}' backend-aiops

# 컨테이너 리소스 사용량 확인
docker stats backend-aiops

# 컨테이너 내부에서 Python 실행
docker exec -it backend-aiops python -c "import sys; print(sys.path)"
```

---

## 다음 단계

로컬 테스트가 완료되었다면:

1. ✅ Git에 커밋 및 Push
2. ✅ GitHub Actions에서 실제 CI/CD 파이프라인 실행
3. ✅ [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) 참조하여 운영 서버 배포

---

## 참고 링크

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Build 가이드](https://docs.docker.com/engine/reference/commandline/build/)
- [Docker Run 가이드](https://docs.docker.com/engine/reference/commandline/run/)
