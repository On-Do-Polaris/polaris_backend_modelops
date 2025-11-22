'''
파일명: hazard_scheduler.py
최종 수정일: 2025-11-22
버전: v01
파일 개요: Hazard Score 배치 스케줄러 (연 1회 실행)
'''

from typing import Dict, Any, List
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .hazard_batch import HazardBatchProcessor

logger = logging.getLogger(__name__)


class HazardScheduler:
	"""Hazard Score 배치 계산 스케줄러 (매년 1월 1일 04:00)"""

	def __init__(self, config: Dict[str, Any]):
		self.config = config
		self.batch_processor = HazardBatchProcessor(config.get('batch_config', {}))
		self.scheduler = BackgroundScheduler() if config.get('enable_scheduler', True) else None
		logger.info("HazardScheduler initialized")

	def start(self, grid_coordinates_callback=None) -> None:
		"""스케줄러 시작"""
		if not self.scheduler:
			return

		schedule = self.config.get('schedule', {'type': 'cron', 'month': 1, 'day': 1, 'hour': 4})

		if schedule['type'] == 'cron':
			trigger = CronTrigger(
				month=schedule.get('month', 1),
				day=schedule.get('day', 1),
				hour=schedule.get('hour', 4),
				minute=schedule.get('minute', 0)
			)
			self.scheduler.add_job(
				lambda: self.run_batch(grid_coordinates_callback() if grid_coordinates_callback else []),
				trigger=trigger,
				id='annual_hazard_batch',
				replace_existing=True
			)

		self.scheduler.start()
		logger.info("HazardScheduler started")

	def run_batch(self, grid_coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
		"""배치 실행"""
		logger.info(f"=== Hazard Score Batch Started ({len(grid_coordinates)} grids) ===")
		result = self.batch_processor.process_all_grids(grid_coordinates)
		logger.info(f"=== Hazard Score Batch Completed: {result['success_rate']}% success ===")
		return result

	def stop(self) -> None:
		if self.scheduler and self.scheduler.running:
			self.scheduler.shutdown()
