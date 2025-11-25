# Oracle 서버 배포 가이드

GitHub Actions를 통해 Oracle Cloud 서버에 Backend AIops를 자동 배포하는 전체 가이드입니다.

## 📋 목차

1. [배포 아키텍처](#배포-아키텍처)
2. [서버 사전 준비](#서버-사전-준비)
3. [GitHub Secrets 설정](#github-secrets-설정)
4. [배포 플로우](#배포-플로우)
5. [배포 검증](#배포-검증)
6. [운영 가이드](#운영-가이드)
7. [트러블슈팅](#트러블슈팅)

---

## 배포 아키텍처

```
┌─────────────────┐
│  GitHub Actions │
│    (CI/CD)      │
└────────┬────────┘
         │
         │ 1. Push to main
         ▼
┌─────────────────┐
│   CI Workflow   │
│  - Test         │
│  - Build Image  │
│  - Push to GHCR │
└────────┬────────┘
         │
         │ 2. Trigger on success
         ▼
┌─────────────────┐
│   CD Workflow   │
│  - SSH to server│
│  - Pull code    │
│  - Deploy       │
└────────┬────────┘
         │
         │ 3. Deploy
         ▼
┌─────────────────┐
│  Oracle Server  │
│  - Pull image   │
│  - Run container│
└─────────────────┘
```

---

## 서버 사전 준비

### 1. Oracle Cloud 서버 접속

```bash
# SSH Key로 접속
ssh -i ~/.ssh/oracle_key.pem opc@<SERVER_IP>
```

### 2. Docker 설치

```bash
# Docker 설치 (Oracle Linux)
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# Docker 권한 부여
sudo usermod -aG docker opc
newgrp docker

# Docker 설치 확인
docker --version
docker info
```

### 3. Git 설치 및 저장소 클론

```bash
# Git 설치
sudo yum install -y git

# 프로젝트 디렉토리 생성
mkdir -p ~/backend_aiops
cd ~/backend_aiops

# 저장소 클론
git clone https://github.com/your-org/backend_aiops.git .

# 또는 이미 클론된 경우
cd ~/backend_aiops
git pull origin main
```

### 4. 환경 변수 파일 생성

```bash
cd ~/backend_aiops

# .env 파일 생성
nano .env
```

.env 파일 내용 예시는 .env.example 참조

### 5. 스크립트 실행 권한 부여

```bash
chmod +x docker-build.sh
chmod +x docker-deploy.sh
```

### 6. GitHub Container Registry 인증

```bash
# Personal Access Token으로 로그인
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

---

## GitHub Secrets 설정

상세 내용은 GITHUB_SECRETS.md 참조

### 필수 Secrets

| Secret 이름 | 설명 |
|------------|------|
| SERVER_HOST | 서버 IP 또는 도메인 |
| SERVER_USERNAME | SSH 사용자명 (opc) |
| SERVER_SSH_KEY | Private Key 전체 내용 |
| DEPLOY_PATH | 프로젝트 경로 (/home/opc/backend_aiops) |

---

## 배포 플로우

### 자동 배포

1. 로컬에서 코드 수정 및 Push
2. CI Workflow 자동 실행 (Test & Build)
3. CD Workflow 자동 실행 (Deploy)

### 수동 배포

```bash
cd /home/opc/backend_aiops
git pull origin main
./docker-deploy.sh deploy
```

---

## 배포 검증

### GitHub Actions 확인

- CI - Test & Build 워크플로우 성공
- CD - Deploy 워크플로우 성공

### 서버 확인

```bash
docker ps | grep backend-aiops
docker logs backend-aiops
./docker-deploy.sh status
```

---

## 운영 가이드

### 로그 확인

```bash
docker logs -f backend-aiops
docker logs --tail 100 backend-aiops
./docker-deploy.sh logs
```

### 컨테이너 재시작

```bash
docker restart backend-aiops
./docker-deploy.sh deploy
```

### 환경 변수 변경

```bash
nano .env
./docker-deploy.sh deploy
```

---

## 트러블슈팅

### Permission denied 에러

- SSH Key 확인
- authorized_keys 등록 확인

### 컨테이너 즉시 종료

- docker logs 확인
- .env 파일 확인
- 데이터베이스 연결 확인

### 디스크 부족

```bash
df -h
docker system prune -a
```

---

## 참고 링크

- GitHub Actions 문서
- Docker 문서
- GITHUB_SECRETS.md
- LOCAL_CICD_TEST.md
