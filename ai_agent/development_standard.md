# 🧭 [산출물] 개발 표준 정의 (Software Development Standard)

---

## 1. 문서 저장 규칙

- 문장 한 줄 작성 후 `Ctrl + S` 로 저장

---

## 2. Git 규칙

### 2.1 Main Branch 규칙

1. 본인의 Pull Request(PR)는 본인이 수락할 수 없다.  
2. `git reset` 명령어 사용 금지  

#### GitHub Settings
- Repository → Settings → Branch Protection Rules 에서 다음 두 옵션 설정:
  - 본인 PR 승인 불가
  - Force Push 금지

#### 업무 관련 시간 규칙
- **PR 시간:** 17시 10분  
- **Fetch 시간 (Pull):** 09시

---

### 2.2 Commit 규칙

- 1일 1 commit 필수  
- `.gitignore` 파일 관리 필수  
- 파일 단위로 commit (`git add .` 금지)

#### Commit Message 규칙
\`\`\`bash
git commit -m "[add/update/delete] 파일명_버전_수정내용"
\`\`\`

- `[3중 택1]`: `add` / `update` / `delete`
- 예시: `[update] readme_v02_파일구조추가`
- 상세 부분 작성:
  - 최대 2문장  
  - “무엇”을 “왜” 변경했는지 설명  
  - 마침표(`.`) 사용 금지  
- 파일 버전 형식: `v00`  
- 업로드 전 타 브랜치 확인 필수

---

### 2.3 README 관리 규칙

- `README.md` 파일은 **백엔드 / 프론트엔드 / 에이전트**별로 관리
- `docs/` 폴더 내에 README 파일 배치
- **Main 브랜치:** 전체 프로젝트 개요  
- **Backend 브랜치:** 백엔드 구조, 데이터 흐름 등 세부 설명

#### README 구성 예시

| 구분 | 내용 |
|------|------|
| Backend | flow, input(+데이터 스키마), process(+주요 함수), output(+데이터 스키마), 에이전트 별 라이브러리 |
| Main | 프로젝트 명, 설명, 목차, 실행방법, 디렉토리 구조 |
| 참고 | `polaris_backend`의 README 참고 |

---

## 3. 코드 구조 및 규칙

- Agent는 tool로 분리 후 annotation 사용  
- Tool, prompt는 별도 디렉토리로 관리  
- Python 함수에는 반드시 `@데코레이터`(tool) 적용  
- 공통 util은 별도의 `utils` 폴더로 관리  

---

## 4. 주석 규칙 (Python 기준)

- **Docstring 형태로 상세 주석 작성 (`''' '''`)**
- 파일 상단에 개요, 최종 수정일, 파일 버전 명시  

예시:
\`\`\`python
'''
파일명: auth_service.py
최종 수정일: 2025-11-04
버전: v00
파일 개요: 사용자 인증 관련 기능 처리
'''
\`\`\`

- 함수 간 연관(import, 호출)은 docstring 안에 호출 파일명 명시  
- 예시:
\`\`\`python
def divide(a: float, b: float) -> float:
    """
    두 수를 나눈 값을 반환합니다.

    Args:
        a: 피제수
        b: 제수

    Returns:
        나눗셈 결과

    Raises:
        ZeroDivisionError: b가 0일 때
    """
    return a / b
\`\`\`

---

## 5. 들여쓰기 및 코드 스타일

- **Tab 사용 (공백 금지)**  
  - Tab 1번 = 4칸  
  - Tab 2번 = 8칸
- 한 줄 최대 160자
- 삼항 연산자 (`a if b else c`) 사용 금지
- Python 기호 연산자 대신 문자 연산자 사용
- `True → False` 순서 유지 (`not` 지양)
- 연산자(+, -, =, ,) 주변은 space 삽입
- 문자열과 숫자 변수 혼합 시 f-string 사용

\`\`\`python
result1 = f"저는 {s}를 좋아합니다. 하루 {n}잔 마셔요"
\`\`\`

- 큰따옴표: 문장용  
- 작은따옴표: 단어용
- 괄호 규칙:
  - `((내용) and (내용))` — 이중 괄호는 붙여쓰기
  - 함수 괄호는 공백 없이 붙이기 (`func()`)
  - 인자가 없을 때도 괄호 붙이기 `()`

---

## 6. 명명 규칙

| 구분 | 스타일 | 예시 | 비고 |
|------|---------|------|------|
| 패키지(폴더) | snake_case | auth_service | 전부 소문자 |
| 모듈(파일) | snake_case | auth_controller.py | 클래스 기반 이름 |
| 클래스명 | PascalCase | AuthService | 각 단어 대문자 시작 |
| 함수명 | snake_case | get_user_list() | 명령형 권장 |
| 변수명 | snake_case | user_name | 짧고 명확하게 |
| 상수 | UPPER_CASE | DEFAULT_PAGE_SIZE | 불변 값 |
| 환경변수 | UPPER_CASE | DATABASE_URL | _로 구분 |

---

## 7. 로깅 규칙 (Logging Standard)

- 로그는 `debug`, `info`, `warn`, `error`, `fatal` 로 구분  
- 로그 레벨은 `.env` 파일에서 환경변수로 관리  

### 7.1 공통 로깅 구조

\`\`\`
app/
 ├── core/
 │    ├── logger.py          # 공통 로깅 설정
 │    ├── secure_logger.py   # 보안 로깅 처리
\`\`\`

### 7.2 로깅 기본 설정 예시 (`app/core/logger.py`)

\`\`\`python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger():
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
    )

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
\`\`\`

### 7.3 로그 레벨 정의

| 레벨 | 의미 | 사용 예시 |
|------|------|-----------|
| DEBUG | 개발 중 상세 진단 | `logger.debug("Cache miss for key: %s", key)` |
| INFO | 정상 동작, 처리 로그 | `logger.info("User %s logged in", user_id)` |
| WARNING | 잠재적 문제 | `logger.warning("Slow query detected: %s", query)` |
| ERROR | 예외 발생 | `logger.error("Payment failed: %s", e, exc_info=True)` |
| CRITICAL | 시스템 중단 위험 | `logger.critical("Database connection lost!")` |

### 7.4 예외 처리 시 로깅 예시
\`\`\`python
def process_payment():
    try:
        # business logic
        ...
    except Exception as e:
        if logger.isEnabledFor(logging.ERROR):
            logger.error("Payment processing failed: %s", str(e), exc_info=True)
        raise
\`\`\`

---

### 7.5 기본 로그 항목

| 항목명 | 예시 값 | 설명 | 비고 |
|--------|----------|------|------|
| timestamp | 2025-11-04 10:25:12 | 로그 발생 시각 | 필수 |
| level | INFO | 로그 레벨 | 필수 |
| module | app.fc.fcd.fcdb.service.auth_service | 로그 모듈 | 필수 |
| function | save_auth | 함수명 | 필수 |
| line | 45 | 코드 라인 | 필수 |
| message | Auth record saved successfully | 로그 메시지 | 필수 |
| user_id | kimjs | 요청자 ID | 선택 |
| request_id | req-20251104-abc123 | 추적 ID | 선택 |

#### 로그 예시
\`\`\`
2025-11-04 10:25:12 | INFO | app.fc.fcd.fcdb.service.auth_service | save_auth:45 | user=kimjs | req=req-20251104-abc123 | Auth record saved successfully (id=102)
\`\`\`

---

### 7.6 예외 로그 항목

| 항목명 | 예시 값 | 설명 |
|--------|----------|------|
| timestamp | 2025-11-04 10:45:10 | 예외 발생 시각 |
| level | ERROR | 로그 레벨 |
| module | app.fc.fcd.fcdb.service.auth_service | 예외 모듈 |
| function | delete_auth | 예외 함수 |
| line | 77 | 코드 라인 |
| error_code | E_AUTH_001 | 에러 코드 |
| message | Auth record not found | 에러 메시지 |
| exception_type | ValueError | 예외 클래스명 |
| stack_trace | traceback 내용 | 예외 상세 |
| user_id | kimjs | 선택 |
| request_id | req-20251104-xyz987 | 선택 |

#### 예외 로그 예시
\`\`\`
2025-11-04 10:45:10 | ERROR | app.fc.fcd.fcdb.service.auth_service | delete_auth:77 | [E_AUTH_001] Auth record not found | user=kimjs | req=req-20251104-xyz987
Traceback (most recent call last):
  File "/app/fc/fcd/fcdb/service/auth_service.py", line 75, in delete_auth
    raise ValueError("Auth record not found")
ValueError: Auth record not found
\`\`\`

---

## 8. 세션 관리

- 로그인 세션 구현 시 별도 논의 예정

---

## 9. 차트 표준

- 시각화(Chart) 표현 방식은 추후 협의 및 표준화 예정

---

## 10. 보안 규칙

- Python 템플릿 기반 구현  
- `docstring` 문장은 마침표 없이 명사로 마무리  
- 모든 변수 주석 필요  
  - 코드 + space + `#` + space + 주석  
  - 예시: `for i in range(5):  # 반복문 설명`
- 제어문은 한 문장으로 설명
- 함수는 의미 단위로 개행, 한 줄당 한 문장 작성

---

## 11. 데이터 관리 규칙

- 데이터 파일명 및 폴더명은 **반드시 영어**로 지정
- CSV 파일 표준화 및 구조화는 추후 논의 예정

---

## 12. Q&A 및 용어

- `environment` → `env`
- 명확한 약어가 없으면 풀네임 영어 사용
- `esg`는 그대로 표기
- 로그는 `debug`, `info`, `warn`, `error`로 구분  
- 로그 레벨: `debug < info < warn < error < fatal`

---

_최종 수정일: 2025-11-04_
