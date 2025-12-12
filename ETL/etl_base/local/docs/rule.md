[산출물] 개발표준정의아키텍처 표준
https://docs.google.com/spreadsheets/d/1cMlVfxctMykpoqy7UV5XLHUhtD733Q3A6uw1E87aslQ/edit?usp=sharing





(지라 관련 추가 필요 rule 초안) - 깃허브 커밋 시 지라의 키 값을 commit의 message에 추가하여 커밋하기

* 우측에 개발→ 커밋 만들기→ 키 복사 보면 키 값이 있는데 커밋할때,
* 내용에 저 키 값이 포함되면 자동으로 지라의 태스크랑 연결 되는 것 같습니다!
* 그래서 저희 커밋 문구 규칙을 저걸 포함하도록 수정하면 좋을 것 같습니다~


쿼리 실행계획
이슈 단위 커밋 및 관리


1. 문장 한 줄 작성 후 ctrl+s

2. git 규칙

2.1. [main branch]

1. 본인의 pull request는 본인이 수락할 수 없다.
2. git reset 명령어 사용 금지


깃허브 - settings
옵션으로 2가지 룰 선택

[업무]

* PR 시간 : 17시 10분



* fetch 시간(=pull하는 시간) : 09시

2.2 [commit]

* 1일 1 commit 필수
* .gitignore 관리
* 파일 단위로 나누어 commit (git add . 금지)
* commit message 규칙 (git commit -m "내용")
    * [add추가/update업데이트/delete삭제] '수정사항' 
        * [3중 택1] 파일명_파일버전_수정내용(상세)
            * ex) [update] readme_v02_파일구조추가
        * 상세 부분 작성 방법
            * 최대 2문장, "무엇"을 "왜" 변경했는지 설명, 마침표를 사용하지 않음
    * 파일버전 형식 v00
        * 업로드 전 타 브랜치 확인

2.3. [README]

* README.md 파일 관리 - 백엔드/프론트엔드/ 에이전트 별로도 브랜치 구분 시 readme
    * docs 폴더 안 README 파일 관리
    * main에서는 백엔드 전체 그림
    * 내용
        * 백엔드 : flow, input(+데이터스키마), process(+주요함수설명), output(+데이터스키마), 에이전트 별 필요한 라이브러리
        * main : 프로젝트 명, 설명, 목차, 실행방법, 디렉토리 구조
        * 참고 : polaris_backend의 readme

3. 코드 규칙

* Agent는 tool로 분리한 후 annotation
* 툴, prompt는 디렉토리로 빼서 관리
* python @(데코레이션) tool 달아주기
* 공통 util로 빼서 관리


<주석규칙> = 파이썬 기준

* docstring 형태 주석 작성 (상세)
* ''' ''' - 파일 제일 윗단에 해당 코드에 대한 개요 작성
* 최종 수정일 작성 (예) 2025-11-04)
* 파일 버전 작성 (예) v00)
* 함수 import 연관 호출 - 함수 docstring안에 호출 파일명을 작성
    * 예) 해당 함수가 다른 파일에 어디에서 어떻게 쓰이고 있는지 확인할 수 있도록


들여쓰기

* tab 사용
    * tab 1번 4카
    * tab 2번 8칸
* 한 Line 160문자 내에서 작성
* 4칸, 8칸 단위로 사용
* : ? 삼중연산자 금지
* python 기호연산자 대신 문자 연산자 사용
* true → false 순서로 작성, not 지양
* a in, list - ??????
* 연산자(, +, -, = )들은 모두 space로 구분
    * semicolon, comma, 예약어 뒤에는 space를 둔다
* 문자와 숫자 변수 혼합 사용 시 fstring 
    * 예)result1 = f"저는 { s }를 좋아합니다. 하루 { n }잔 마셔요."
* 큰따옴표 - 문장에 사용, 작은따옴표 - 단어에 사용



* 괄호 앞 뒤는 붙이고, 매개변수는 space로 구분


* ((내용)) - 이중 괄호는 붙여쓰기
    * ((내용) and (내용))
* 함수(  ) - 붙여쓰기
* 인자가 없을 때 괄호 붙여쓰기 ()


<용어>

* environment = env
* esg
* 명확한 약어가 없으면 줄이는 것보다 풀어서 영어로 변수, 함수명



<프론트>

* UI - vue.js따라


<presentation>

* 통신, api


<개발 표준>
log는 debug, info, warn, error로 구별하여 사용한다.(로그레벨은 debug < info < warn < error < fatal)

<로그>

* 로그 레벨은 .env 파일에서 환경변수로 관리
* logging표준 = 어떻게 로그를 남길지 
    * 날짜, 시간, 내용, 등 템플릿

app/
 ├── core/
 │    ├── logger.py          # 공통 로깅 설정
 │    ├── secure_logger.py   # 보안 로깅 처리

항목
	기준

