# Commit Convention

polaris 프로젝트의 Commit Convention 정의

## 1. 목적

- 커밋 메시지 표준화를 통한 변경 이력의 명확한 관리
- 코드 리뷰 효율 향상

## 2. 기본 작성 규칙

```
[type] 파일명_수정내용
```

## 3. 세부 규칙

### 3.1. 필수 준수사항

- [type] 형식으로 시작
- 수정내용은 최대 2문장
- "무엇"을 "왜" 변경했는지 명시
- 마침표 사용 금지
- 명사형으로 마무리
- 언더스코어(*) / 공백 구분 (예: user_service*사용자조회기능)

## 4. Commit Type 정의

커밋 목적을 명확하게 하기 위해 아래 타입을 사용

| Type     | 설명                  | 사용 시점                      |
| -------- | --------------------- | ------------------------------ |
| `add`    | 새로운 파일/기능 추가 | 새 기능, 파일, 모듈 생성 시    |
| `update` | 기존 파일/기능 수정   | 기능 개선, 버그 수정, 리팩토링 |
| `delete` | 파일/기능 삭제        | 불필요한 코드, 파일 제거 시    |

## 5. 작성 예시

### 5.1. 기능 추가

```bash
git commit -m "[add] user_service_사용자조회기능구현"
git commit -m "[add] login_api_JWT기반인증추가"
git commit -m "[add] payment_module_결제기능구현사용자요청반영"
```

### 5.2. 기능 수정

```bash
git commit -m "[update] auth_service_토큰만료시간30분으로변경"
git commit -m "[update] user_model_이메일중복검증추가보안강화위해"
git commit -m "[update] readme_실행방법추가신규개발자온보딩위해"
```

### 5.3. 파일 삭제

```bash
git commit -m "[delete] temp_file_테스트파일제거"
git commit -m "[delete] old_api_미사용API제거코드정리위해"
git commit -m "[delete] deprecated_util_레거시유틸리티제거"
```

### 5.4. 수정내용 작성 가이드

좋은 예시

```
[update] auth_service_토큰만료시간30분으로변경보안강화
[add] payment_api_결제기능구현사용자요청반영
[update] user_validator_이메일형식검증추가입력오류방지
```

나쁜 예시

```
[update] auth_service_수정함.
[add] user_model_추가
[update] config_변경했습니다
[add] 기능 추가
```

## 6. 검토 체크리스트

- [ ] 기본 작성 규칙을 지켰는가
- [ ] [type] 형식을 사용했는가
- [ ] 파일명이 명확한가
- [ ] 수정내용이 명확한가
- [ ] 마침표를 사용하지 않았는가
- [ ] 최대 2문장 이내인가
- [ ] "무엇"을 "왜" 변경했는지 명시했는가
