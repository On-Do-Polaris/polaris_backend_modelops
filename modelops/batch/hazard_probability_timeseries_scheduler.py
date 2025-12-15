from typing import List, Tuple, Callable, Optional
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .hazard_probability_timeseries_batch import run_batch as run_hp_batch_processor
from .hazard_probability_timeseries_batch import get_all_grid_points
from ..config.settings import settings

logger = logging.getLogger(__name__)


class HazardProbabilityTimeseriesScheduler:
    """H, P(H) 시계열 배치 계산 스케줄러 (매년 1월 1일 04:00)"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        logger.info("HazardProbabilityTimeseriesScheduler initialized")

    def start(self) -> None:
        """스케줄러 시작"""
        # H, P(H) 배치는 매년 1월 1일 04:00에 실행
        # settings.py의 hazard_schedule 설정을 따름
        trigger = CronTrigger(
            month=settings.hazard_schedule_month,
            day=settings.hazard_schedule_day,
            hour=settings.hazard_schedule_hour,
            minute=settings.hazard_schedule_minute
        )

        self.scheduler.add_job(
            self._execute_batch,
            trigger=trigger,
            id='annual_hazard_probability_timeseries_batch',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(
            f"HazardProbabilityTimeseriesScheduler started - Schedule: "
            f"{settings.hazard_schedule_month}/{settings.hazard_schedule_day} "
            f"{settings.hazard_schedule_hour}:{settings.hazard_schedule_minute:02d}"
        )

    def _execute_batch(self) -> None:
        """스케줄된 배치 실행"""
        logger.info(f"=== H, P(H) Timeseries Batch Scheduled Execution Started ===")
        try:
            # 모든 격자점 가져오기 (필요 시)
            # 현재 run_batch는 grid_points를 None으로 전달하면 내부에서 get_all_grid_points()를 호출
            run_hp_batch_processor(
                grid_points=None, # run_batch에서 알아서 조회하도록 None 전달
                scenarios=None,   # 기본 시나리오 사용
                years=None,       # 기본 연도 범위 사용
                risk_types=None,  # 기본 리스크 타입 사용
                batch_size=settings.batch_size
            )
            logger.info(f"=== H, P(H) Timeseries Batch Scheduled Execution Completed Successfully ===")
        except Exception as e:
            logger.error(f"=== H, P(H) Timeseries Batch Scheduled Execution Failed: {e} ===")
            
    def stop(self) -> None:
        """스케줄러 중지"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("HazardProbabilityTimeseriesScheduler stopped")
