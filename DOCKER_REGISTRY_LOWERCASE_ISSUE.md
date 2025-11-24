# Docker Registry 대문자 이슈 해결 가이드

## 문제 상황

GitHub Container Registry (ghcr.io) 또는 다른 Docker 레지스트리에 이미지를 push할 때 다음과 같은 오류가 발생할 수 있습니다:

```
ERROR: failed to build: invalid tag "ghcr.io/On-Do-Polaris/project-name/image:tag":
repository name must be lowercase
```

## 원인

Docker 레지스트리는 **이미지 이름(repository name)을 소문자로만 허용**합니다. 하지만 GitHub 저장소 owner나 organization 이름에 대문자가 포함되어 있으면 이 문제가 발생합니다.

### 예시

```bash
# GitHub 저장소
https://github.com/On-Do-Polaris/polaris_backend_aiops
                    ^^^^^^^^^^^^^ (대문자 포함)

# Docker 이미지 태그 (문제 발생)
ghcr.io/On-Do-Polaris/polaris_backend_aiops/backend-aiops:tag
        ^^^^^^^^^^^^^ (대문자가 포함되어 있어 오류)
```

## 해결 방법

Docker 이미지 빌드 스크립트에서 레포지토리 이름을 **소문자로 변환**해야 합니다.

### Shell Script에서 변환

bash의 `tr` 명령어를 사용하여 대문자를 소문자로 변환합니다:

```bash
local repo_lower=$(echo "${GITHUB_REPOSITORY:-local}" | tr '[:upper:]' '[:lower:]')
```

### 전체 예시

#### 수정 전 (오류 발생)

```bash
build() {
    local full_image="${REGISTRY}/${GITHUB_REPOSITORY}/${IMAGE_NAME}:${TAG}"

    docker build \
        --tag "${full_image}" \
        --tag "${REGISTRY}/${GITHUB_REPOSITORY}/${IMAGE_NAME}:latest" \
        .
}
```

#### 수정 후 (정상 동작)

```bash
build() {
    # 레포지토리 이름을 소문자로 변환
    local repo_lower=$(echo "${GITHUB_REPOSITORY:-local}" | tr '[:upper:]' '[:lower:]')
    local full_image="${REGISTRY}/${repo_lower}/${IMAGE_NAME}:${TAG}"

    docker build \
        --tag "${full_image}" \
        --tag "${REGISTRY}/${repo_lower}/${IMAGE_NAME}:latest" \
        .
}
```

## GitHub Actions에서 적용

GitHub Actions에서 환경변수로 제공되는 `GITHUB_REPOSITORY`는 대소문자를 유지하므로, 이를 소문자로 변환해야 합니다.

### 방법 1: Shell 스크립트 사용 (권장)

빌드 스크립트 내에서 변환:

```bash
#!/bin/bash
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-local}"
REPO_LOWER=$(echo "$GITHUB_REPOSITORY" | tr '[:upper:]' '[:lower:]')

docker build -t "ghcr.io/${REPO_LOWER}/image:tag" .
docker push "ghcr.io/${REPO_LOWER}/image:tag"
```

### 방법 2: GitHub Actions에서 직접 변환

`.github/workflows/ci.yaml`:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Set lowercase repository name
        id: repo
        run: echo "repo_lower=$(echo ${{ github.repository }} | tr '[:upper:]' '[:lower:]')" >> $GITHUB_OUTPUT

      - name: Build Docker image
        run: |
          docker build -t ghcr.io/${{ steps.repo.outputs.repo_lower }}/image:tag .
          docker push ghcr.io/${{ steps.repo.outputs.repo_lower }}/image:tag
```

## 다른 언어/도구에서의 변환

### Python

```python
import os

github_repo = os.environ.get('GITHUB_REPOSITORY', 'local')
repo_lower = github_repo.lower()
image_tag = f"ghcr.io/{repo_lower}/image:tag"
```

### JavaScript/Node.js

```javascript
const githubRepo = process.env.GITHUB_REPOSITORY || 'local';
const repoLower = githubRepo.toLowerCase();
const imageTag = `ghcr.io/${repoLower}/image:tag`;
```

### Makefile

```makefile
GITHUB_REPOSITORY ?= local
REPO_LOWER := $(shell echo $(GITHUB_REPOSITORY) | tr '[:upper:]' '[:lower:]')

build:
	docker build -t ghcr.io/$(REPO_LOWER)/image:tag .
```

## 주의사항

### 1. GitHub 저장소 이름은 그대로 유지

Docker 이미지 이름만 소문자로 변환되며, **실제 GitHub 저장소 이름은 변경되지 않습니다**.

```
실제 GitHub: On-Do-Polaris/project-name (대문자 유지)
Docker 이미지: on-do-polaris/project-name (소문자 변환)
```

### 2. Label과 Metadata

Docker 이미지의 label이나 metadata에는 원본 GitHub 저장소 URL을 사용할 수 있습니다:

```bash
docker build \
    --tag "ghcr.io/${repo_lower}/image:tag" \
    --label "org.opencontainers.image.source=https://github.com/${GITHUB_REPOSITORY}" \
    .
```

label은 이미지 이름이 아니므로 대소문자 제약이 없습니다.

### 3. 모든 곳에서 일관성 유지

빌드, push, pull 시 모두 동일한 소문자 변환 로직을 적용해야 합니다:

```bash
# 빌드 시
docker build -t ghcr.io/${repo_lower}/image:tag .

# Push 시
docker push ghcr.io/${repo_lower}/image:tag

# Pull 시
docker pull ghcr.io/${repo_lower}/image:tag
```

## 검증 방법

### 로컬에서 테스트

```bash
# 환경변수 설정
export GITHUB_REPOSITORY="On-Do-Polaris/project-name"

# 변환 확인
echo $GITHUB_REPOSITORY | tr '[:upper:]' '[:lower:]'
# 출력: on-do-polaris/project-name

# 빌드 테스트
./docker-build.sh local
```

### CI에서 확인

GitHub Actions 로그에서 다음을 확인:

```
[INFO] Building Docker image: ghcr.io/on-do-polaris/project-name/image:abc123
                                      ^^^^^^^^^^^^^^^^^^^^^^^^ (모두 소문자)
```

## 관련 레퍼런스

- [Docker Official Docs - Naming Convention](https://docs.docker.com/engine/reference/commandline/tag/#extended-description)
- [OCI Distribution Spec - Repository Names](https://github.com/opencontainers/distribution-spec/blob/main/spec.md#pull)
- [GitHub Packages - Publishing Docker Images](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## 요약

| 항목 | 설명 |
|------|------|
| **문제** | Docker 레지스트리는 이미지 이름에 대문자를 허용하지 않음 |
| **원인** | GitHub 저장소 owner/org 이름에 대문자 포함 |
| **해결** | `tr '[:upper:]' '[:lower:]'`로 소문자 변환 |
| **영향 범위** | Docker 이미지 이름만 (GitHub 저장소 이름은 유지) |
| **적용 위치** | 빌드, push, pull 모든 곳에서 일관되게 적용 |
