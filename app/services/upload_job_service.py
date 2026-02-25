"""
上传任务服务。

处理批量音档上传，包括：
- 建立上传任务和预先建立 AudioInfo
- 分段上传管理
- 上传进度追踪
- 断点续传支援
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.enums.enums import JobStatus, TaskStatus, UploadStatus
from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.recorder import RecorderInfo
from app.models.upload_job import UploadJob, UploadTask
from app.schemas.upload_job import (
    MultipartInitResponse,
    MultipartPartUrl,
    MultipartUrlsResponse,
    PartCompleteRequest,
    SkippedFileInfo,
    TaskProgressResponse,
    TaskStatusInfo,
    UploadJobCreateRequest,
    UploadJobCreateResponse,
    UploadJobProgress,
    UploadJobStatusResponse,
    UploadTaskInfo,
)
from app.services.minio_service import MinioService
from app.utils.audio_path import generate_object_key, parse_audio_filename
from app.utils.wav_header import parse_wav_header

logger = logging.getLogger(__name__)


class UploadJobService:
    """上传任务服务类。"""

    def __init__(self, db: Session):
        self.db = db
        self.minio = MinioService()

    # =========================================================================
    # Job Management
    # =========================================================================

    def create_job(
        self,
        request: UploadJobCreateRequest,
        user_id: int,
    ) -> UploadJobCreateResponse:
        """
        建立上传任务，同时批量建立 AudioInfo。

        Args:
            request: 上传任务请求
            user_id: 使用者 ID

        Returns:
            UploadJobCreateResponse
        """
        # 1. 验证 deployment
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(
                DeploymentInfo.id == request.deployment_id,
                DeploymentInfo.is_deleted.is_(False),
            )
            .first()
        )

        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )

        bucket = deployment.point.project.name
        point_name = deployment.point.name

        # 确保 bucket 存在
        self.minio.create_bucket(bucket)

        # 2. Per-file 格式驗證
        skipped_files: list[SkippedFileInfo] = []
        format_valid_files = []

        for file_info in request.files:
            try:
                parsed = parse_audio_filename(file_info.name)
                format_valid_files.append((file_info, parsed))
            except ValueError:
                skipped_files.append(
                    SkippedFileInfo(
                        name=file_info.name,
                        reason="Invalid filename format: expected {sn}.{YYMMDDHHMMSS}.{ext}",
                    )
                )

        # 3. 批量查詢 RecorderInfo SN（確認 SN 已在系統中登錄）
        candidate_sns = {parsed.recorder_sn for _, parsed in format_valid_files}
        existing_sns: set[str] = set()
        if candidate_sns:
            existing_sns = {
                r[0]
                for r in self.db.query(RecorderInfo.sn)
                .filter(
                    RecorderInfo.sn.in_(candidate_sns),
                    RecorderInfo.is_deleted.is_(False),
                )
                .all()
            }

        sn_valid_files = []
        for file_info, parsed in format_valid_files:
            if parsed.recorder_sn not in existing_sns:
                skipped_files.append(
                    SkippedFileInfo(
                        name=file_info.name,
                        reason=f"Recorder SN '{parsed.recorder_sn}' not found in system",
                    )
                )
            else:
                sn_valid_files.append((file_info, parsed))

        # 4. Per-file object_key 重複檢查
        candidate_keys = [
            generate_object_key(point_name, file_info.name)
            for file_info, _ in sn_valid_files
        ]
        active_keys: set[str] = set()
        deleted_keys: set[str] = set()
        if candidate_keys:
            active_keys = {
                r[0]
                for r in self.db.query(AudioInfo.object_key)
                .filter(
                    AudioInfo.object_key.in_(candidate_keys),
                    AudioInfo.is_deleted.is_(False),
                )
                .all()
            }
            deleted_keys = {
                r[0]
                for r in self.db.query(AudioInfo.object_key)
                .filter(
                    AudioInfo.object_key.in_(candidate_keys),
                    AudioInfo.is_deleted.is_(True),
                )
                .all()
            }

        valid_files = []
        for file_info, parsed in sn_valid_files:
            object_key = generate_object_key(point_name, file_info.name)
            if object_key in active_keys:
                skipped_files.append(
                    SkippedFileInfo(name=file_info.name, reason="Already exists")
                )
            elif object_key in deleted_keys:
                skipped_files.append(
                    SkippedFileInfo(
                        name=file_info.name,
                        reason="Reserved by deleted record. Hard delete to release.",
                    )
                )
            else:
                valid_files.append((file_info, parsed))

        # 5. 若全部 skip 則整批失敗
        if not valid_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All files skipped: no valid files to upload",
            )

        # 6. 批量建立 AudioInfo (upload_status = pending)
        audio_map: dict[str, AudioInfo] = {}

        for file_info, parsed in valid_files:
            object_key = generate_object_key(point_name, file_info.name)

            audio = AudioInfo(
                deployment_id=request.deployment_id,
                file_name=file_info.name,
                recorder_sn=parsed.recorder_sn,
                object_key=object_key,
                file_size=file_info.size,
                record_time=parsed.record_time,
                file_format=parsed.extension,
                upload_status=UploadStatus.PENDING,
            )
            self.db.add(audio)
            audio_map[object_key] = audio

        self.db.flush()  # 取得 audio.id

        # 4. 建立 Job
        job = UploadJob(
            deployment_id=request.deployment_id,
            user_id=user_id,
            priority=request.priority,
            total_files=len(valid_files),
            status=JobStatus.PENDING,
        )
        self.db.add(job)
        self.db.flush()

        # 5. 建立 Tasks (关联 audio_id)
        tasks_info = []
        url_expires_at = datetime.now(UTC) + timedelta(hours=24)

        for file_info, _ in valid_files:
            object_key = generate_object_key(point_name, file_info.name)
            audio = audio_map[object_key]

            task = UploadTask(
                job_id=job.id,
                audio_id=audio.id,
                file_name=file_info.name,
                object_key=object_key,
                file_size=file_info.size,
                checksum=file_info.checksum,
                url_expires_at=url_expires_at,
            )
            self.db.add(task)
            self.db.flush()

            tasks_info.append(
                UploadTaskInfo(
                    task_id=task.id,
                    audio_id=audio.id,
                    file_name=file_info.name,
                    object_key=object_key,
                )
            )

        self.db.commit()

        logger.info(f"Created upload job {job.id} with {len(tasks_info)} files")

        return UploadJobCreateResponse(
            job_id=job.id,
            deployment_id=request.deployment_id,
            status=job.status,
            total_files=job.total_files,
            tasks=tasks_info,
            skipped_files=skipped_files,
        )

    def get_job_status(self, job_id: str) -> UploadJobStatusResponse:
        """查询任务进度。"""
        job = self.db.query(UploadJob).filter(UploadJob.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        total = job.total_files
        percentage = (job.completed_count / total * 100) if total > 0 else 0

        # 估算剩余时间
        estimated = None
        if job.started_at and job.completed_count > 0:
            elapsed = (datetime.now(UTC) - job.started_at).total_seconds()
            rate = job.completed_count / elapsed
            remaining = total - job.completed_count
            if rate > 0:
                remaining_seconds = remaining / rate
                hours = int(remaining_seconds // 3600)
                minutes = int((remaining_seconds % 3600) // 60)
                estimated = f"{hours}h {minutes}m"

        # 取得所有 tasks 状态 (用于断点续传)
        tasks_info = [
            TaskStatusInfo(
                task_id=t.id,
                file_name=t.file_name,
                status=t.status,
                completed_parts=t.completed_parts or 0,
                total_parts=t.total_parts,
            )
            for t in job.tasks
        ]

        return UploadJobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=UploadJobProgress(
                total=total,
                uploaded=job.uploaded_count,
                completed=job.completed_count,
                failed=job.failed_count,
                percentage=round(percentage, 1),
            ),
            tasks=tasks_info,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_remaining=estimated,
        )

    def list_jobs(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[UploadJobStatusResponse]:
        """列出使用者的上传任务。"""
        jobs = (
            self.db.query(UploadJob)
            .filter(UploadJob.user_id == user_id)
            .order_by(UploadJob.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return [self._job_to_status_response(job) for job in jobs]

    def cancel_job(self, job_id: str, user_id: int) -> None:
        """
        取消任務，並清理 MinIO 孤兒 parts 及軟刪除相關 AudioInfo。

        Args:
            job_id: 任務 ID
            user_id: 執行取消的使用者 ID（用於軟刪除 deleted_by）
        """
        job = self.db.query(UploadJob).filter(UploadJob.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            return

        bucket = job.deployment.point.project.name
        now = datetime.now(UTC)

        for task in job.tasks:
            if task.upload_id:
                self.minio.abort_multipart_upload(
                    bucket, task.object_key, task.upload_id
                )

            audio = task.audio
            if audio and not audio.is_deleted:
                audio.is_deleted = True
                audio.deleted_at = now
                audio.deleted_by = user_id

            task.status = TaskStatus.FAILED

        job.status = JobStatus.CANCELLED
        job.completed_at = now
        self.db.commit()

    # =========================================================================
    # Multipart Upload
    # =========================================================================

    def init_multipart(self, job_id: str, task_id: str) -> MultipartInitResponse:
        """初始化分段上传。"""
        task = self._get_task(job_id, task_id)

        if task.upload_id:
            # 已初始化，回传现有资讯 (幂等)
            return MultipartInitResponse(
                upload_id=task.upload_id,
                total_parts=task.total_parts or 1,
                part_size=task.part_size,
            )

        # 计算分段
        file_size = task.file_size or 0
        part_size = 100 * 1024 * 1024  # 100MB
        total_parts = (file_size + part_size - 1) // part_size
        total_parts = max(1, total_parts)

        # 向 MinIO 初始化
        bucket = task.job.deployment.point.project.name
        upload_id = self.minio.create_multipart_upload(
            bucket=bucket,
            key=task.object_key,
        )

        # 更新 task
        task.upload_id = upload_id
        task.total_parts = total_parts
        task.part_size = part_size
        task.status = TaskStatus.MULTIPART_INIT
        task.part_etags = {}

        # 更新 audio
        audio = task.audio
        audio.upload_id = upload_id
        audio.upload_status = UploadStatus.UPLOADING
        audio.upload_total_parts = total_parts

        self.db.commit()

        return MultipartInitResponse(
            upload_id=upload_id,
            total_parts=total_parts,
            part_size=part_size,
        )

    def get_multipart_urls(
        self, job_id: str, task_id: str, part_numbers: list[int]
    ) -> MultipartUrlsResponse:
        """取得指定 parts 的 presigned URLs。"""
        task = self._get_task(job_id, task_id)

        if not task.upload_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart upload not initialized",
            )

        bucket = task.job.deployment.point.project.name
        parts = []

        for part_number in part_numbers:
            url = self.minio.generate_part_upload_url(
                bucket=bucket,
                key=task.object_key,
                upload_id=task.upload_id,
                part_number=part_number,
                expires_in=3600,
            )
            parts.append(
                MultipartPartUrl(
                    part_number=part_number,
                    presigned_url=url,
                )
            )

        return MultipartUrlsResponse(parts=parts)

    def mark_part_complete(
        self, job_id: str, task_id: str, part_number: int, etag: str
    ) -> None:
        """标记单一 part 上传完成。"""
        task = self._get_task(job_id, task_id)

        if not task.part_etags:
            task.part_etags = {}

        # 记录 etag
        task.part_etags[str(part_number)] = etag
        task.completed_parts = len(task.part_etags)
        task.status = TaskStatus.UPLOADING

        # 更新 audio 进度
        audio = task.audio
        audio.upload_progress = task.completed_parts

        self.db.commit()

    def complete_multipart(
        self, job_id: str, task_id: str, parts: list[PartCompleteRequest]
    ) -> None:
        """完成分段上传，更新 AudioInfo 状态。"""
        task = self._get_task(job_id, task_id)

        if not task.upload_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart upload not initialized",
            )

        bucket = task.job.deployment.point.project.name

        # 1. 向 MinIO 完成上传，取得 ETag
        etag = self.minio.complete_multipart_upload(
            bucket=bucket,
            key=task.object_key,
            upload_id=task.upload_id,
            parts=[{"PartNumber": p.part_number, "ETag": p.etag} for p in parts],
        )

        # 2. 更新 Task 状态
        task.status = TaskStatus.COMPLETED
        task.uploaded_at = datetime.now(UTC)
        task.completed_at = datetime.now(UTC)

        # 3. 更新 AudioInfo 状态 (已预先建立)
        audio = task.audio
        audio.upload_status = UploadStatus.COMPLETED
        audio.upload_id = None
        audio.upload_progress = task.total_parts
        audio.checksum = etag

        # 4. 讀取 WAV header，填入 metadata 並驗證
        try:
            header_data = self.minio.read_object_range(bucket, task.object_key, 0, 43)
            wav_info = parse_wav_header(header_data)

            if wav_info.is_valid:
                audio.fs = wav_info.sample_rate
                audio.audio_channels = wav_info.num_channels
                audio.record_duration = wav_info.duration_seconds

                warnings = []
                deployment = task.job.deployment

                if deployment.fs and wav_info.sample_rate != deployment.fs:
                    warnings.append(
                        f"SampleRate: header={wav_info.sample_rate},"
                        f" expected={deployment.fs}"
                    )

                expected_bits = (
                    deployment.recorder.bits if deployment.recorder.bits else 16
                )
                if wav_info.bits_per_sample != expected_bits:
                    warnings.append(
                        f"BitsPerSample: header={wav_info.bits_per_sample},"
                        f" expected={expected_bits}"
                    )

                expected_byte_rate = (
                    wav_info.sample_rate
                    * wav_info.num_channels
                    * wav_info.bits_per_sample
                    // 8
                )
                if wav_info.byte_rate != expected_byte_rate:
                    warnings.append(
                        f"ByteRate: header={wav_info.byte_rate},"
                        f" calculated={expected_byte_rate}"
                    )

                if warnings:
                    audio.header_warning = "; ".join(warnings)
        except Exception:
            logger.warning(f"Failed to validate WAV header for {task.object_key}")

        # 4. 更新 Job 计数
        job = task.job
        job.uploaded_count += 1
        job.completed_count += 1

        if job.status == JobStatus.PENDING:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(UTC)

        # 检查是否全部完成
        if job.completed_count >= job.total_files:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)

        self.db.commit()
        logger.info(f"Completed multipart upload for task {task_id}")

    def abort_multipart(self, job_id: str, task_id: str) -> None:
        """取消分段上传。"""
        task = self._get_task(job_id, task_id)

        if task.upload_id:
            bucket = task.job.deployment.point.project.name
            self.minio.abort_multipart_upload(
                bucket=bucket,
                key=task.object_key,
                upload_id=task.upload_id,
            )

        task.upload_id = None
        task.part_etags = None
        task.completed_parts = 0
        task.status = TaskStatus.PENDING

        # 重置 audio 状态
        audio = task.audio
        audio.upload_id = None
        audio.upload_status = UploadStatus.PENDING
        audio.upload_progress = 0

        self.db.commit()

    def get_task_progress(self, job_id: str, task_id: str) -> TaskProgressResponse:
        """取得单一档案的上传进度 (用于断点续传)。"""
        task = self._get_task(job_id, task_id)

        completed_parts = (
            sorted([int(p) for p in task.part_etags.keys()])
            if task.part_etags
            else []
        )

        remaining_parts = [
            p
            for p in range(1, (task.total_parts or 0) + 1)
            if p not in completed_parts
        ]

        return TaskProgressResponse(
            task_id=task.id,
            file_name=task.file_name,
            status=task.status,
            upload_id=task.upload_id,
            part_size=task.part_size,
            total_parts=task.total_parts,
            completed_parts=completed_parts,
            remaining_parts=remaining_parts,
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_task(self, job_id: str, task_id: str) -> UploadTask:
        """取得 task，不存在则 404。"""
        task = (
            self.db.query(UploadTask)
            .filter(
                UploadTask.id == task_id,
                UploadTask.job_id == job_id,
            )
            .first()
        )

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        return task

    def _job_to_status_response(self, job: UploadJob) -> UploadJobStatusResponse:
        """将 UploadJob 转换为 UploadJobStatusResponse。"""
        total = job.total_files
        percentage = (job.completed_count / total * 100) if total > 0 else 0

        tasks_info = [
            TaskStatusInfo(
                task_id=t.id,
                file_name=t.file_name,
                status=t.status,
                completed_parts=t.completed_parts or 0,
                total_parts=t.total_parts,
            )
            for t in job.tasks
        ]

        return UploadJobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=UploadJobProgress(
                total=total,
                uploaded=job.uploaded_count,
                completed=job.completed_count,
                failed=job.failed_count,
                percentage=round(percentage, 1),
            ),
            tasks=tasks_info,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_remaining=None,
        )
