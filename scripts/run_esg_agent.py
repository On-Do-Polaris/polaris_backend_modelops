#!/usr/bin/env python3
"""
==================================================================
ESG Trends Agent 실행 스크립트

사용법:
    uv run scripts/run_esg_agent.py [옵션]

옵션:
    --parallel    병렬 수집 모드 사용
    --dry-run     실제 배포 없이 테스트
    --verbose     상세 로깅 출력
==================================================================
"""
import sys
import os
import argparse
from datetime import datetime

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.esg_trends_agent.utils.config import Config
from src.esg_trends_agent.utils.logging import setup_logger, get_logger
from src.esg_trends_agent.graph import run_esg_trends_workflow, run_parallel_workflow
from src.esg_trends_agent.state import create_initial_state


def validate_config() -> bool:
    """필수 설정값 검증

    Returns:
        bool: 검증 통과 여부
    """
    logger = get_logger("esg_agent.main")

    errors = []

    # 필수 API 키 확인
    if not Config.KMA_API_KEY:
        errors.append("KMA_API_KEY가 설정되지 않았습니다 (기상청 API)")

    if not Config.OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY가 설정되지 않았습니다")

    # 선택적 설정 경고
    if not Config.KOTRA_API_KEY:
        logger.warning("KOTRA_API_KEY 미설정 - 글로벌 ESG 뉴스는 검색으로 대체됩니다")

    if not Config.SLACK_BOT_TOKEN or not Config.SLACK_CHANNEL:
        logger.warning("Slack 설정 미완료 - 리포트가 파일로만 저장됩니다")

    if not Config.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY 미설정 - DuckDuckGo 검색으로 대체됩니다")

    # 에러 출력
    if errors:
        logger.error("설정 검증 실패:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("설정 검증 완료")
    return True


def main():
    """메인 실행 함수"""
    # 인자 파싱
    parser = argparse.ArgumentParser(
        description="ESG Trends Agent - ESG 트렌드 분석 및 리포트 생성"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="병렬 수집 모드 사용 (더 빠르지만 리소스 사용 증가)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 Slack 배포 없이 테스트"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로깅 출력"
    )

    args = parser.parse_args()

    # 로거 설정
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logger(log_level)
    logger = get_logger("esg_agent.main")

    # 시작 배너
    logger.info("=" * 60)
    logger.info("🌱 ESG Trends Agent 시작")
    logger.info(f"   시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   모드: {'병렬 수집' if args.parallel else '순차 수집'}")
    logger.info(f"   Dry Run: {args.dry_run}")
    logger.info("=" * 60)

    # 설정 검증
    if not validate_config():
        logger.error("설정 검증 실패로 종료합니다")
        sys.exit(1)

    # Dry Run 모드 설정
    if args.dry_run:
        # Slack 설정 임시 비활성화
        original_slack_token = Config.SLACK_BOT_TOKEN
        original_slack_channel = Config.SLACK_CHANNEL
        Config.SLACK_BOT_TOKEN = ""
        Config.SLACK_CHANNEL = ""
        logger.info("Dry Run 모드: Slack 배포 비활성화")

    try:
        # 워크플로우 실행
        if args.parallel:
            final_state = run_parallel_workflow()
        else:
            final_state = run_esg_trends_workflow()

        # 결과 요약
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 실행 결과 요약")
        logger.info("=" * 60)
        logger.info(f"날씨 데이터: {len(final_state.get('weather_data', []))}개 지역")
        logger.info(f"국내 뉴스: {len(final_state.get('domestic_news', []))}건")
        logger.info(f"글로벌 뉴스: {len(final_state.get('global_news', []))}건")
        logger.info(f"품질 점수: {final_state.get('quality_score', 0):.1%}")

        errors = final_state.get("errors", [])
        if errors:
            logger.warning(f"발생한 에러: {len(errors)}건")
            for error in errors[:5]:  # 최대 5개만 표시
                logger.warning(f"  - {error}")

        # 리포트 미리보기
        final_report = final_state.get("final_report", "")
        if final_report:
            logger.info("")
            logger.info("📝 리포트 미리보기 (처음 500자)")
            logger.info("-" * 40)
            print(final_report[:500])
            logger.info("-" * 40)

        logger.info("")
        logger.info("✅ ESG Trends Agent 완료")

    except Exception as e:
        logger.error(f"워크플로우 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Dry Run 모드 복원
        if args.dry_run:
            Config.SLACK_BOT_TOKEN = original_slack_token
            Config.SLACK_CHANNEL = original_slack_channel


if __name__ == "__main__":
    main()
