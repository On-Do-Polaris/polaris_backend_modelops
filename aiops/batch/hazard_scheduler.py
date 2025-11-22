'''
파일명: hazard_scheduler.py
최종 수정일: 2025-11-22
버전: v02
파일 개요: Hazard Score 배치 스케줄러 (연 1회 실행)
'''

from typing import Dict, Any, List, Callable, Optional
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .hazard_batch import HazardBatchProcessor
from ..config.settings import settings

logger = logging.getLogger(__name__)


class HazardScheduler:
    """Hazard Score 배치 계산 스케줄러 (매년 1월 1일 04:00)"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.processor = HazardBatchProcessor({
            'parallel_workers': settings.parallel_workers
        })
        self.grid_coordinates_callback: Optional[Callable] = None
        logger.info("HazardScheduler initialized")

    def start(self, grid_coordinates_callback: Optional[Callable] = None) -> None:
        """스케줄러 시작"""
        self.grid_coordinates_callback = grid_coordinates_callback

        trigger = CronTrigger(
            month=settings.hazard_schedule_month,
            day=settings.hazard_schedule_day,
            hour=settings.hazard_schedule_hour,
            minute=settings.hazard_schedule_minute
        )

        self.scheduler.add_job(
            self._execute_batch,
            trigger=trigger,
            id='annual_hazard_batch',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"HazardScheduler started - Schedule: {settings.hazard_schedule_month}/{settings.hazard_schedule_day} {settings.hazard_schedule_hour}:{settings.hazard_schedule_minute:02d}")

    def _execute_batch(self) -> None:
        """스케줄된 배치 실행"""
        grid_coordinates = []
        if self.grid_coordinates_callback:
            grid_coordinates = self.grid_coordinates_callback()

        self.run_batch(grid_coordinates)

    def run_batch(self, grid_coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
        """배치 실행"""
        logger.info(f"=== Hazard Score Batch Started ({len(grid_coordinates)} grids) ===")
        result = self.processor.process_all_grids(grid_coordinates)
        logger.info(f"=== Hazard Score Batch Completed: {result['success_rate']}% success ===")
        return result

    def stop(self) -> None:
        """스케줄러 중지"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("HazardScheduler stopped")
