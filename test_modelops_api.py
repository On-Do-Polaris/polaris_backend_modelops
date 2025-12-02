"""
ModelOps FastAPI 테스트 스크립트
Health Check와 기본 엔드포인트 테스트
"""

import requests
import json
import sys
import time
from typing import Optional

# API 기본 URL
BASE_URL = "http://localhost:8001"


class Colors:
    """터미널 색상"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """성공 메시지"""
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")


def print_error(text: str):
    """에러 메시지"""
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")


def print_info(text: str):
    """정보 메시지"""
    print(f"{Colors.YELLOW}[INFO] {text}{Colors.RESET}")


def check_server_running() -> bool:
    """서버 실행 여부 확인"""
    print_header("1. 서버 실행 확인")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=3)
        if response.status_code == 200:
            data = response.json()
            print_success("서버가 실행 중입니다!")
            print(f"   서비스: {data.get('service')}")
            print(f"   버전: {data.get('version')}")
            print(f"   설명: {data.get('description')}")
            return True
        else:
            print_error(f"서버 응답 오류: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("서버에 연결할 수 없습니다.")
        print_info("서버를 시작하려면: python -m modelops.api.main")
        print_info("또는: uvicorn modelops.api.main:app --host 0.0.0.0 --port 8001")
        return False
    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        return False


def test_health_check() -> bool:
    """Health Check 테스트"""
    print_header("2. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code == 200:
            data = response.json()
            print_success("Health Check 성공!")
            print(f"   상태: {data.get('status')}")
            print(f"   서비스: {data.get('service')}")
            print(f"   타임스탬프: {data.get('timestamp')}")
            return True
        else:
            print_error(f"Health Check 실패: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health Check 오류: {str(e)}")
        return False


def test_database_health() -> bool:
    """Database Health Check 테스트"""
    print_header("3. Database Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health/db", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Database 연결 성공!")
            print(f"   상태: {data.get('status')}")
            print(f"   데이터베이스: {data.get('database')}")
            print(f"   타임스탬프: {data.get('timestamp')}")
            return True
        else:
            print_error(f"Database 연결 실패: {response.status_code}")
            error_data = response.json()
            print(f"   에러: {error_data.get('detail', {}).get('error')}")
            print_info("데이터베이스 서버(포트 5432 또는 5433)가 실행 중인지 확인하세요.")
            return False
    except Exception as e:
        print_error(f"Database Health Check 오류: {str(e)}")
        return False


def test_api_docs() -> bool:
    """API 문서 접근 테스트"""
    print_header("4. API 문서 접근")
    try:
        # Swagger UI 테스트
        response = requests.get(f"{BASE_URL}/docs", timeout=3)
        if response.status_code == 200:
            print_success("Swagger UI 접근 가능!")
            print(f"   URL: {BASE_URL}/docs")
        else:
            print_error(f"Swagger UI 접근 실패: {response.status_code}")

        # ReDoc 테스트
        response = requests.get(f"{BASE_URL}/redoc", timeout=3)
        if response.status_code == 200:
            print_success("ReDoc 접근 가능!")
            print(f"   URL: {BASE_URL}/redoc")
            return True
        else:
            print_error(f"ReDoc 접근 실패: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"API 문서 접근 오류: {str(e)}")
        return False


def test_risk_assessment_endpoint() -> bool:
    """Risk Assessment 엔드포인트 기본 테스트 (DB 연결 필요 없음)"""
    print_header("5. Risk Assessment 엔드포인트 구조 확인")

    # 엔드포인트 존재 여부만 확인
    print_info("POST /api/v1/risk-assessment/calculate 엔드포인트 확인")
    try:
        # 잘못된 데이터로 테스트 (구조 확인용)
        response = requests.post(
            f"{BASE_URL}/api/v1/risk-assessment/calculate",
            json={},  # 빈 데이터
            timeout=3
        )

        # 422 (Validation Error) 또는 500 (Server Error) 예상
        if response.status_code in [422, 500]:
            print_success("엔드포인트가 존재하고 응답합니다.")
            print(f"   상태 코드: {response.status_code}")
            if response.status_code == 422:
                print_info("   (Validation Error는 정상입니다 - 엔드포인트가 작동 중)")
            return True
        elif response.status_code == 200:
            print_success("엔드포인트가 정상 작동합니다!")
            return True
        else:
            print_error(f"예상치 못한 응답: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"엔드포인트 테스트 오류: {str(e)}")
        return False


def print_summary(results: dict):
    """테스트 결과 요약"""
    print_header("테스트 결과 요약")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for test_name, result in results.items():
        status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if result else f"{Colors.RED}[FAIL]{Colors.RESET}"
        print(f"  {test_name}: {status}")

    print(f"\n{Colors.BOLD}Total {total} tests:{Colors.RESET}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.RESET}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Some tests failed{Colors.RESET}")


def main():
    """메인 테스트 실행"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print(" " * 10 + "ModelOps FastAPI Test")
    print("=" * 60)
    print(f"{Colors.RESET}\n")

    results = {}

    # 1. 서버 실행 확인
    if not check_server_running():
        print_error("\n서버가 실행되지 않아 테스트를 중단합니다.")
        sys.exit(1)
    results["서버 실행"] = True

    # 2. Health Check
    results["Health Check"] = test_health_check()

    # 3. Database Health Check
    results["Database Health"] = test_database_health()

    # 4. API 문서
    results["API 문서"] = test_api_docs()

    # 5. Risk Assessment 엔드포인트
    results["Risk Assessment 엔드포인트"] = test_risk_assessment_endpoint()

    # 결과 요약
    print_summary(results)

    # 추가 정보
    print_header("Useful Links")
    print(f"  API Docs (Swagger): {Colors.BLUE}{BASE_URL}/docs{Colors.RESET}")
    print(f"  API Docs (ReDoc):   {Colors.BLUE}{BASE_URL}/redoc{Colors.RESET}")
    print(f"  Health Check:       {Colors.BLUE}{BASE_URL}/health{Colors.RESET}")
    print(f"  DB Health:          {Colors.BLUE}{BASE_URL}/health/db{Colors.RESET}")

    # 종료 코드
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
