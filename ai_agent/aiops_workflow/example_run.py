'''
파일명: example_run.py
최종 수정일: 2025-11-22
버전: v01
파일 개요: AIops Workflow 실행 예제
'''

import logging
from datetime import datetime

from ai_agent.aiops_workflow import (
	ProbabilityBatchProcessor,
	HazardBatchProcessor,
	ProbabilityScheduler,
	HazardScheduler
)

# 로깅 설정
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ========== 예제 1: 수동 배치 실행 ==========
def example_manual_batch():
	"""수동으로 배치 작업 실행"""
	logger.info("=== Example 1: Manual Batch Execution ===")

	# 테스트용 격자 좌표 (실제로는 DB에서 조회)
	grid_coordinates = [
		{'lat': 37.5665, 'lon': 126.9780},  # 서울
		{'lat': 35.1796, 'lon': 129.0756},  # 부산
		{'lat': 33.4890, 'lon': 126.4983},  # 제주
		# ... 실제로는 수천~수만 개
	]

	# P(H) 배치 실행
	prob_config = {
		'parallel_workers': 4,
		'db_config': {},
		'storage_config': {}
	}

	prob_processor = ProbabilityBatchProcessor(prob_config)
	prob_result = prob_processor.process_all_grids(grid_coordinates)

	logger.info(f"P(H) Batch Result: {prob_result}")

	# Hazard Score 배치 실행
	hazard_config = {
		'parallel_workers': 4,
		'db_config': {},
		'storage_config': {}
	}

	hazard_processor = HazardBatchProcessor(hazard_config)
	hazard_result = hazard_processor.process_all_grids(grid_coordinates)

	logger.info(f"Hazard Score Batch Result: {hazard_result}")


# ========== 예제 2: 스케줄러 실행 ==========
def example_scheduler():
	"""스케줄러로 자동 실행"""
	logger.info("=== Example 2: Scheduler Execution ===")

	# 격자 좌표를 가져오는 함수 (DB 연동)
	def get_grid_coordinates():
		# 실제로는 DB 쿼리
		# return db.query("SELECT lat, lon FROM grid_coordinates")
		return [
			{'lat': 37.5665, 'lon': 126.9780},
			{'lat': 35.1796, 'lon': 129.0756},
			{'lat': 33.4890, 'lon': 126.4983},
		]

	# P(H) 스케줄러 (매년 1월 1일 02:00)
	prob_scheduler_config = {
		'schedule': {
			'type': 'cron',
			'month': 1,
			'day': 1,
			'hour': 2,
			'minute': 0
		},
		'batch_config': {
			'parallel_workers': 8
		},
		'enable_scheduler': True
	}

	prob_scheduler = ProbabilityScheduler(prob_scheduler_config)
	prob_scheduler.start(grid_coordinates_callback=get_grid_coordinates)

	# Hazard Score 스케줄러 (매년 1월 1일 04:00)
	hazard_scheduler_config = {
		'schedule': {
			'type': 'cron',
			'month': 1,
			'day': 1,
			'hour': 4,
			'minute': 0
		},
		'batch_config': {
			'parallel_workers': 8
		},
		'enable_scheduler': True
	}

	hazard_scheduler = HazardScheduler(hazard_scheduler_config)
	hazard_scheduler.start(grid_coordinates_callback=get_grid_coordinates)

	logger.info("Schedulers started successfully!")
	logger.info("P(H) will run annually on Jan 1 at 02:00")
	logger.info("Hazard Score will run annually on Jan 1 at 04:00")

	# 스케줄러는 백그라운드에서 계속 실행됨
	# 종료하려면: prob_scheduler.stop(), hazard_scheduler.stop()


# ========== 예제 3: 테스트용 즉시 실행 (Interval) ==========
def example_test_scheduler():
	"""테스트용 짧은 주기 스케줄러"""
	logger.info("=== Example 3: Test Scheduler (Interval) ===")

	def get_test_grids():
		return [
			{'lat': 37.5665, 'lon': 126.9780},
			{'lat': 35.1796, 'lon': 129.0756},
		]

	# 1시간마다 실행 (테스트용)
	test_config = {
		'schedule': {
			'type': 'interval',
			'hours': 1  # 1시간마다
		},
		'batch_config': {
			'parallel_workers': 2
		},
		'enable_scheduler': True
	}

	scheduler = ProbabilityScheduler(test_config)
	scheduler.start(grid_coordinates_callback=get_test_grids)

	logger.info("Test scheduler started! Will run every 1 hour")


if __name__ == '__main__':
	# 원하는 예제 실행
	example_manual_batch()
	# example_scheduler()
	# example_test_scheduler()
