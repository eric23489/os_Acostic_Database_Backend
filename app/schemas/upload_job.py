"""
上传任务 Schema。

用于批量音档上传的请求和响应模型。
"""

import re
from datetime import datetime

from pydantic import BaseModel, field_validator


class FileInfo(BaseModel):
    """单一档案资讯。"""

    name: str  # 档名格式: 7505.240611130000.wav
    size: int | None = None
    checksum: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """驗證檔名格式: {recorder_id}.{12位時間戳}[.{副檔名}]"""
        if not re.match(r"^\d+\.\d{12}(\.\w+)?$", v):
            raise ValueError(
                "Invalid filename format. Expected: {recorder_id}.{YYMMDDHHmmss}[.ext] "
                "(e.g., 7505.240611130000.wav)"
            )
        return v


class SkippedFileInfo(BaseModel):
    """被跳過的檔案資訊。"""

    name: str
    reason: str


class UploadJobCreateRequest(BaseModel):
    """建立上传任务请求。"""

    deployment_id: int
    priority: int = 5  # 0=高, 9=低
    files: list[FileInfo]

    @field_validator("files")
    @classmethod
    def validate_files(cls, v: list[FileInfo]) -> list[FileInfo]:
        if len(v) == 0:
            raise ValueError("At least 1 file required")
        if len(v) > 1000:
            raise ValueError("Maximum 1000 files per job")
        return v


class UploadTaskInfo(BaseModel):
    """上传子任务资讯。"""

    task_id: str
    audio_id: int  # 预先建立的 AudioInfo ID
    file_name: str
    object_key: str


class UploadJobCreateResponse(BaseModel):
    """建立上传任务响应。"""

    job_id: str
    deployment_id: int
    status: str
    total_files: int
    tasks: list[UploadTaskInfo]
    skipped_files: list[SkippedFileInfo] = []


class TaskCompleteRequest(BaseModel):
    """通知档案上传完成请求。"""

    etag: str | None = None
    file_size: int | None = None


class UploadJobProgress(BaseModel):
    """上传任务进度。"""

    total: int
    uploaded: int
    completed: int
    failed: int
    percentage: float


class TaskStatusInfo(BaseModel):
    """子任务状态资讯。"""

    task_id: str
    file_name: str
    status: str
    completed_parts: int
    total_parts: int | None


class UploadJobStatusResponse(BaseModel):
    """上传任务状态响应。"""

    job_id: str
    status: str
    progress: UploadJobProgress
    tasks: list[TaskStatusInfo]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    estimated_remaining: str | None


# =============================================================================
# Multipart Upload Schemas
# =============================================================================


class MultipartInitResponse(BaseModel):
    """初始化分段上传响应。"""

    upload_id: str
    total_parts: int
    part_size: int
    checksum_algorithm: str = "SHA256"


class MultipartUrlsRequest(BaseModel):
    """请求 part presigned URLs。"""

    part_numbers: list[int]


class MultipartPartUrl(BaseModel):
    """单一 part 的 presigned URL。"""

    part_number: int
    presigned_url: str


class MultipartUrlsResponse(BaseModel):
    """Part presigned URLs 响应。"""

    parts: list[MultipartPartUrl]


class PartCompleteRequest(BaseModel):
    """通知单一 part 上传完成请求。"""

    part_number: int
    etag: str
    checksum_sha256: str | None = None


class MultipartCompleteRequest(BaseModel):
    """完成分段上传请求。"""

    parts: list[PartCompleteRequest]


class TaskProgressResponse(BaseModel):
    """单一档案上传进度响应 (用于断点续传)。"""

    task_id: str
    file_name: str
    status: str
    upload_id: str | None
    part_size: int | None
    total_parts: int | None
    completed_parts: list[int]
    remaining_parts: list[int]
