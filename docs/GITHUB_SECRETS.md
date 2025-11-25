# GitHub Secrets 설정 가이드

Backend AIops 프로젝트의 CI/CD 파이프라인에 필요한 GitHub Secrets 설정 가이드입니다.

## 📋 목차

1. [CI (Continuous Integration) Secrets](#ci-continuous-integration-secrets)
2. [CD (Continuous Deployment) Secrets](#cd-continuous-deployment-secrets)
3. [Secrets 설정 방법](#secrets-설정-방법)
4. [검증 방법](#검증-방법)

---

## CI (Continuous Integration) Secrets

CI 워크플로우는 **자동으로 제공되는 `GITHUB_TOKEN`**을 사용하므로 **추가 설정이 필요 없습니다**.

### 자동 제공되는 Secret

| Secret 이름 | 설명 | 제공 방식 |
|------------|------|----------|
| `GITHUB_TOKEN` | GitHub Container Registry (ghcr.io) 인증용 토큰 | GitHub Actions가 자동 생성 |

**✅ CI 단계에서는 별도로 설정할 Secret이 없습니다!**

---

## CD (Continuous Deployment) Secrets

CD 워크플로우는 Oracle 서버에 SSH로 접속하여 배포하므로 **다음 4개의 Secret을 반드시 설정**해야 합니다.

### 필수 Secrets

| Secret 이름 | 설명 | 예시 | 필수 여부 |
|------------|------|------|----------|
| `SERVER_HOST` | 배포 대상 서버의 IP 주소 또는 도메인 | `192.168.1.100` 또는 `server.example.com` | ✅ 필수 |
| `SERVER_USERNAME` | 서버 SSH 접속 사용자명 | `ubuntu`, `opc`, `root` 등 | ✅ 필수 |
| `SERVER_SSH_KEY` | SSH 개인 키 (Private Key) 전체 내용 | `-----BEGIN OPENSSH PRIVATE KEY-----...` | ✅ 필수 |
| `DEPLOY_PATH` | 서버에서 프로젝트가 위치한 절대 경로 | `/home/ubuntu/backend_aiops` | ✅ 필수 |

### 선택 Secrets

| Secret 이름 | 설명 | 기본값 | 필수 여부 |
|------------|------|--------|----------|
| `SERVER_PORT` | SSH 접속 포트 | `22` | ⚪ 선택 (기본 22 포트 사용) |

---

## Secrets 설정 방법

### 1. GitHub Repository 페이지 접속

1. GitHub에서 `backend_aiops` 저장소로 이동
2. **Settings** 탭 클릭
3. 왼쪽 메뉴에서 **Secrets and variables** → **Actions** 클릭

### 2. Secret 추가

#### `SERVER_HOST` 설정

```
Name: SERVER_HOST
Value: <서버 IP 또는 도메인>
```

**예시:**
```
192.168.1.100
```
또는
```
oracle-server.example.com
```

---

#### `SERVER_USERNAME` 설정

```
Name: SERVER_USERNAME
Value: <SSH 접속 사용자명>
```

**예시:**
```
opc
```
(Oracle Cloud는 일반적으로 `opc` 사용자 사용)

---

#### `SERVER_SSH_KEY` 설정

```
Name: SERVER_SSH_KEY
Value: <SSH Private Key 전체 내용>
```

**Private Key 가져오기:**

1. **로컬에서 Private Key 확인:**
   ```bash
   cat ~/.ssh/id_rsa
   # 또는
   cat ~/.ssh/oracle_key.pem
   ```

2. **전체 내용을 복사하여 붙여넣기:**
   ```
   -----BEGIN OPENSSH PRIVATE KEY-----
   b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
   ...
   (전체 키 내용)
   ...
   -----END OPENSSH PRIVATE KEY-----
   ```

**⚠️ 주의사항:**
- **전체 내용**을 복사해야 합니다 (`-----BEGIN` ~ `-----END` 포함)
- 줄바꿈 포함하여 **원본 그대로** 복사
- Public Key(`.pub`)가 아닌 **Private Key** 사용

---

#### `DEPLOY_PATH` 설정

```
Name: DEPLOY_PATH
Value: <서버의 프로젝트 절대 경로>
```

**예시:**
```
/home/opc/backend_aiops
```

**서버에서 경로 확인 방법:**
```bash
# 서버에 SSH 접속 후
cd backend_aiops
pwd
# 출력: /home/opc/backend_aiops (이 값을 사용)
```

---

#### `SERVER_PORT` 설정 (선택사항)

```
Name: SERVER_PORT
Value: <SSH 포트 번호>
```

**예시:**
```
22
```
(대부분의 경우 기본값 22 사용하므로 설정 불필요)

---

## 검증 방법

### 1. Secret 설정 확인

GitHub Repository → **Settings** → **Secrets and variables** → **Actions**에서 다음 Secret들이 표시되는지 확인:

```
✅ SERVER_HOST
✅ SERVER_USERNAME
✅ SERVER_SSH_KEY
✅ DEPLOY_PATH
⚪ SERVER_PORT (선택)
```

### 2. SSH 접속 테스트 (로컬에서)

Secret 설정 전에 로컬에서 SSH 접속이 되는지 테스트:

```bash
ssh -i ~/.ssh/oracle_key.pem opc@192.168.1.100
```

성공적으로 접속되면 Secret 설정 준비 완료!

### 3. GitHub Actions 실행 테스트

1. `main` 브랜치에 커밋 Push
2. **Actions** 탭에서 워크플로우 실행 확인
3. CD 워크플로우의 "Deploy to Server" 단계가 성공하는지 확인

---

## 전체 Secret 요약

### CI 단계 (자동 제공)
```yaml
✅ GITHUB_TOKEN (자동)
```

### CD 단계 (수동 설정 필요)
```yaml
✅ SERVER_HOST         # 예: 192.168.1.100
✅ SERVER_USERNAME     # 예: opc
✅ SERVER_SSH_KEY      # Private Key 전체 내용
✅ DEPLOY_PATH         # 예: /home/opc/backend_aiops
⚪ SERVER_PORT         # 기본값: 22 (선택)
```

---

## 트러블슈팅

### 문제 1: "Permission denied (publickey)" 에러

**원인:** SSH Key가 잘못되었거나 서버에 Public Key가 등록되지 않음

**해결:**
1. 서버의 `~/.ssh/authorized_keys`에 Public Key가 등록되어 있는지 확인
2. Private Key가 정확한지 확인 (`-----BEGIN` ~ `-----END` 포함)

### 문제 2: "Host key verification failed" 에러

**원인:** 서버의 Host Key가 GitHub Actions에 등록되지 않음

**해결:**
CD 워크플로우 파일에 `StrictHostKeyChecking=no` 옵션 추가:
```yaml
script: |
  export StrictHostKeyChecking=no
  cd ${{ secrets.DEPLOY_PATH }}
  ...
```

### 문제 3: "No such file or directory" 에러

**원인:** `DEPLOY_PATH`가 잘못되었거나 서버에 디렉토리가 없음

**해결:**
1. 서버에 SSH 접속하여 디렉토리 확인
2. 없다면 생성:
   ```bash
   mkdir -p /home/opc/backend_aiops
   cd /home/opc/backend_aiops
   git clone https://github.com/your-org/backend_aiops.git .
   ```

---

## 참고 링크

- [GitHub Actions Secrets 공식 문서](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [SSH Action 문서](https://github.com/appleboy/ssh-action)
- [Docker Login Action 문서](https://github.com/docker/login-action)
