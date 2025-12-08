"""
ModelOps Risk Assessment API 서버 시작 스크립트

E, V, AAL 계산 API 서버를 실행합니다.

사용법:
    python start_api_server.py

옵션:
    --host: 호스트 주소 (기본값: 0.0.0.0)
    --port: 포트 번호 (기본값: 8001)
    --reload: 개발 모드 (코드 변경 시 자동 재시작)
"""

import uvicorn
import argparse
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """API 서버 시작"""
    parser = argparse.ArgumentParser(
        description="ModelOps Risk Assessment API 서버"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="호스트 주소 (기본값: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="포트 번호 (기본값: 8001)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="개발 모드 - 코드 변경 시 자동 재시작"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="로그 레벨 (기본값: info)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("ModelOps Risk Assessment API 서버 시작")
    print("=" * 70)
    print(f"호스트: {args.host}")
    print(f"포트: {args.port}")
    print(f"리로드 모드: {'활성화' if args.reload else '비활성화'}")
    print(f"로그 레벨: {args.log_level.upper()}")
    print("=" * 70)
    print(f"API 문서: http://localhost:{args.port}/docs")
    print(f"Health Check: http://localhost:{args.port}/health")
    print(f"WebSocket 예시: ws://localhost:{args.port}/api/v1/risk-assessment/ws/{{request_id}}")
    print("=" * 70)
    print("서버를 종료하려면 Ctrl+C를 누르세요")
    print("=" * 70)

    # uvicorn으로 서버 실행
    uvicorn.run(
        "modelops.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다...")
        sys.exit(0)
    except Exception as e:
        print(f"\n에러 발생: {e}")
        sys.exit(1)
