import logging
import signal
import sys
from aiops.batch.probability_scheduler import ProbabilityScheduler
from aiops.batch.hazard_scheduler import HazardScheduler
from aiops.batch.probability_batch import ProbabilityBatchProcessor
from aiops.batch.hazard_batch import HazardBatchProcessor
from aiops.triggers.notify_listener import NotifyListener
from aiops.database.connection import DatabaseConnection
from aiops.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_probability_batch():
    """P(H) 배치 작업 실행"""
    logger.info("Starting Probability batch job (triggered)")
    processor = ProbabilityBatchProcessor({
        'parallel_workers': settings.parallel_workers
    })
    grid_coordinates = DatabaseConnection.fetch_grid_coordinates()
    result = processor.process_all_grids(grid_coordinates)
    logger.info(f"Probability batch completed: {result}")


def run_hazard_batch():
    """Hazard Score 배치 작업 실행"""
    logger.info("Starting Hazard Score batch job (triggered)")
    processor = HazardBatchProcessor({
        'parallel_workers': settings.parallel_workers
    })
    grid_coordinates = DatabaseConnection.fetch_grid_coordinates()
    result = processor.process_all_grids(grid_coordinates)
    logger.info(f"Hazard batch completed: {result}")


def main():
    """메인 실행 함수"""
    logger.info("Starting AIops workflow system")

    # 스케줄러 시작
    prob_scheduler = ProbabilityScheduler()
    hazard_scheduler = HazardScheduler()

    prob_scheduler.start(grid_coordinates_callback=DatabaseConnection.fetch_grid_coordinates)
    hazard_scheduler.start(grid_coordinates_callback=DatabaseConnection.fetch_grid_coordinates)

    logger.info("Schedulers started")
    logger.info(f"  - Probability: {settings.probability_schedule_month}/{settings.probability_schedule_day} {settings.probability_schedule_hour}:{settings.probability_schedule_minute:02d}")
    logger.info(f"  - Hazard: {settings.hazard_schedule_month}/{settings.hazard_schedule_day} {settings.hazard_schedule_hour}:{settings.hazard_schedule_minute:02d}")

    # NOTIFY 리스너 설정
    listener = NotifyListener()
    listener.register_handler('probability', run_probability_batch)
    listener.register_handler('hazard', run_hazard_batch)

    # Graceful shutdown 설정
    def signal_handler(sig, frame):
        logger.info("Shutting down gracefully...")
        prob_scheduler.stop()
        hazard_scheduler.stop()
        listener.stop_listening()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # NOTIFY 리스닝 시작 (blocking)
    try:
        listener.start_listening()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        signal_handler(None, None)


if __name__ == "__main__":
    main()
