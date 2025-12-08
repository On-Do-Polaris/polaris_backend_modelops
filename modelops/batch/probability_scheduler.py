'''
파일명: probability_scheduler.py
최종 수정일: 2025-11-22
버전: v02
파일 개요: P(H) 배치 스케줄러 (연 1회 실행)
'''

from typing import Dict, Any, List, Callable, Optional
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .probability_batch import ProbabilityBatchProcessor
from ..config.settings import settings

logger = logging.getLogger(__name__)


class ProbabilityScheduler:
    """P(H) 배치 계산 스케줄러 (매년 1월 1일 02:00)"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.processor = ProbabilityBatchProcessor({
            'parallel_workers': settings.parallel_workers
        })
        self.grid_coordinates_callback: Optional[Callable] = None
        logger.info("ProbabilityScheduler initialized")

    def start(self, grid_coordinates_callback: Optional[Callable] = None) -> None:
        """스케줄러 시작"""
        self.grid_coordinates_callback = grid_coordinates_callback

        trigger = CronTrigger(
            month=settings.probability_schedule_month,
            day=settings.probability_schedule_day,
            hour=settings.probability_schedule_hour,
            minute=settings.probability_schedule_minute
        )

        self.scheduler.add_job(
            self._execute_batch,
            trigger=trigger,
            id='annual_probability_batch',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"ProbabilityScheduler started - Schedule: {settings.probability_schedule_month}/{settings.probability_schedule_day} {settings.probability_schedule_hour}:{settings.probability_schedule_minute:02d}")

    def _execute_batch(self) -> None:
        """스케줄된 배치 실행"""
        grid_coordinates = []
        if self.grid_coordinates_callback:
            grid_coordinates = self.grid_coordinates_callback()

        self.run_batch(grid_coordinates)

    def run_batch(self, grid_coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
        """배치 실행"""
        logger.info(f"=== P(H) Batch Started ({len(grid_coordinates)} grids) ===")
        result = self.processor.process_all_grids(grid_coordinates)
        logger.info(f"=== P(H) Batch Completed: {result['success_rate']}% success ===")
        return result

    def stop(self) -> None:
        """스케줄러 중지"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("ProbabilityScheduler stopped")
