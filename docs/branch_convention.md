# Branch Convention

polaris 프로젝트의 Branch Convention 정의

## 1. 목적

- 브랜치 이름을 통한 작업 내용과 이슈의 즉시 파악
- 통일된 규칙 적용으로 협업 효율성 향상

## 2. 기본 작성 규칙

```
{유형}/{이슈번호}-{작업명}
```

## 3. 세부 규칙

### 3.1. 필수 준수사항

- 전체 소문자만 사용
- 하이픈(-)으로 단어 구분
- 이슈 번호 반드시 포함
- 3-5 단어 이내 구성
- 슬래시(/) 구분자는 유형과 상세명 사이에만 사용
- 언더스코어(\_) / 공백 / 대문자 / 한글 / 다중 슬래시 사용 금지
- develop 브랜치를 거치지 않은 main PR 금지 (hotfix 제외)

### 3.2. 브랜치 보호 규칙

- 본인의 PR을 본인이 승인할 수 없음
- git reset 명령어 사용 불가
- main 브랜치에 직접 push 불가
- PR 병합 완료 후 작업 브랜치 즉시 삭제

### 3.3. 작업 시간 규칙

- 오전 9시: develop 브랜치 fetch 및 동기화
- 오후 5시 10분: Pull Request 생성
- 단, 빠른 반영이 필요한 경우, 모든 팀원의 동의를 얻은 후 PR 진행

## 4. 브랜치 유형 정의

브랜치 목적을 명확하게 하기 위해 아래 유형을 사용

| 유형       | 설명                            | 분기 기준 |
| ---------- | ------------------------------- | --------- |
| `feature`  | 새로운 기능 개발                | develop   |
| `fix`      | 버그 수정                       | develop   |
| `refactor` | 코드 리팩토링                   | develop   |
| `hotfix`   | 긴급 수정 (배포 후 발견된 버그) | main      |

## 5. 작업 흐름

### 5.1. 일반 작업 흐름 (feature, fix, refactor)

1. develop 브랜치에서 작업 브랜치 생성

   - feature/{이슈번호}-{작업명} 생성

2. 작업 브랜치에서 개발 진행

   - 코드 작성 및 commit

3. develop 브랜치로 PR 생성

   - 코드 리뷰 및 승인

4. develop 브랜치에 병합

   - 작업 브랜치 삭제

5. develop에서 통합 테스트 진행

   - GitActions를 통한 자동 CI 진행

6. develop이 안정화되면 main으로 PR 생성

   - 최종 리뷰 및 승인

7. main 브랜치에 병합
   - 배포

### 5.2. 긴급 수정 흐름 (hotfix)

1. main 브랜치에서 hotfix 브랜치 생성

   - hotfix/{문제명} 생성

2. hotfix 브랜치에서 수정 진행

   - 버그 수정 및 commit

3. main 브랜치로 PR 생성 및 병합

   - 즉시 배포

4. develop 브랜치로도 PR 생성 및 병합

   - develop 동기화

5. hotfix 브랜치 삭제

## 6. 작성 예시

### 6.1. 기능 추가

# develop 브랜치 최신화

```bash
git checkout develop
git pull origin develop
```

# 작업 브랜치 생성

```bash
git checkout -b feature/{이슈번호}-{작업명}
```

# 작업 완료 후 push

```bash
git push origin feature/{이슈번호}-{작업명}
```

**브랜치명 예시**

```bash
feature/12-add-login
feature/34-add-signup
```

### 6.2. 버그 수정

```bash
git checkout develop
git pull origin develop
git checkout -b fix/{이슈번호}-{버그명}
git push origin fix/{이슈번호}-{버그명}
```

**브랜치명 예시**

```bash
fix/23-token-error
fix/45-api-timeout
```

### 6.3. 리팩토링

```bash
git checkout develop
git pull origin develop
git checkout -b refactor/{이슈번호}-{대상}
git push origin refactor/{이슈번호}-{대상}
```

**브랜치명 예시**

```bash
refactor/56-user-service
refactor/78-auth-logic
```

### 6.4. 긴급 수정

```bash
git checkout main
git pull origin main
git checkout -b hotfix/{문제명}
git push origin hotfix/{문제명}
```

**브랜치명 예시**

```bash
hotfix/login-crash
hotfix/payment-error
```

## 7. 검토 체크리스트

- [ ] 기본 작성 규칙을 지켰는가
- [ ] 이슈가 먼저 생성되었는가
- [ ] 브랜치명에 이슈 번호가 포함되었는가
- [ ] 모든 문자가 소문자인가
- [ ] 하이픈으로만 구분했는가
- [ ] 정해진 유형에서 사용하였는가
- [ ] 3-5 단어 이내인가
- [ ] 슬래시를 중복 사용하지 않았는가
- [ ] develop에서 분기했는가 (hotfix는 main에서 분기)
- [ ] 업로드 전 브랜치를 확인했는가
- [ ] PR 시간(17:10)을 준수했는가
- [ ] PR에 관련 이슈 번호를 연결했는가