로깅 라이브러리
	Python 표준 logging 모듈 사용 (필요 시 loguru 병행 가능)

패턴
	SLF4J의 façade 패턴과 동일하게, 각 모듈에서 logger = logging.getLogger(__name__) 방식 사용

로거 생성 위치
	각 모듈(파일) 단위로 별도 로거 정의

출력 포맷
	1줄 로그 표준 (시간, 레벨, 모듈, 함수명, 메시지)

로그 레벨 구분
	DEBUG < INFO < WARNING < ERROR < CRITICAL

성능 최적화
	로그 출력 전 if logger.isEnabledFor(logging.DEBUG): 조건문으로 레벨 체크 수행

보안 로그 분리
	개인정보, 주요 거래 행위 등은 별도 “보안 로깅” 처리기로 분리

SQL 로그 분리
	ORM(SQLAlchemy)의 SQL 실행 로그는 별도 핸들러에서 관리


 app/core/logger.py -> 아래 코드로 
 
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

    # SQLAlchemy 등 외부 로그 레벨 조정
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

로그 레벨 사용 규칙

구분
	사용 시점
	예시 코드

DEBUG
	개발 중 상세 진단
	logger.debug("Redis cache miss: %s", key)

INFO
	정상 동작 기록, 주요 처리 시작/완료
	logger.info("User %s logged in", user_id)

WARNING
	잠재적 문제, 재시도 가능 이벤트
	logger.warning("Slow query detected: %s", query)

ERROR
	예외 발생, 실패 처리
	logger.error("Payment failed: %s", e, exc_info=True)

CRITICAL
	시스템 중단 위험, 긴급 대응 필요
	logger.critical("Database connection lost!")


예외 발생 시 로깅

import logging

logger = logging.getLogger(__name__)

def process_payment():
    try:
        # business logic
        ...
    except Exception as e:
        if logger.isEnabledFor(logging.ERROR):
            logger.error("Payment processing failed: %s", str(e), exc_info=True)
        raise  # 예외는 상위 계층으로 전달

로그 요약

항목
	Python 표준

기본 라이브러리
	logging

로거 이름
	__name__

