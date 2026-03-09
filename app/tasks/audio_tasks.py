"""
音档上传相关的 Celery 任务。

包括：
- 孤儿记录清理 (7 天未完成的上传)
- 过期任务清理
"""

import logging
from datetime import UTC, datetime, timedelta

from celery import shared_task
from celery.schedules import crontab
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.enums.enums import JobStatus, TaskStatus, UploadStatus
from app.models.audio import AudioInfo
from app.models.upload_job import UploadJob, UploadTask
from app.services.minio_service import MinioService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def finalize_completed_uploads(self, job_id: str):
    """
    检查并完成上传任务。

    注意: AudioInfo 已在建立 Job 时预先建立
    此 Task 用于处理需要后续处理的情况 (如验证档案完整性)
    """
    db: Session = SessionLocal()
    try:
        job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # 检查是否全部完成
        completed_count = (
            db.query(UploadTask)
            .filter(
                UploadTask.job_id == job_id,
                UploadTask.status == TaskStatus.COMPLETED,
            )
            .count()
        )

        if completed_count >= job.total_files:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            db.commit()
            logger.info(f"Job {job_id} completed: {completed_count} files")

    except Exception as e:
        db.rollback()
        logger.error(f"Error finalizing job: {e}")
        raise self.retry(exc=e) from e
    finally:
        db.close()


@shared_task
def cleanup_abandoned_audio_records():
    """
    清理超过 7 天仍为 pending/uploading 的 AudioInfo 记录。

    Celery Beat: 每天凌晨 3 点执行
    """
    db: Session = SessionLocal()
    minio_service = MinioService()

    try:
        cutoff = datetime.now(UTC) - timedelta(days=7)

        stale_records = (
            db.query(AudioInfo)
            .filter(
                AudioInfo.upload_status.in_(
                    [UploadStatus.PENDING, UploadStatus.UPLOADING]
                ),
                AudioInfo.created_at < cutoff,
            )
            .all()
        )

        cleaned_count = 0
        for record in stale_records:
            # 1. 清理 MinIO 残留的 multipart upload
            if record.upload_id:
                try:
                    bucket = record.deployment.point.project.name
                    minio_service.abort_multipart_upload(
                        bucket=bucket,
                        key=record.object_key,
                        upload_id=record.upload_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to abort multipart: {e}")

            # 2. 先刪 UploadTask（FK 參照 AudioInfo），再刪 AudioInfo
            db.query(UploadTask).filter(UploadTask.audio_id == record.id).delete(
                synchronize_session=False
            )
            db.delete(record)
            cleaned_count += 1

        db.commit()
        logger.info(f"Cleaned up {cleaned_count} abandoned audio records")

    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up abandoned records: {e}")
    finally:
        db.close()


@shared_task
def cleanup_expired_jobs():
    """
    清理过期的 jobs (7天未完成)。

    每小时执行一次
    """
    db: Session = SessionLocal()
    minio_service = MinioService()

    try:
        cutoff = datetime.now(UTC) - timedelta(days=7)

        expired_jobs = (
            db.query(UploadJob)
            .filter(
                UploadJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
                UploadJob.created_at < cutoff,
            )
            .all()
        )

        for job in expired_jobs:
            # 清理 MinIO 孤儿物件
            for task in job.tasks:
                if task.upload_id:
                    try:
                        bucket = job.deployment.point.project.name
                        minio_service.abort_multipart_upload(
                            bucket=bucket,
                            key=task.object_key,
                            upload_id=task.upload_id,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to abort multipart for task {task.id}: {e}"
                        )

            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(UTC)

        db.commit()
        logger.info(f"Cleaned up {len(expired_jobs)} expired jobs")

    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up expired jobs: {e}")
    finally:
        db.close()


# =============================================================================
# Celery Beat Schedule
# =============================================================================

celery_app.conf.beat_schedule = {
    "cleanup-abandoned-audio": {
        "task": "app.tasks.audio_tasks.cleanup_abandoned_audio_records",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨 3 点
    },
    "cleanup-expired-jobs": {
        "task": "app.tasks.audio_tasks.cleanup_expired_jobs",
        "schedule": 3600.0,  # 每小时
    },
}
