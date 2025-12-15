'''
파일명: batch_scheduler.py
최종 수정일: 2025-12-15
버전: v01
파일 개요: H와 P(H) 배치 작업 스케줄러 (APScheduler 사용)
변경 이력:
    - 2025-12-15: v01 - 최초 생성
        * P(H) 배치: 매년 1월 1일 02:00 실행
        * H 배치: 매년 1월 1일 04:00 실행
        * APScheduler CronTrigger 사용
        * 독립 실행 및 백그라운드 서비스 지원
'''

import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import sys
import os

# 배치 모듈 임포트
from .probability_timeseries_batch import run_probability_batch
from .hazard_timeseries_batch import run_hazard_batch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def probability_batch_job():
    """
    P(H) 배치 작업 실행 함수
    스케줄: 매년 1월 1일 02:00
    """
    logger.info("=" * 80)
    logger.info("P(H) BATCH JOB STARTED")
    logger.info(f"Execution Time: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    try:
        run_probability_batch(
            grid_points=None,  # 전체 격자점
            scenarios=None,    # 전체 시나리오
            years=None,        # 2021-2100
            risk_types=None,   # 전체 리스크
            batch_size=100,
            max_workers=4
        )
        logger.info("P(H) BATCH JOB COMPLETED SUCCESSFULLY")
    except Exception as e:
        logger.error(f"P(H) BATCH JOB FAILED: {e}", exc_info=True)
        raise


def hazard_batch_job():
    """
    H 배치 작업 실행 함수
    스케줄: 매년 1월 1일 04:00
    """
    logger.info("=" * 80)
    logger.info("HAZARD SCORE BATCH JOB STARTED")
    logger.info(f"Execution Time: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    try:
        run_hazard_batch(
            grid_points=None,  # 전체 격자점
            scenarios=None,    # 전체 시나리오
            years=None,        # 2021-2100
            risk_types=None,   # 전체 리스크
            batch_size=100,
            max_workers=4
        )
        logger.info("HAZARD SCORE BATCH JOB COMPLETED SUCCESSFULLY")
    except Exception as e:
        logger.error(f"HAZARD SCORE BATCH JOB FAILED: {e}", exc_info=True)
        raise


def start_scheduler():
    """
    스케줄러 시작 함수
    """
    scheduler = BlockingScheduler()

    # P(H) 배치 스케줄 등록: 매년 1월 1일 02:00
    scheduler.add_job(
        probability_batch_job,
        trigger=CronTrigger(
            month=1,      # 1월
            day=1,        # 1일
            hour=2,       # 02:00
            minute=0
        ),
        id='probability_batch',
        name='P(H) Timeseries Batch',
        replace_existing=True
    )

    # H 배치 스케줄 등록: 매년 1월 1일 04:00
    scheduler.add_job(
        hazard_batch_job,
        trigger=CronTrigger(
            month=1,      # 1월
            day=1,        # 1일
            hour=4,       # 04:00
            minute=0
        ),
        id='hazard_batch',
        name='Hazard Score Timeseries Batch',
        replace_existing=True
    )

    logger.info("=" * 80)
    logger.info("BATCH SCHEDULER STARTED")
    logger.info("Scheduled Jobs:")
    logger.info("  1. P(H) Batch - Every January 1st at 02:00")
    logger.info("  2. Hazard Batch - Every January 1st at 04:00")
    logger.info("=" * 80)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()


if __name__ == "__main__":
    """
    실행 예시:

    # 스케줄러 시작 (포그라운드)
    python -m modelops.batch.batch_scheduler

    # 백그라운드 실행 (Linux/Mac)
    nohup python -m modelops.batch.batch_scheduler > scheduler.log 2>&1 &

    # Windows 서비스로 등록 (별도 설정 필요)
    # 또는 Windows Task Scheduler 사용
    """

    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}", exc_info=True)
        sys.exit(1)