포맷
	`시간

레벨
	DEBUG, INFO, WARNING, ERROR, CRITICAL

보안 로그 분리
	secure_logger

성능 체크
	logger.isEnabledFor()

예외 로깅
	exc_info=True

SQL 로그 관리
	sqlalchemy.engine 로거 사용



기본 로깅 항목

항목명
	예시 값
	설명
	비고

timestamp
	2025-11-04 10:25:12
	로그 발생 시각 (%Y-%m-%d %H:%M:%S)
	필수

level
	INFO / DEBUG / WARNING / ERROR / CRITICAL
	로그 레벨
	필수

module
	app.fc.fcd.fcdb.service.auth_service
	로그가 발생한 모듈 경로
	필수

function
	save_auth
	로그가 발생한 함수명
	필수

line
	45
	로그가 발생한 코드 라인 번호
	필수

message
	"Auth record saved successfully (id=102)"
	실제 로그 메시지
	필수

elapsed_ms
	35
	(선택) 처리 시간(ms 단위)
	성능 모니터링용

request_id
	req-20251104-abc123
	(선택) API 호출 단위 추적 ID
	분산 트레이싱용

user_id
	kimjs
	(선택) 요청자 식별 ID
	인증/보안 로그 연계

client_ip
	10.10.1.42
	(선택) 요청자 IP
	웹 요청 시 필수

service_name
	AuthService
	(선택) 서비스 이름
	모듈 구분용

env
	dev / prod
	(선택) 실행 환경
	로그 라우팅 구분용


로깅 포맷 예시

2025-11-04 10:25:12 | INFO | app.fc.fcd.fcdb.service.auth_service | save_auth:45 | user=kimjs | req=req-20251104-abc123 | Auth record saved successfully (id=102)


예외 로그 항목

항목명
	예시 값
	설명
	비고

timestamp
	2025-11-04 10:45:10
	예외 발생 시각
	필수

level
	ERROR
	로그 레벨
	필수

module
	app.fc.fcd.fcdb.service.auth_service
	예외 발생 모듈
	필수

function
	delete_auth
	예외 발생 함수
	필수

line
	77
	예외 발생 코드라인
	필수

error_code
	E_AUTH_001
	비즈니스 정의 에러코드
	필수

message
	"Auth record not found"
	에러 요약 메시지
	필수

exception_type
	ValueError
	발생 예외 클래스명
	필수

stack_trace
	(traceback 내용)
	Stack Trace 전체
	필수

user_id
	kimjs
	(선택) 사용자 ID
	선택

request_id
	req-20251104-xyz987
	(선택) 요청 추적 ID
	선택



예외 로그

2025-11-04 10:45:10 | ERROR | app.fc.fcd.fcdb.service.auth_service | delete_auth:77 | [E_AUTH_001] Auth record not found | user=kimjs | req=req-20251104-xyz987
Traceback (most recent call last):
  File "/app/fc/fcd/fcdb/service/auth_service.py", line 75, in delete_auth
    raise ValueError("Auth record not found")
ValueError: Auth record not found


<세션>

* 로그인 세션 구현 시 추가 논의


<chart 표준>

* 차트를 어떻게 그릴지 추가 고민



<보안>

* 파이썬 템플릿



docstring = ''' '''

* .을 사용하지 않고 명사로 마무리
* 모든 변수 주석 필요 (# 추가, 해당 줄 옆에)
    * 코드(space)#(space)주석 작성
    * 예) for (int i=0; i<5; i++) # for문 상세 내용 작성
* 제어 구조 = 조건문 (1문장으로 설명)
* end 부분 추가는 아래 캡쳐와 같이 명확히 구분



* 함수 주석
    * 의미 단위로 enter 구분
    * 한 줄에 한 문장 작성

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




<작성 파일명> = 파이썬 기준

* 기본 : 소문자 + _ (언더바 기본1개, 최대 2개)

구분
	스타일
	예시
	비고

패키지(폴더)
	snake_case
	auth_service, user_api
	전부 소문자, _로 단어 구분

모듈(파일)
	snake_case
	auth_controller.py, user_schema.py
	Java의 클래스명 기반으로 파일명은 소문자

클래스명
	PascalCase
	AuthService, UserRepository
	각 단어의 첫 글자 대문자

함수/메서드명
	snake_case
	get_user_list(), save_auth()
	명령형 동사로 시작 권장

변수명
	snake_case
	user_name, auth_id
	짧고 명확하게

상수명
	UPPER_CASE
	DEFAULT_PAGE_SIZE, API_VERSION
	불변 값

환경변수
	UPPER_CASE
	DATABASE_URL, SECRET_KEY
	모두 대문자, _로 구분





(QNA)



<데이터 >

* 데이터 csv 파일명, 폴더 모두 영어로 반드시
* 추후 논의 필요



소프트웨어 아키텍처

구분
	상세 구분
	버전 정보 / 설명

프론트엔드 (Frontend)
	언어
	TypeScript 5.9.3


	런타임
	Node.js 22.11.0


	프레임워크
	Vue.js 3.4.29


	빌드 도구
	Vite 5.4.10


	스타일 라이브러리
	Tailwind CSS 3.4.14


	데이터 시각화
	Chart.js 4.4.3, Vue Chart.js 5.3.1

공통 백엔드 (API 서버)
	언어
	Java 21.0.9 LTS


	프레임워크
	Spring Boot 3.5.7 (Spring Framework 6.2.12)


	빌드 도구
	Apache Maven 3.9.11


	역할
	인증/인가, 토큰 발급/검증, BFF, API Gateway, 도메인 로직

추론 백엔드 (Model Serving)
	언어
	Python 3.11.10


	런타임
	Uvicorn 0.30.6


	프레임워크
	FastAPI 0.115.4


	패키지 관리
	uv 0.5.8


	역할
	AI 추론, LLM 호출, 벡터 검색, LangChain/LangGraph Agent

벡터 DB (Vector Store)
	종류
	Qdrant 1.8.3


	사용 주체
	FastAPI / LangChain / LangGraph (Python 전용)


	비고
	Java(Spring)에서는 직접 접근하지 않음

관계형 DB (RDBMS)
	종류
	MariaDB 11.4.3 LTS


	사용 주체
	Spring Boot (메인 도메인/인증 DB), Python Read-only 가능

웹서버/프록시
	리버스 프록시
	Nginx Proxy Manager 2.11.3


	인증서 관리
	Let’s Encrypt (ACME 기반 자동 TLS)

AI Agent
	프레임워크
	LangChain 0.3.7


	그래프 엔진
	LangGraph 0.2.11


	언어 모델
	OpenAI GPT-4o-mini

운영체제 (OS)
	서버 환경
	Ubuntu Server 22.04.5 LTS


	로그 관리
	logrotate 3.21.0

개발환경 (IDE)
	개발 도구
	Visual Studio Code 1.95.2

형상관리 (VCS)
	플랫폼
	GitHub


	레포지토리 전략
	Polyrepo (서비스별 분리 운영)

CI/CD
	CI
	GitHub Actions


	러너 OS
	ubuntu-22.04


	주요 액션
	actions/checkout@v4


	
	actions/setup-node@v6 (Node 22.11.0)


	
	actions/setup-java@v5 (Java 21, Temurin)


	
	actions/setup-python@v5 (Python 3.11.10)


	
	actions/cache@v4


	CD
	GitHub Actions


	아티팩트
	actions/upload-artifact@v5, actions/download-artifact@v6




https://theskala.slack.com/docs/T089ENT4A2D/F09TS49DWRK
