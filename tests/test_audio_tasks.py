"""
Celery 任務測試。

測試 app/tasks/audio_tasks.py 中的清理任務。
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.enums.enums import JobStatus, TaskStatus, UploadStatus


class TestFinalizeCompletedUploads:
    """測試 finalize_completed_uploads 任務。"""

    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_job_not_found(self, mock_session_local):
        """測試 job 不存在時的處理。"""
        from app.tasks.audio_tasks import finalize_completed_uploads

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # 應該不會拋出異常
        finalize_completed_uploads("nonexistent-job-id")

        mock_db.close.assert_called_once()

    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_job_completed_when_all_tasks_done(self, mock_session_local):
        """測試所有任務完成時，job 狀態更新為 completed。"""
        from app.tasks.audio_tasks import finalize_completed_uploads

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock job
        mock_job = MagicMock()
        mock_job.total_files = 5
        mock_job.status = JobStatus.PROCESSING
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        # Mock completed count
        mock_db.query.return_value.filter.return_value.count.return_value = 5

        finalize_completed_uploads("test-job-id")

        assert mock_job.status == JobStatus.COMPLETED
        assert mock_job.completed_at is not None
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_job_not_completed_when_tasks_pending(self, mock_session_local):
        """測試任務未全部完成時，job 狀態不變。"""
        from app.tasks.audio_tasks import finalize_completed_uploads

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock job
        mock_job = MagicMock()
        mock_job.total_files = 5
        mock_job.status = JobStatus.PROCESSING
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        # Mock completed count (only 3 of 5)
        mock_db.query.return_value.filter.return_value.count.return_value = 3

        finalize_completed_uploads("test-job-id")

        # Status should not change
        assert mock_job.status == JobStatus.PROCESSING
        mock_db.close.assert_called_once()


class TestCleanupAbandonedAudioRecords:
    """測試 cleanup_abandoned_audio_records 任務。"""

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_no_stale_records(self, mock_session_local, mock_minio_class):
        """測試沒有過期記錄時的處理。"""
        from app.tasks.audio_tasks import cleanup_abandoned_audio_records

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []

        cleanup_abandoned_audio_records()

        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_stale_records_without_upload_id(
        self, mock_session_local, mock_minio_class
    ):
        """測試清理沒有 upload_id 的過期記錄。"""
        from app.tasks.audio_tasks import cleanup_abandoned_audio_records

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock stale record without upload_id
        mock_record = MagicMock()
        mock_record.upload_id = None
        mock_record.object_key = "test/key.wav"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]

        cleanup_abandoned_audio_records()

        # Should delete record but not call abort_multipart_upload
        mock_db.delete.assert_called_once_with(mock_record)
        mock_minio.abort_multipart_upload.assert_not_called()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_stale_records_with_upload_id(
        self, mock_session_local, mock_minio_class
    ):
        """測試清理有 upload_id 的過期記錄 (需要中止 multipart upload)。"""
        from app.tasks.audio_tasks import cleanup_abandoned_audio_records

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock stale record with upload_id
        mock_record = MagicMock()
        mock_record.upload_id = "test-upload-id"
        mock_record.object_key = "test/key.wav"
        mock_record.deployment.point.project.name = "test-bucket"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]

        cleanup_abandoned_audio_records()

        # Should call abort_multipart_upload and delete record
        mock_minio.abort_multipart_upload.assert_called_once_with(
            bucket="test-bucket",
            key="test/key.wav",
            upload_id="test-upload-id",
        )
        mock_db.delete.assert_called_once_with(mock_record)
        mock_db.commit.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_handles_minio_error(self, mock_session_local, mock_minio_class):
        """測試 MinIO 錯誤時繼續清理。"""
        from app.tasks.audio_tasks import cleanup_abandoned_audio_records

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock MinIO error
        mock_minio.abort_multipart_upload.side_effect = Exception("MinIO error")

        # Mock stale record
        mock_record = MagicMock()
        mock_record.upload_id = "test-upload-id"
        mock_record.object_key = "test/key.wav"
        mock_record.deployment.point.project.name = "test-bucket"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]

        # Should not raise exception
        cleanup_abandoned_audio_records()

        # Should still delete record
        mock_db.delete.assert_called_once_with(mock_record)
        mock_db.commit.assert_called_once()


class TestCleanupExpiredJobs:
    """測試 cleanup_expired_jobs 任務。"""

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_no_expired_jobs(self, mock_session_local, mock_minio_class):
        """測試沒有過期任務時的處理。"""
        from app.tasks.audio_tasks import cleanup_expired_jobs

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []

        cleanup_expired_jobs()

        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_expired_job_without_tasks(
        self, mock_session_local, mock_minio_class
    ):
        """測試清理沒有子任務的過期任務。"""
        from app.tasks.audio_tasks import cleanup_expired_jobs

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock expired job without tasks
        mock_job = MagicMock()
        mock_job.status = JobStatus.PENDING
        mock_job.tasks = []
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_job]

        cleanup_expired_jobs()

        assert mock_job.status == JobStatus.FAILED
        assert mock_job.completed_at is not None
        mock_db.commit.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_expired_job_with_multipart_tasks(
        self, mock_session_local, mock_minio_class
    ):
        """測試清理有分段上傳的過期任務。"""
        from app.tasks.audio_tasks import cleanup_expired_jobs

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock task with upload_id
        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.upload_id = "upload-id-1"
        mock_task.object_key = "test/key.wav"

        # Mock expired job
        mock_job = MagicMock()
        mock_job.status = JobStatus.PROCESSING
        mock_job.tasks = [mock_task]
        mock_job.deployment.point.project.name = "test-bucket"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_job]

        cleanup_expired_jobs()

        # Should abort multipart upload
        mock_minio.abort_multipart_upload.assert_called_once_with(
            bucket="test-bucket",
            key="test/key.wav",
            upload_id="upload-id-1",
        )
        assert mock_job.status == JobStatus.FAILED
        mock_db.commit.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_handles_minio_error(self, mock_session_local, mock_minio_class):
        """測試 MinIO 錯誤時繼續處理。"""
        from app.tasks.audio_tasks import cleanup_expired_jobs

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock MinIO error
        mock_minio.abort_multipart_upload.side_effect = Exception("MinIO error")

        # Mock task
        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.upload_id = "upload-id-1"
        mock_task.object_key = "test/key.wav"

        # Mock job
        mock_job = MagicMock()
        mock_job.status = JobStatus.PROCESSING
        mock_job.tasks = [mock_task]
        mock_job.deployment.point.project.name = "test-bucket"
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_job]

        # Should not raise
        cleanup_expired_jobs()

        # Should still mark job as failed
        assert mock_job.status == JobStatus.FAILED
        mock_db.commit.assert_called_once()

    @patch("app.tasks.audio_tasks.MinioService")
    @patch("app.tasks.audio_tasks.SessionLocal")
    def test_cleanup_skips_tasks_without_upload_id(
        self, mock_session_local, mock_minio_class
    ):
        """測試跳過沒有 upload_id 的任務。"""
        from app.tasks.audio_tasks import cleanup_expired_jobs

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_minio = MagicMock()
        mock_minio_class.return_value = mock_minio

        # Mock task without upload_id
        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.upload_id = None

        # Mock job
        mock_job = MagicMock()
        mock_job.status = JobStatus.PENDING
        mock_job.tasks = [mock_task]
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_job]

        cleanup_expired_jobs()

        # Should not call abort_multipart_upload
        mock_minio.abort_multipart_upload.assert_not_called()
        assert mock_job.status == JobStatus.FAILED
        mock_db.commit.assert_called_once()


class TestCeleryBeatSchedule:
    """測試 Celery Beat 排程配置。"""

    def test_beat_schedule_exists(self):
        """測試排程配置存在。"""
        from app.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "cleanup-abandoned-audio" in schedule
        assert "cleanup-expired-jobs" in schedule

    def test_cleanup_abandoned_audio_schedule(self):
        """測試孤兒記錄清理排程。"""
        from app.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule["cleanup-abandoned-audio"]
        assert schedule["task"] == "app.tasks.audio_tasks.cleanup_abandoned_audio_records"

    def test_cleanup_expired_jobs_schedule(self):
        """測試過期任務清理排程。"""
        from app.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule["cleanup-expired-jobs"]
        assert schedule["task"] == "app.tasks.audio_tasks.cleanup_expired_jobs"
        assert schedule["schedule"] == 3600.0  # 每小時
