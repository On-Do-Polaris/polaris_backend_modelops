"""
배치 리팩토링 테스트 스크립트
소규모 테스트 (10개 격자)
"""

import sys
import logging
from modelops.batch.probability_batch import ProbabilityBatchProcessor
from modelops.batch.hazard_batch import HazardBatchProcessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_probability_batch():
    """Probability Batch 테스트"""
    logger.info("=" * 60)
    logger.info("Testing Probability Batch (10 grids)")
    logger.info("=" * 60)

    # 테스트용 10개 격자 좌표
    test_coords = [
        {'latitude': 37.5 + i * 0.1, 'longitude': 127.0 + i * 0.1}
        for i in range(10)
    ]

    config = {'parallel_workers': 2}
    processor = ProbabilityBatchProcessor(config)

    try:
        summary = processor.process_all_grids(test_coords)

        logger.info("\n" + "=" * 60)
        logger.info("Probability Batch Test Results:")
        logger.info(f"  Total grids: {summary['total_grids']}")
        logger.info(f"  Processed: {summary['processed']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Success rate: {summary['success_rate']}%")
        logger.info(f"  Duration: {summary['duration_seconds']:.2f}s")
        logger.info("=" * 60)

        return summary['failed'] == 0

    except Exception as e:
        logger.error(f"Probability batch test failed: {str(e)}", exc_info=True)
        return False


def test_hazard_batch():
    """Hazard Batch 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Hazard Batch (10 grids)")
    logger.info("=" * 60)

    # 테스트용 10개 격자 좌표
    test_coords = [
        {'latitude': 37.5 + i * 0.1, 'longitude': 127.0 + i * 0.1}
        for i in range(10)
    ]

    config = {'parallel_workers': 2}
    processor = HazardBatchProcessor(config)

    try:
        summary = processor.process_all_grids(test_coords)

        logger.info("\n" + "=" * 60)
        logger.info("Hazard Batch Test Results:")
        logger.info(f"  Total grids: {summary['total_grids']}")
        logger.info(f"  Processed: {summary['processed']}")
        logger.info(f"  Failed: {summary['failed']}")
        logger.info(f"  Success rate: {summary['success_rate']}%")
        logger.info(f"  Duration: {summary['duration_seconds']:.2f}s")
        logger.info("=" * 60)

        return summary['failed'] == 0

    except Exception as e:
        logger.error(f"Hazard batch test failed: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("Starting batch refactor tests...\n")

    # Probability Batch 테스트
    prob_success = test_probability_batch()

    # Hazard Batch 테스트
    hazard_success = test_hazard_batch()

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Probability Batch: {'✅ PASSED' if prob_success else '❌ FAILED'}")
    logger.info(f"Hazard Batch: {'✅ PASSED' if hazard_success else '❌ FAILED'}")
    logger.info("=" * 60)

    if prob_success and hazard_success:
        logger.info("\n🎉 All tests PASSED! Refactoring successful.")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests FAILED. Please check the logs above.")
        sys.exit(1)
