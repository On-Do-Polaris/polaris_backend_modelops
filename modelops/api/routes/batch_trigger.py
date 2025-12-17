"""
Batch Trigger API
배치 작업 강제 실행 API
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch-trigger", tags=["batch-trigger"])


@router.post("/run-probability-batch")
async def trigger_probability_batch():
    """
    P(H) 배치 작업을 1초 후에 강제 실행

    CronTrigger를 현재시간 + 1초로 설정하여 즉시 실행
    """
    try:
        from main import scheduler, probability_batch_job
        from apscheduler.triggers.cron import CronTrigger

        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler is not running")

        # 현재 시간 + 1초
        trigger_time = datetime.now() + timedelta(seconds=1)

        # 기존 작업 제거 (있다면)
        if scheduler.get_job('probability_batch_manual'):
            scheduler.remove_job('probability_batch_manual')

        # 1초 후 실행되도록 CronTrigger 설정
        scheduler.add_job(
            probability_batch_job,
            trigger=CronTrigger(
                year=trigger_time.year,
                month=trigger_time.month,
                day=trigger_time.day,
                hour=trigger_time.hour,
                minute=trigger_time.minute,
                second=trigger_time.second
            ),
            id='probability_batch_manual',
            name='P(H) Batch (Manual Trigger)',
            replace_existing=True
        )

        logger.info(f"P(H) 배치 작업이 {trigger_time.isoformat()}에 실행되도록 예약되었습니다.")

        return {
            'status': 'success',
            'message': 'P(H) 배치 작업이 1초 후에 실행됩니다.',
            'scheduled_time': trigger_time.isoformat(),
            'job_id': 'probability_batch_manual'
        }

    except ImportError as e:
        logger.error(f"Scheduler import 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduler import failed: {str(e)}")
    except Exception as e:
        logger.error(f"P(H) 배치 트리거 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger P(H) batch: {str(e)}")


@router.post("/run-hazard-batch")
async def trigger_hazard_batch():
    """
    H(Hazard Score) 배치 작업을 1초 후에 강제 실행

    CronTrigger를 현재시간 + 1초로 설정하여 즉시 실행
    """
    try:
        from main import scheduler, hazard_batch_job
        from apscheduler.triggers.cron import CronTrigger

        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler is not running")

        # 현재 시간 + 1초
        trigger_time = datetime.now() + timedelta(seconds=1)

        # 기존 작업 제거 (있다면)
        if scheduler.get_job('hazard_batch_manual'):
            scheduler.remove_job('hazard_batch_manual')

        # 1초 후 실행되도록 CronTrigger 설정
        scheduler.add_job(
            hazard_batch_job,
            trigger=CronTrigger(
                year=trigger_time.year,
                month=trigger_time.month,
                day=trigger_time.day,
                hour=trigger_time.hour,
                minute=trigger_time.minute,
                second=trigger_time.second
            ),
            id='hazard_batch_manual',
            name='Hazard Score Batch (Manual Trigger)',
            replace_existing=True
        )

        logger.info(f"H 배치 작업이 {trigger_time.isoformat()}에 실행되도록 예약되었습니다.")

        return {
            'status': 'success',
            'message': 'H 배치 작업이 1초 후에 실행됩니다.',
            'scheduled_time': trigger_time.isoformat(),
            'job_id': 'hazard_batch_manual'
        }

    except ImportError as e:
        logger.error(f"Scheduler import 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduler import failed: {str(e)}")
    except Exception as e:
        logger.error(f"H 배치 트리거 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger H batch: {str(e)}")


@router.get("/scheduled-jobs")
async def get_scheduled_jobs():
    """
    현재 스케줄러에 등록된 모든 작업 조회
    """
    try:
        from main import scheduler

        if scheduler is None:
            raise HTTPException(status_code=503, detail="Scheduler is not running")

        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })

        return {
            'total_jobs': len(jobs),
            'jobs': jobs
        }

    except ImportError as e:
        logger.error(f"Scheduler import 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Scheduler import failed: {str(e)}")
    except Exception as e:
        logger.error(f"스케줄 작업 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get scheduled jobs: {str(e)}")
