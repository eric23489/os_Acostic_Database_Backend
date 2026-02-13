# Batch Audio Upload - 佇列方案 + 分段上傳

## 實作狀態

| Phase | 內容 | 狀態 |
|-------|------|------|
| **0.5** | 路徑生成工具 (audio_path.py) | 完成 |
| **1** | Docker + Redis + Celery 設定 | 完成 |
| **2** | Model (UploadJob, UploadTask) + Migration | 完成 |
| **2.5** | MinIO Service (Multipart 方法) | 完成 |
| **3** | Schema (Job + Multipart + 檔名驗證) | 完成 |
| **4** | UploadJob Service (含 Multipart) | 完成 |
| **5** | API Endpoints (Job + Multipart) | 完成 |
| **6** | Celery Tasks | 完成 |
| **7** | 測試 | 完成 |
| **8** | Audio 下載端點 | 完成 |

**測試結果**: 整合測試 8 passed (含 4 個下載測試)

**重要修正**:
- ForeignKey 參照修正: `ForeignKey("users.id")` -> `ForeignKey("user_info.id")`

---

## 概述
使用 Redis + Celery 佇列架構處理大量檔案上傳 (800+ 檔案，每檔 1.29GB)。
- **先建 AudioInfo**: 上傳前批量建立記錄，提前驗證
- **分段上傳**: 每段 100MB，失敗只需重傳該段
- **斷點續傳**: 記錄已完成的 parts，可從中斷點繼續
- **優先級控制**: 上傳不阻塞其他 MinIO 操作
- **孤兒清理**: 7 天未完成的記錄自動清理

---

## 架構圖

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  前端    │    │  後端    │    │  Redis   │    │  Worker  │    │  MinIO   │
│          │───>│ (FastAPI)│───>│  Queue   │───>│ (Celery) │───>│          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │                                               │
     │                                               │
     └───────────── 直接上傳 (presigned URL) ────────┘
```

---

## 新增元件

| 元件 | 用途 | Docker Image |
|------|------|--------------|
| Redis | 訊息佇列 + 任務狀態 | `redis:7-alpine` |
| Celery Worker | 背景任務處理 | 自建 (同 app image) |
| Celery Beat | 定時任務 (清理) | 自建 (同 app image) |

---

## 修改檔案

| 檔案 | 變更 | 狀態 |
|------|------|------|
| `docker-compose.yml` | +3 services (redis, celery-worker, celery-beat) | 完成 |
| `requirements.txt` | +celery[redis], +redis | 完成 |
| `app/core/celery_app.py` | 新增 Celery 設定 | 完成 |
| `app/enums/enums.py` | +UploadStatus, +JobStatus, +TaskStatus | 完成 |
| `app/models/upload_job.py` | 新增 UploadJob, UploadTask Model | 完成 |
| `app/models/__init__.py` | 註冊新 Model | 完成 |
| `app/schemas/upload_job.py` | 新增 Job + Multipart Schema | 完成 |
| `app/utils/audio_path.py` | 新增路徑生成 + 檔名解析工具 | 完成 |
| `app/models/audio.py` | +upload_status, +upload_id 欄位 | 完成 |
| `app/services/minio_service.py` | +4 Multipart 方法, +create_bucket | 完成 |
| `app/services/upload_job_service.py` | 新增 Service (含 Multipart) | 完成 |
| `app/tasks/audio_tasks.py` | 新增 Celery Tasks | 完成 |
| `app/api/v1/endpoints/api_upload_jobs.py` | 新增 API (Job + Multipart) | 完成 |
| `app/api/v1/api.py` | 註冊新 router | 完成 |
| `alembic/versions/2026_02_12_add_upload_jobs.py` | Migration | 完成 |
| `tests/test_audio_path.py` | 路徑工具測試 (10 tests) | 完成 |
| `tests/test_upload_job_schema.py` | Schema 測試 (12 tests) | 完成 |

---

## MinIO 路徑結構

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Object Key 結構                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Bucket: {ProjectInfo.name}                                                 │
│                                                                             │
│  Object Key: {Point_Name}/{YYYY}/{MM}/Raw_Data/{Filename}                  │
│                                                                             │
│  範例:                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Bucket: taiwanpower2nd                                              │   │
│  │  Key: TPC01/2024/06/Raw_Data/7505.240611130000.wav                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  完整路徑: taiwanpower2nd/TPC01/2024/06/Raw_Data/7505.240611130000.wav     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Filename 格式解析                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Filename: 7505.240611130000.wav                                           │
│            ││││ ││││││││││││                                               │
│            ││││ ││││││││││└─ 秒 (SS)                                       │
│            ││││ ││││││││└─── 分 (MM)                                       │
│            ││││ ││││││└───── 時 (HH)                                       │
│            ││││ ││││└─────── 日 (DD)                                       │
│            ││││ ││└───────── 月 (MM) → 用於路徑                            │
│            ││││ └─────────── 年 (YY) → 20YY 用於路徑                       │
│            │└──────────────── RecorderInfo.sn                              │
│                                                                             │
│  解析結果:                                                                  │
│  - recorder_sn: 7505                                                        │
│  - record_time: 2024-06-11 13:00:00                                        │
│  - path_year: 2024                                                          │
│  - path_month: 06                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## AudioInfo Model 變更

```python
# app/models/audio.py (新增欄位)
from app.enums.enums import UploadStatus

class AudioInfo(Base):
    # ... 現有欄位保持不變 ...

    # 新增上傳狀態追蹤
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    upload_status = Column(String(20), default=UploadStatus.COMPLETED, server_default="completed")
    upload_id = Column(String(100), nullable=True)      # Multipart upload_id
    upload_progress = Column(Integer, default=0)        # 已完成的 parts 數
    upload_total_parts = Column(Integer, nullable=True) # 總 parts 數
```

**Note**: `upload_status` 預設為 `COMPLETED` (server_default="completed")，確保舊資料相容性。新上傳的檔案會在建立時設為 `PENDING`。

---

## 流程變更：先建 AudioInfo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  新流程: 建立 Job 時同時批量建立 AudioInfo                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  POST /upload-jobs                                                         │
│  { deployment_id: 1, files: [800 個檔案資訊] }                             │
│                                                                             │
│  後端處理:                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. 驗證 deployment_id 存在且活躍                                    │   │
│  │ 2. 驗證所有檔名格式 (7505.240611130000.wav)                         │   │
│  │ 3. 檢查 object_key 重複 (活躍 + 軟刪除)                             │   │
│  │ 4. 批量建立 AudioInfo (upload_status = "pending")                   │   │
│  │ 5. 建立 UploadJob                                                   │   │
│  │ 6. 建立 UploadTasks (關聯 audio_id)                                │   │
│  │ 7. 產生 presigned URLs                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Response:                                                                  │
│  {                                                                          │
│    job_id: "xxx",                                                          │
│    tasks: [                                                                 │
│      { task_id: "t1", audio_id: 101, file_name: "...", presigned_url: "..." },│
│      { task_id: "t2", audio_id: 102, file_name: "...", presigned_url: "..." },│
│      ...                                                                    │
│    ]                                                                        │
│  }                                                                          │
│                                                                             │
│  好處:                                                                      │
│  - 上傳前就驗證完成                                                        │
│  - 前端立即取得 audio_id                                                   │
│  - 重複檔案立即拒絕 (不浪費上傳時間)                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 孤兒記錄清理

```python
# app/tasks/audio_tasks.py

@shared_task
def cleanup_abandoned_audio_records():
    """
    清理超過 7 天仍為 pending/uploading 的 AudioInfo 記錄
    Celery Beat: 每天執行一次
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)

        stale_records = db.query(AudioInfo).filter(
            AudioInfo.upload_status.in_([UploadStatus.PENDING, UploadStatus.UPLOADING]),
            AudioInfo.created_at < cutoff,
        ).all()

        for record in stale_records:
            # 1. 清理 MinIO 殘留的 multipart upload
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

            # 2. 硬刪除記錄 (不是軟刪除，因為從未完成)
            db.delete(record)

        db.commit()
        logger.info(f"Cleaned up {len(stale_records)} abandoned audio records")

    finally:
        db.close()

# Celery Beat 排程
celery_app.conf.beat_schedule["cleanup-abandoned-audio"] = {
    "task": "app.tasks.audio_tasks.cleanup_abandoned_audio_records",
    "schedule": crontab(hour=3, minute=0),  # 每天凌晨 3 點
}
```

---

## Phase 0: Project 建立 Bucket

```python
# app/services/project_service.py (修改 create_project)

def create_project(self, project: ProjectCreate) -> ProjectInfo:
    """建立專案，同時建立 MinIO bucket"""
    # ... 現有驗證邏輯 ...

    db_project = ProjectInfo(**project.model_dump())
    self.db.add(db_project)
    self.db.commit()
    self.db.refresh(db_project)

    # 建立 MinIO bucket
    try:
        minio_service = MinioService()
        minio_service.create_bucket(db_project.name)
    except Exception as e:
        logger.warning(f"Failed to create bucket {db_project.name}: {e}")
        # 不 rollback，bucket 可稍後手動建立

    return db_project

# app/services/minio_service.py (新增方法)

def create_bucket(self, bucket_name: str) -> None:
    """建立 bucket (如果不存在)"""
    try:
        self.s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        self.s3_client.create_bucket(Bucket=bucket_name)
```

---

## Phase 0.5: 路徑生成工具

```python
# app/utils/audio_path.py

import re
from datetime import datetime
from dataclasses import dataclass

@dataclass
class AudioFileInfo:
    """解析檔名後的資訊"""
    recorder_sn: str
    record_time: datetime
    extension: str

def parse_audio_filename(filename: str) -> AudioFileInfo:
    """
    解析音檔檔名，取得錄音機序號和錄製時間。

    Args:
        filename: 檔名，格式為 "7505.240611130000.wav"

    Returns:
        AudioFileInfo: 包含 recorder_sn, record_time, extension

    Raises:
        ValueError: 檔名格式不符
    """
    # 支援 "7505.240611130000.wav" 或 "7505.240611130000"
    pattern = r'^(\d+)\.(\d{12})(?:\.(\w+))?$'
    match = re.match(pattern, filename)

    if not match:
        raise ValueError(f"Invalid filename format: {filename}")

    recorder_sn = match.group(1)
    timestamp_str = match.group(2)  # "240611130000"
    extension = match.group(3) or "wav"

    # 解析時間戳
    year = 2000 + int(timestamp_str[0:2])   # 24 -> 2024
    month = int(timestamp_str[2:4])          # 06
    day = int(timestamp_str[4:6])            # 11
    hour = int(timestamp_str[6:8])           # 13
    minute = int(timestamp_str[8:10])        # 00
    second = int(timestamp_str[10:12])       # 00

    record_time = datetime(year, month, day, hour, minute, second)

    return AudioFileInfo(
        recorder_sn=recorder_sn,
        record_time=record_time,
        extension=extension,
    )

def generate_object_key(point_name: str, filename: str) -> str:
    """
    生成 MinIO object key。

    Args:
        point_name: PointInfo.name (如 "TPC01")
        filename: 檔名 (如 "7505.240611130000.wav")

    Returns:
        object_key: 如 "TPC01/2024/06/Raw_Data/7505.240611130000.wav"
    """
    info = parse_audio_filename(filename)

    year = info.record_time.strftime("%Y")  # "2024"
    month = info.record_time.strftime("%m")  # "06"

    return f"{point_name}/{year}/{month}/Raw_Data/{filename}"

# 使用範例
# filename = "7505.240611130000.wav"
# point_name = "TPC01"
# object_key = generate_object_key(point_name, filename)
# → "TPC01/2024/06/Raw_Data/7505.240611130000.wav"
```

---

## Phase 1: 基礎設施

### 1.1 Docker Compose

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  celery-worker:
    build: .
    command: celery -A app.core.celery_app worker --loglevel=info --concurrency=4
    depends_on:
      - redis
      - db
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0

  celery-beat:
    build: .
    command: celery -A app.core.celery_app beat --loglevel=info
    depends_on:
      - redis

volumes:
  redis_data:
```

### 1.2 Celery 設定

```python
# app/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "audio_tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    # 優先級設定 (0=最高, 9=最低)
    task_default_priority=5,
    task_queue_max_priority=10,
    # 任務路由
    task_routes={
        "app.tasks.audio_tasks.process_high_priority": {"queue": "high"},
        "app.tasks.audio_tasks.create_audio_info_batch": {"queue": "normal"},
        "app.tasks.audio_tasks.cleanup_orphan_objects": {"queue": "low"},
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
```

---

## Phase 2: 資料模型

### 2.1 Enums (app/enums/enums.py)

```python
# app/enums/enums.py (新增)
from enum import StrEnum

class UploadStatus(StrEnum):
    """音檔上傳狀態"""
    PENDING = "pending"       # 已建立，等待上傳
    UPLOADING = "uploading"   # 上傳中 (有 parts 進度)
    COMPLETED = "completed"   # 上傳完成
    FAILED = "failed"         # 上傳失敗

class JobStatus(StrEnum):
    """上傳任務狀態"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskStatus(StrEnum):
    """上傳子任務狀態"""
    PENDING = "pending"             # 等待上傳
    MULTIPART_INIT = "multipart-init"  # 已初始化分段上傳 (注意: 使用 hyphen)
    UPLOADING = "uploading"         # 上傳中 (有 parts 進度)
    UPLOADED = "uploaded"           # 已上傳到 MinIO
    COMPLETED = "completed"         # 完成
    FAILED = "failed"               # 失敗
```

### 2.2 Model (app/models/upload_job.py)

```python
# app/models/upload_job.py
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.base import Base
from app.enums.enums import JobStatus, TaskStatus

class UploadJob(Base):
    __tablename__ = "upload_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    deployment_id = Column(Integer, ForeignKey("deployment_info.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False)  # 注意: 是 user_info 不是 users
    status = Column(String(20), default=JobStatus.PENDING)
    priority = Column(Integer, default=5)  # 0=高, 9=低

    total_files = Column(Integer, default=0)
    uploaded_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)  # 實作時改名
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    deployment = relationship("DeploymentInfo")
    user = relationship("UserInfo")
    tasks = relationship("UploadTask", back_populates="job", cascade="all, delete-orphan")

class UploadTask(Base):
    __tablename__ = "upload_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id = Column(String(36), ForeignKey("upload_jobs.id"), nullable=False, index=True)

    file_name = Column(String(255), nullable=False)
    object_key = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)

    status = Column(String(20), default=TaskStatus.PENDING, index=True)
    presigned_url = Column(Text, nullable=True)
    url_expires_at = Column(DateTime(timezone=True), nullable=True)

    audio_id = Column(Integer, ForeignKey("audio_info.id"), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Multipart Upload 追蹤
    upload_id = Column(String(100), nullable=True)      # MinIO multipart upload_id
    total_parts = Column(Integer, nullable=True)        # 總段數 (1.29GB / 100MB = 13)
    completed_parts = Column(Integer, default=0)        # 已完成段數
    part_size = Column(Integer, default=104857600)      # 每段大小 (預設 100MB)
    part_etags = Column(JSON, nullable=True)            # {"1": "etag1", "2": "etag2", ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("UploadJob", back_populates="tasks")
    audio = relationship("AudioInfo")
```

### 2.3 Schema

```python
# app/schemas/upload_job.py
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class FileInfo(BaseModel):
    name: str  # 檔名格式: 7505.240611130000.wav
    size: Optional[int] = None
    checksum: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_filename_format(cls, v: str) -> str:
        """驗證檔名格式符合 {sn}.{YYMMDDHHMMSS}.wav"""
        import re
        pattern = r'^\d+\.\d{12}(?:\.\w+)?$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid filename format: {v}. "
                "Expected: {recorder_sn}.{YYMMDDHHMMSS}.{ext}"
            )
        return v

class UploadJobCreateRequest(BaseModel):
    deployment_id: int
    priority: Optional[int] = 5  # 0=高, 9=低
    files: List[FileInfo]

    @field_validator("files")
    @classmethod
    def validate_files(cls, v):
        if len(v) == 0:
            raise ValueError("At least 1 file required")
        if len(v) > 1000:
            raise ValueError("Maximum 1000 files per job")
        return v

class UploadTaskInfo(BaseModel):
    task_id: str
    audio_id: int  # 預先建立的 AudioInfo ID
    file_name: str
    object_key: str

class UploadJobCreateResponse(BaseModel):
    job_id: str
    deployment_id: int
    status: str
    total_files: int
    tasks: List[UploadTaskInfo]

class TaskCompleteRequest(BaseModel):
    etag: Optional[str] = None
    file_size: Optional[int] = None

class UploadJobProgress(BaseModel):
    total: int
    uploaded: int
    db_created: int
    failed: int
    percentage: float

class TaskStatusInfo(BaseModel):
    task_id: str
    file_name: str
    status: str
    completed_parts: int
    total_parts: Optional[int]

class UploadJobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: UploadJobProgress
    tasks: List[TaskStatusInfo]  # 用於斷點續傳比對
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_remaining: Optional[str]

# Multipart Upload Schemas
class MultipartInitResponse(BaseModel):
    upload_id: str
    total_parts: int
    part_size: int

class MultipartUrlsRequest(BaseModel):
    part_numbers: List[int]  # 要取得 URL 的 part 編號

class MultipartPartUrl(BaseModel):
    part_number: int
    presigned_url: str

class MultipartUrlsResponse(BaseModel):
    parts: List[MultipartPartUrl]

class PartCompleteRequest(BaseModel):
    part_number: int
    etag: str

class MultipartCompleteRequest(BaseModel):
    parts: List[PartCompleteRequest]
```

---

## Phase 2.5: MinIO Service (Multipart 方法)

```python
# app/services/minio_service.py (新增方法)

def create_multipart_upload(self, bucket: str, key: str) -> str:
    """初始化分段上傳，回傳 upload_id"""
    response = self.s3_client.create_multipart_upload(
        Bucket=bucket,
        Key=key,
    )
    return response["UploadId"]

def generate_part_upload_url(
    self,
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    expires_in: int = 3600,
) -> str:
    """產生單一 part 的 presigned URL"""
    return self.s3_client.generate_presigned_url(
        ClientMethod="upload_part",
        Params={
            "Bucket": bucket,
            "Key": key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=expires_in,
    )

def complete_multipart_upload(
    self,
    bucket: str,
    key: str,
    upload_id: str,
    parts: list[dict],  # [{"PartNumber": 1, "ETag": "xxx"}, ...]
) -> None:
    """完成分段上傳，合併所有 parts"""
    self.s3_client.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )

def abort_multipart_upload(self, bucket: str, key: str, upload_id: str) -> None:
    """取消分段上傳，清理已上傳的 parts"""
    self.s3_client.abort_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
    )
```

---

## Phase 3: Celery Tasks

```python
# app/tasks/audio_tasks.py
from celery import shared_task
from celery.schedules import crontab
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.enums.enums import JobStatus, UploadStatus
from app.models.audio import AudioInfo
from app.models.upload_job import UploadJob, UploadTask
from app.services.minio_service import MinioService

import logging
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def finalize_completed_uploads(self, job_id: str):
    """
    Worker: 檢查並完成上傳任務

    注意: AudioInfo 已在建立 Job 時預先建立
    此 Task 用於處理需要後續處理的情況 (如驗證檔案完整性)
    """
    db: Session = SessionLocal()
    try:
        job = db.query(UploadJob).filter(UploadJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # 檢查是否全部完成
        completed_count = db.query(UploadTask).filter(
            UploadTask.job_id == job_id,
            UploadTask.status == "completed",
        ).count()

        if completed_count >= job.total_files:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            db.commit()
            logger.info(f"Job {job_id} completed: {completed_count} files")

    except Exception as e:
        db.rollback()
        logger.error(f"Error finalizing job: {e}")
        raise self.retry(exc=e)
    finally:
        db.close()

@shared_task
def cleanup_abandoned_audio_records():
    """
    清理超過 7 天仍為 pending/uploading 的 AudioInfo 記錄。

    Celery Beat: 每天凌晨 3 點執行
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
            # 1. 清理 MinIO 殘留的 multipart upload
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

            # 2. 硬刪除記錄 (不是軟刪除，因為從未完成)
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
    清理過期的 jobs (7天未完成)。

    每小時執行一次
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
            # 清理 MinIO 孤兒物件
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
                        logger.warning(f"Failed to abort multipart for task {task.id}: {e}")

            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(UTC)

        db.commit()
        logger.info(f"Cleaned up {len(expired_jobs)} expired jobs")

    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up expired jobs: {e}")
    finally:
        db.close()


# Celery Beat 排程
celery_app.conf.beat_schedule = {
    "cleanup-abandoned-audio": {
        "task": "app.tasks.audio_tasks.cleanup_abandoned_audio_records",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨 3 點
    },
    "cleanup-expired-jobs": {
        "task": "app.tasks.audio_tasks.cleanup_expired_jobs",
        "schedule": 3600.0,  # 每小時
    },
}
```

---

## Phase 4: Service

```python
# app/services/upload_job_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.upload_job import UploadJob, UploadTask, JobStatus, TaskStatus
from app.models.deployment import DeploymentInfo
from app.schemas.upload_job import (
    UploadJobCreateRequest,
    UploadJobCreateResponse,
    UploadTaskInfo,
    UploadJobStatusResponse,
    UploadJobProgress,
)
from app.services.minio_service import MinioService

class UploadJobService:
    def __init__(self, db: Session):
        self.db = db
        self.minio = MinioService()

    def create_job(
        self,
        request: UploadJobCreateRequest,
        user_id: int,
    ) -> UploadJobCreateResponse:
        """建立上傳任務，同時批量建立 AudioInfo"""

        from app.utils.audio_path import generate_object_key, parse_audio_filename

        # 1. 驗證 deployment
        deployment = self.db.query(DeploymentInfo).filter(
            DeploymentInfo.id == request.deployment_id,
            DeploymentInfo.is_deleted.is_(False),
        ).first()

        if not deployment:
            raise HTTPException(404, "Deployment not found")

        bucket = deployment.point.project.name

        # 2. 生成所有 object_keys 並檢查重複
        object_keys = []
        for file_info in request.files:
            object_key = generate_object_key(deployment.point.name, file_info.name)
            object_keys.append(object_key)

        # 檢查活躍記錄重複
        existing_active = self.db.query(AudioInfo.object_key).filter(
            AudioInfo.object_key.in_(object_keys),
            AudioInfo.is_deleted.is_(False),
        ).all()

        if existing_active:
            duplicates = [r[0] for r in existing_active]
            raise HTTPException(400, f"Files already exist: {duplicates[:5]}...")

        # 檢查軟刪除記錄佔用
        existing_deleted = self.db.query(AudioInfo.object_key).filter(
            AudioInfo.object_key.in_(object_keys),
            AudioInfo.is_deleted.is_(True),
        ).all()

        if existing_deleted:
            reserved = [r[0] for r in existing_deleted]
            raise HTTPException(400, f"Files reserved by deleted records: {reserved[:5]}...")

        # 3. 批量建立 AudioInfo (upload_status = pending)
        audio_map = {}  # object_key -> AudioInfo

        for file_info in request.files:
            object_key = generate_object_key(deployment.point.name, file_info.name)
            parsed = parse_audio_filename(file_info.name)

            audio = AudioInfo(
                deployment_id=request.deployment_id,
                file_name=file_info.name,
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
            total_files=len(request.files),
            status=JobStatus.PENDING,
        )
        self.db.add(job)
        self.db.flush()

        # 5. 建立 Tasks (關聯 audio_id)
        tasks_info = []
        url_expires_at = datetime.utcnow() + timedelta(hours=24)

        for file_info in request.files:
            object_key = generate_object_key(deployment.point.name, file_info.name)
            audio = audio_map[object_key]

            task = UploadTask(
                job_id=job.id,
                audio_id=audio.id,  # 關聯到剛建立的 AudioInfo
                file_name=file_info.name,
                object_key=object_key,
                file_size=file_info.size,
                checksum=file_info.checksum,
                url_expires_at=url_expires_at,
            )
            self.db.add(task)

            tasks_info.append(UploadTaskInfo(
                task_id=task.id,
                audio_id=audio.id,
                file_name=file_info.name,
                object_key=object_key,
            ))

        self.db.commit()

        return UploadJobCreateResponse(
            job_id=job.id,
            deployment_id=request.deployment_id,
            status=job.status,
            total_files=job.total_files,
            tasks=tasks_info,
        )

    def mark_task_uploaded(
        self,
        job_id: str,
        task_id: str,
        etag: str = None,
        file_size: int = None,
    ) -> None:
        """標記單一檔案已上傳完成"""

        task = self.db.query(UploadTask).filter(
            UploadTask.id == task_id,
            UploadTask.job_id == job_id,
        ).first()

        if not task:
            raise HTTPException(404, "Task not found")

        if task.status != TaskStatus.PENDING:
            return  # 冪等性：已處理過

        task.status = TaskStatus.UPLOADED
        task.uploaded_at = datetime.utcnow()
        if file_size:
            task.file_size = file_size

        # 更新 job 計數
        job = task.job
        job.uploaded_count += 1

        if job.status == JobStatus.PENDING:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()

        self.db.commit()

        # 檢查是否湊滿一批，放入佇列
        self._check_and_queue_batch(job_id)

    def _check_and_queue_batch(self, job_id: str, batch_size: int = 50):
        """檢查是否有足夠的已上傳 tasks，放入佇列"""
        from app.tasks.audio_tasks import create_audio_info_batch

        uploaded_tasks = self.db.query(UploadTask).filter(
            UploadTask.job_id == job_id,
            UploadTask.status == TaskStatus.UPLOADED,
        ).limit(batch_size).all()

        if len(uploaded_tasks) >= batch_size:
            task_ids = [t.id for t in uploaded_tasks]

            for task in uploaded_tasks:
                task.status = TaskStatus.QUEUED
            self.db.commit()

            # 放入 Celery 佇列
            create_audio_info_batch.delay(job_id, task_ids)

    def get_job_status(self, job_id: str) -> UploadJobStatusResponse:
        """查詢任務進度"""

        job = self.db.query(UploadJob).filter(UploadJob.id == job_id).first()

        if not job:
            raise HTTPException(404, "Job not found")

        total = job.total_files
        percentage = (job.db_created_count / total * 100) if total > 0 else 0

        # 估算剩餘時間
        estimated = None
        if job.started_at and job.db_created_count > 0:
            elapsed = (datetime.utcnow() - job.started_at).total_seconds()
            rate = job.db_created_count / elapsed  # files per second
            remaining = total - job.db_created_count
            if rate > 0:
                remaining_seconds = remaining / rate
                hours = int(remaining_seconds // 3600)
                minutes = int((remaining_seconds % 3600) // 60)
                estimated = f"{hours}h {minutes}m"

        # 取得所有 tasks 狀態 (用於斷點續傳)
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
                db_created=job.db_created_count,
                failed=job.failed_count,
                percentage=round(percentage, 1),
            ),
            tasks=tasks_info,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_remaining=estimated,
        )

    def cancel_job(self, job_id: str) -> None:
        """取消任務"""
        job = self.db.query(UploadJob).filter(UploadJob.id == job_id).first()

        if not job:
            raise HTTPException(404, "Job not found")

        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            return

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        self.db.commit()

    # ============================================
    # Multipart Upload Methods
    # ============================================

    def init_multipart(self, job_id: str, task_id: str) -> MultipartInitResponse:
        """初始化分段上傳"""
        task = self._get_task(job_id, task_id)

        if task.upload_id:
            # 已初始化，回傳現有資訊 (冪等)
            return MultipartInitResponse(
                upload_id=task.upload_id,
                total_parts=task.total_parts,
                part_size=task.part_size,
            )

        # 計算分段
        file_size = task.file_size or 0
        part_size = 100 * 1024 * 1024  # 100MB
        total_parts = (file_size + part_size - 1) // part_size  # 向上取整
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
        self.db.commit()

        return MultipartInitResponse(
            upload_id=upload_id,
            total_parts=total_parts,
            part_size=part_size,
        )

    def get_multipart_urls(
        self, job_id: str, task_id: str, part_numbers: list[int]
    ) -> MultipartUrlsResponse:
        """取得指定 parts 的 presigned URLs"""
        task = self._get_task(job_id, task_id)

        if not task.upload_id:
            raise HTTPException(400, "Multipart upload not initialized")

        bucket = task.job.deployment.point.project.name
        parts = []

        for part_number in part_numbers:
            url = self.minio.generate_part_upload_url(
                bucket=bucket,
                key=task.object_key,
                upload_id=task.upload_id,
                part_number=part_number,
                expires_in=3600,  # 1 hour
            )
            parts.append(MultipartPartUrl(
                part_number=part_number,
                presigned_url=url,
            ))

        return MultipartUrlsResponse(parts=parts)

    def mark_part_complete(
        self, job_id: str, task_id: str, part_number: int, etag: str
    ) -> None:
        """標記單一 part 上傳完成"""
        task = self._get_task(job_id, task_id)

        if not task.part_etags:
            task.part_etags = {}

        # 記錄 etag
        task.part_etags[str(part_number)] = etag
        task.completed_parts = len(task.part_etags)
        task.status = TaskStatus.UPLOADING

        self.db.commit()

    def complete_multipart(
        self, job_id: str, task_id: str, parts: list[PartCompleteRequest]
    ) -> None:
        """完成分段上傳，更新 AudioInfo 狀態"""
        task = self._get_task(job_id, task_id)

        if not task.upload_id:
            raise HTTPException(400, "Multipart upload not initialized")

        bucket = task.job.deployment.point.project.name

        # 1. 向 MinIO 完成上傳
        self.minio.complete_multipart_upload(
            bucket=bucket,
            key=task.object_key,
            upload_id=task.upload_id,
            parts=[{"PartNumber": p.part_number, "ETag": p.etag} for p in parts],
        )

        # 2. 更新 Task 狀態
        task.status = TaskStatus.UPLOADED
        task.uploaded_at = datetime.utcnow()

        # 3. 更新 AudioInfo 狀態 (已預先建立)
        audio = task.audio
        audio.upload_status = UploadStatus.COMPLETED
        audio.upload_id = None  # 清除 upload_id
        audio.upload_progress = task.total_parts

        # 可選: 從 MinIO 取得實際檔案大小
        # actual_size = self.minio.get_object_size(bucket, task.object_key)
        # audio.file_size = actual_size

        # 4. 更新 Job 計數
        task.job.uploaded_count += 1
        task.job.db_created_count += 1  # AudioInfo 已在建立 Job 時建立

        if task.job.status == JobStatus.PENDING:
            task.job.status = JobStatus.PROCESSING
            task.job.started_at = datetime.utcnow()

        # 檢查是否全部完成
        if task.job.db_created_count >= task.job.total_files:
            task.job.status = JobStatus.COMPLETED
            task.job.completed_at = datetime.utcnow()

        self.db.commit()

    def abort_multipart(self, job_id: str, task_id: str) -> None:
        """取消分段上傳"""
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
        self.db.commit()

    def get_task_progress(self, job_id: str, task_id: str) -> dict:
        """取得單一檔案的上傳進度 (用於斷點續傳)"""
        task = self._get_task(job_id, task_id)

        completed_parts = list(task.part_etags.keys()) if task.part_etags else []

        return {
            "task_id": task.id,
            "file_name": task.file_name,
            "status": task.status,
            "upload_id": task.upload_id,
            "part_size": task.part_size,  # 前端需要此值來切割檔案
            "total_parts": task.total_parts,
            "completed_parts": sorted([int(p) for p in completed_parts]),
            "remaining_parts": [
                p for p in range(1, (task.total_parts or 0) + 1)
                if str(p) not in completed_parts
            ],
        }

    def _get_task(self, job_id: str, task_id: str) -> UploadTask:
        """取得 task，不存在則 404"""
        task = self.db.query(UploadTask).filter(
            UploadTask.id == task_id,
            UploadTask.job_id == job_id,
        ).first()

        if not task:
            raise HTTPException(404, "Task not found")

        return task
```

---

## Phase 5: API

```python
# app/api/v1/endpoints/api_upload_jobs.py
"""上傳任務 API"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import UserInfo
from app.schemas.upload_job import (
    MultipartInitResponse,
    MultipartUrlsRequest,
    MultipartUrlsResponse,
    PartCompleteRequest,
    MultipartCompleteRequest,
    TaskProgressResponse,
    UploadJobCreateRequest,
    UploadJobCreateResponse,
    UploadJobStatusResponse,
)
from app.services.upload_job_service import UploadJobService

router = APIRouter(prefix="/upload-jobs", tags=["Upload Jobs"])

@router.post("/", response_model=UploadJobCreateResponse, status_code=status.HTTP_201_CREATED)
def create_upload_job(
    request: UploadJobCreateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    建立上傳任務

    - 驗證 deployment 存在
    - 產生 presigned URLs (24小時有效)
    - 回傳任務 ID 和上傳 URLs
    """
    return UploadJobService(db).create_job(request, current_user.id)

@router.post("/{job_id}/tasks/{task_id}/complete")
def complete_upload_task(
    job_id: str,
    task_id: str,
    request: TaskCompleteRequest = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    通知單檔上傳完成

    - 前端上傳到 MinIO 後呼叫
    - 觸發 AudioInfo 建立 (湊滿 50 個批次處理)
    """
    UploadJobService(db).mark_task_uploaded(
        job_id=job_id,
        task_id=task_id,
        etag=request.etag if request else None,
        file_size=request.file_size if request else None,
    )
    return {"status": "ok"}

@router.get("/{job_id}", response_model=UploadJobStatusResponse)
def get_upload_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """查詢上傳任務進度"""
    return UploadJobService(db).get_job_status(job_id)

@router.post("/{job_id}/cancel")
def cancel_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """取消上傳任務"""
    UploadJobService(db).cancel_job(job_id)
    return {"status": "cancelled"}

@router.get("/", response_model=list[UploadJobStatusResponse])
def list_upload_jobs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """列出使用者的上傳任務"""
    return UploadJobService(db).list_jobs(current_user.id, skip, limit)

# ============================================
# Multipart Upload API (分段上傳)
# ============================================

@router.post("/{job_id}/tasks/{task_id}/multipart/init", response_model=MultipartInitResponse)
def init_multipart_upload(
    job_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    初始化分段上傳

    - 計算總段數 (file_size / 100MB)
    - 向 MinIO 發起 create_multipart_upload
    - 回傳 upload_id 和分段資訊
    """
    return UploadJobService(db).init_multipart(job_id, task_id)

@router.post("/{job_id}/tasks/{task_id}/multipart/urls", response_model=MultipartUrlsResponse)
def get_multipart_urls(
    job_id: str,
    task_id: str,
    request: MultipartUrlsRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    取得指定 parts 的 presigned URLs

    - 前端可分批請求 (例如一次 5 個)
    - 支援重試失敗的 parts
    """
    return UploadJobService(db).get_multipart_urls(job_id, task_id, request.part_numbers)

@router.post("/{job_id}/tasks/{task_id}/multipart/part-complete")
def complete_part(
    job_id: str,
    task_id: str,
    request: PartCompleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    通知單一 part 上傳完成

    - 記錄 etag
    - 更新進度 (completed_parts)
    """
    UploadJobService(db).mark_part_complete(job_id, task_id, request.part_number, request.etag)
    return {"status": "ok"}

@router.post("/{job_id}/tasks/{task_id}/multipart/complete")
def complete_multipart_upload(
    job_id: str,
    task_id: str,
    request: MultipartCompleteRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    完成分段上傳

    - 向 MinIO 發起 complete_multipart_upload
    - 標記 task 為 UPLOADED
    - 觸發 AudioInfo 建立佇列
    """
    UploadJobService(db).complete_multipart(job_id, task_id, request.parts)
    return {"status": "ok"}

@router.post("/{job_id}/tasks/{task_id}/multipart/abort")
def abort_multipart_upload(
    job_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    取消分段上傳

    - 向 MinIO 發起 abort_multipart_upload
    - 清理已上傳的 parts
    """
    UploadJobService(db).abort_multipart(job_id, task_id)
    return {"status": "aborted"}

@router.get("/{job_id}/tasks/{task_id}/progress")
def get_task_progress(
    job_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    取得單一檔案的上傳進度

    - 用於斷點續傳：查詢已完成的 parts
    """
    return UploadJobService(db).get_task_progress(job_id, task_id)
```

---

## 佇列優先級

| 佇列 | 優先級 | 用途 |
|------|--------|------|
| `high` | 0-3 | 下載請求、API 查詢 |
| `normal` | 4-6 | 建立 AudioInfo |
| `low` | 7-9 | 清理孤兒物件、過期任務 |

---

## 前端流程 (分段上傳)

```javascript
const PART_SIZE = 100 * 1024 * 1024;  // 100MB
const CONCURRENT_PARTS = 3;            // 每檔同時上傳 3 段
const CONCURRENT_FILES = 3;            // 同時上傳 3 個檔案

async function uploadFiles(deploymentId, files) {
  // 1. 建立上傳任務
  const { job_id, tasks } = await fetch('/api/v1/upload-jobs', {
    method: 'POST',
    body: JSON.stringify({
      deployment_id: deploymentId,
      files: files.map(f => ({ name: f.name, size: f.size }))
    })
  }).then(r => r.json());

  // 2. 並行上傳檔案 (每次 3 個)
  const fileLimit = pLimit(CONCURRENT_FILES);

  await Promise.all(tasks.map(task => fileLimit(async () => {
    const file = files.find(f => f.name === task.file_name);
    await uploadFileWithMultipart(job_id, task.task_id, file);
  })));

  // 3. 輪詢進度 (略)
}

async function uploadFileWithMultipart(jobId, taskId, file) {
  const baseUrl = `/api/v1/upload-jobs/${jobId}/tasks/${taskId}`;

  // Step 1: 初始化分段上傳
  const { upload_id, total_parts, part_size } = await fetch(
    `${baseUrl}/multipart/init`,
    { method: 'POST' }
  ).then(r => r.json());

  // Step 2: 檢查斷點續傳 (已完成的 parts)
  const { completed_parts, remaining_parts } = await fetch(
    `${baseUrl}/progress`
  ).then(r => r.json());

  // Step 3: 上傳剩餘的 parts
  const partLimit = pLimit(CONCURRENT_PARTS);

  await Promise.all(remaining_parts.map(partNumber => partLimit(async () => {
    // 取得該 part 的 presigned URL
    const { parts } = await fetch(`${baseUrl}/multipart/urls`, {
      method: 'POST',
      body: JSON.stringify({ part_numbers: [partNumber] })
    }).then(r => r.json());

    const url = parts[0].presigned_url;

    // 切割檔案
    const start = (partNumber - 1) * part_size;
    const end = Math.min(start + part_size, file.size);
    const blob = file.slice(start, end);

    // 上傳到 MinIO
    const response = await fetch(url, {
      method: 'PUT',
      body: blob,
    });

    const etag = response.headers.get('ETag').replace(/"/g, '');

    // 通知後端該 part 完成
    await fetch(`${baseUrl}/multipart/part-complete`, {
      method: 'POST',
      body: JSON.stringify({ part_number: partNumber, etag })
    });
  })));

  // Step 4: 完成分段上傳
  const { completed_parts: allParts } = await fetch(`${baseUrl}/progress`).then(r => r.json());

  // 取得所有 etags
  const partsWithEtags = await getPartsWithEtags(jobId, taskId);

  await fetch(`${baseUrl}/multipart/complete`, {
    method: 'POST',
    body: JSON.stringify({ parts: partsWithEtags })
  });
}

// 斷點續傳: 使用者全選檔案，自動比對跳過已完成
async function resumeUpload(jobId, files) {
  // 1. 取得所有 tasks 狀態
  const { tasks } = await fetch(`/api/v1/upload-jobs/${jobId}`).then(r => r.json());

  // 2. 建立檔名對照表
  const fileMap = new Map(files.map(f => [f.name, f]));

  // 3. 分類處理
  const toUpload = [];

  for (const task of tasks) {
    const file = fileMap.get(task.file_name);
    if (!file) {
      console.warn(`File not found: ${task.file_name}`);
      continue;
    }

    switch (task.status) {
      case 'db_created':
        // 已完成，跳過
        console.log(`Skipping completed: ${task.file_name}`);
        break;

      case 'uploading':
      case 'multipart_init':
        // 有進度，需要續傳
        toUpload.push({ task, file, resume: true });
        break;

      case 'pending':
      default:
        // 尚未開始
        toUpload.push({ task, file, resume: false });
        break;
    }
  }

  console.log(`Resuming: ${toUpload.length} files to upload`);

  // 4. 並行上傳
  const fileLimit = pLimit(CONCURRENT_FILES);

  await Promise.all(toUpload.map(({ task, file, resume }) =>
    fileLimit(async () => {
      if (resume) {
        // 續傳: 查詢已完成的 parts
        const { remaining_parts } = await fetch(
          `/api/v1/upload-jobs/${jobId}/tasks/${task.task_id}/progress`
        ).then(r => r.json());

        await uploadRemainingParts(jobId, task.task_id, file, remaining_parts);
      } else {
        // 從頭上傳
        await uploadFileWithMultipart(jobId, task.task_id, file);
      }
    })
  ));
}

async function uploadRemainingParts(jobId, taskId, file, remainingParts) {
  const baseUrl = `/api/v1/upload-jobs/${jobId}/tasks/${taskId}`;

  // 取得 part_size (從之前的 init)
  const { part_size } = await fetch(`${baseUrl}/progress`).then(r => r.json());

  const partLimit = pLimit(CONCURRENT_PARTS);

  await Promise.all(remainingParts.map(partNumber => partLimit(async () => {
    // 取得 presigned URL
    const { parts } = await fetch(`${baseUrl}/multipart/urls`, {
      method: 'POST',
      body: JSON.stringify({ part_numbers: [partNumber] })
    }).then(r => r.json());

    // 切割並上傳
    const start = (partNumber - 1) * part_size;
    const end = Math.min(start + part_size, file.size);
    const blob = file.slice(start, end);

    const response = await fetch(parts[0].presigned_url, {
      method: 'PUT',
      body: blob,
    });

    const etag = response.headers.get('ETag').replace(/"/g, '');

    await fetch(`${baseUrl}/multipart/part-complete`, {
      method: 'POST',
      body: JSON.stringify({ part_number: partNumber, etag })
    });
  })));

  // 完成上傳
  const { completed_parts } = await fetch(`${baseUrl}/progress`).then(r => r.json());
  // ... complete multipart
}
```

---

## 驗證方式

```bash
# 1. 啟動服務
docker-compose up -d

# 2. 檢查 Celery Worker
docker-compose logs celery-worker

# 3. 執行測試
pytest tests/test_upload_jobs.py -v

# 4. 手動測試
curl -X POST /api/v1/upload-jobs \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"deployment_id": 1, "files": [{"name": "test.wav"}]}'
```

---

## 實作順序

| Phase | 內容 | 狀態 |
|-------|------|------|
| **0.5** | 路徑生成工具 (audio_path.py) | 完成 |
| **1** | Docker + Redis + Celery 設定 | 完成 |
| **2** | Model (UploadJob, UploadTask) + Migration | 完成 |
| **2.5** | MinIO Service (Multipart 方法) | 完成 |
| **3** | Schema (Job + Multipart + 檔名驗證) | 完成 |
| **4** | UploadJob Service (含 Multipart) | 完成 |
| **5** | API Endpoints (Job + Multipart) | 完成 |
| **6** | Celery Tasks | 完成 |
| **7** | 測試 | 完成 |
| **8** | Audio 下載端點 | 完成 |

**Note**: Phase 0 (Project 建立時建立 Bucket) 尚未實作，將於後續整合時加入。

---

## 分段上傳流程圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1.29GB 檔案上傳流程 (13 個 100MB parts)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  前端                        後端                        MinIO              │
│    │                          │                           │                │
│    │ POST /multipart/init     │                           │                │
│    │─────────────────────────>│ create_multipart_upload   │                │
│    │                          │──────────────────────────>│                │
│    │<─────────────────────────│ { upload_id, total: 13 }  │                │
│    │                          │                           │                │
│    │ POST /multipart/urls     │                           │                │
│    │ { part_numbers: [1,2,3] }│                           │                │
│    │─────────────────────────>│ generate_presigned_url x3 │                │
│    │<─────────────────────────│ { parts: [...urls] }      │                │
│    │                          │                           │                │
│    │ PUT url (Part 1, 100MB)  │                           │                │
│    │─────────────────────────────────────────────────────>│                │
│    │<─────────────────────────────────────────────────────│ ETag: "abc"    │
│    │                          │                           │                │
│    │ POST /part-complete      │                           │                │
│    │ { part: 1, etag: "abc" } │                           │                │
│    │─────────────────────────>│ (記錄到 part_etags)       │                │
│    │                          │                           │                │
│    │  ... (重複 Part 2-13)    │                           │                │
│    │                          │                           │                │
│    │ POST /multipart/complete │                           │                │
│    │ { parts: [...] }         │                           │                │
│    │─────────────────────────>│ complete_multipart_upload │                │
│    │                          │──────────────────────────>│                │
│    │                          │                           │ 合併檔案       │
│    │<─────────────────────────│ { status: ok }            │                │
│    │                          │                           │                │
│    │                          │ (更新 AudioInfo 狀態)     │                │
│    │                          │──> upload_status=completed│                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 斷點續傳流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  網路中斷後恢復上傳 (使用者全選檔案)                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  情境: 800 個檔案，上傳到第 300 個時中斷                                    │
│  - 檔案 1-299: 已完成 (DB_CREATED)                                         │
│  - 檔案 300: Part 1-7 已完成, Part 8-13 未完成                             │
│  - 檔案 301-800: 尚未開始 (PENDING)                                        │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  Step 1: 使用者重新選擇全部 800 個檔案                                      │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  前端: files = [file_001, file_002, ... file_800]                          │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  Step 2: 查詢 Job 狀態，取得所有 tasks                                      │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  GET /upload-jobs/{job_id}                                                 │
│  Response:                                                                  │
│  {                                                                          │
│    tasks: [                                                                 │
│      { task_id: "t1", file_name: "7505.240611130000.wav", status: "db_created" },  │
│      { task_id: "t2", file_name: "7505.240611130100.wav", status: "db_created" },  │
│      ...                                                                    │
│      { task_id: "t300", file_name: "...", status: "uploading" },  <- 中斷點│
│      { task_id: "t301", file_name: "...", status: "pending" },             │
│      ...                                                                    │
│    ]                                                                        │
│  }                                                                          │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  Step 3: 前端比對檔案，分類處理                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  for each task:                                                             │
│    if task.status == "db_created":                                         │
│      -> 跳過 (已完成)                                                       │
│    elif task.status == "uploading":                                        │
│      -> 查詢 remaining_parts，只傳剩餘部分                                  │
│    elif task.status == "pending" or "multipart_init":                      │
│      -> 從頭上傳                                                            │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  Step 4: 對中斷的檔案 (t300) 續傳                                           │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  GET /tasks/t300/progress                                                  │
│  -> { completed_parts: [1,2,3,4,5,6,7], remaining_parts: [8,9,10,11,12,13] }│
│                                                                             │
│  只上傳 Part 8-13 (節省 700MB)                                             │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  Step 5: 繼續上傳 t301-t800                                                │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 8: Audio 下載端點

### 需求
使用者透過 Project → Point → Deployment 導航後，要能透過 AudioInfo 的 `object_key` 下載 .wav 檔案。

### object_key 的用途
- **格式**: `{Point_Name}/{YYYY}/{MM}/Raw_Data/{Filename}`
- **範例**: `TPC01/2024/06/Raw_Data/7505.240611130000.wav`
- **用途**: MinIO 中檔案的唯一路徑，用於產生下載 URL

### 現有查詢流程
```
GET /audio/?deployment_id=xxx
→ 返回 AudioInfo 列表 (包含 object_key)
→ 前端需要透過 object_key 取得下載 URL
```

### 新增端點

#### `GET /audio/{audio_id}/download-url`

```python
# app/api/v1/endpoints/api_audio.py

@router.get("/{audio_id}/download-url", response_model=AudioDownloadUrlResponse)
def get_audio_download_url(
    audio_id: int,
    expires_in: int = 3600,  # 預設 1 小時
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得音檔的下載 URL (presigned URL)

    - 查詢 AudioInfo 取得 object_key
    - 驗證 upload_status == "completed"
    - 產生 MinIO presigned URL (method="get_object")
    """
    return AudioService(db).get_download_url(audio_id, expires_in)
```

### Schema

```python
# app/schemas/audio.py

class AudioDownloadUrlResponse(BaseModel):
    presigned_url: str
    expires_in: int  # 有效期 (秒)
    file_name: str
    file_size: int | None
```

### Service 方法

```python
# app/services/audio_service.py

def get_download_url(self, audio_id: int, expires_in: int = 3600) -> dict:
    """取得音檔下載 URL"""
    # 1. 查詢 AudioInfo (含關聯到 Project)
    audio = (
        self.db.query(AudioInfo)
        .options(
            joinedload(AudioInfo.deployment)
            .joinedload(DeploymentInfo.point)
            .joinedload(PointInfo.project)
        )
        .filter(AudioInfo.id == audio_id, AudioInfo.is_deleted.is_(False))
        .first()
    )

    if not audio:
        raise HTTPException(404, "Audio not found")

    # 2. 驗證上傳狀態
    if audio.upload_status != UploadStatus.COMPLETED:
        raise HTTPException(400, f"Audio upload not completed: {audio.upload_status}")

    # 3. 產生 presigned URL
    bucket = audio.deployment.point.project.name
    minio = MinioService()

    presigned_url = minio.generate_presigned_url(
        bucket=bucket,
        key=audio.object_key,
        expires_in=expires_in,
        method="get_object",
    )

    return {
        "presigned_url": presigned_url,
        "expires_in": expires_in,
        "file_name": audio.file_name,
        "file_size": audio.file_size,
    }
```

### 修改檔案

| 檔案 | 修改內容 |
|------|----------|
| `app/schemas/audio.py` | 新增 `AudioDownloadUrlResponse` |
| `app/services/audio_service.py` | 新增 `get_download_url()` |
| `app/api/v1/endpoints/api_audio.py` | 新增 `GET /{audio_id}/download-url` |
| `tests/integration/test_audio_upload_integration.py` | 新增下載驗證測試 |

### 整合測試

已實作 4 個測試函數於 `tests/integration/test_audio_upload_integration.py`:

| 測試函數 | 說明 |
|----------|------|
| `test_download_url_after_upload` | 上傳完成後取得下載 URL 並驗證可下載 |
| `test_download_url_with_custom_expires` | 自訂 expires_in 參數 |
| `test_download_url_not_found` | 不存在的 Audio 回傳 404 |
| `test_download_url_upload_not_completed` | upload_status 非 completed 回傳 400 |

```python
def test_download_url_after_upload(self, api_client, auth_headers, test_deployment, ...):
    """測試上傳完成後取得下載 URL 並驗證可下載"""
    # 1-6. 執行標準上傳流程

    # 7. 取得 AudioInfo ID
    audio = db_session.query(AudioInfo).filter(
        AudioInfo.object_key == object_key
    ).first()

    # 8. 取得下載 URL
    response = api_client.get(
        f"{api_prefix}/audio/{audio.id}/download-url",
        headers=auth_headers,
    )
    assert response.status_code == 200
    download_data = response.json()
    assert download_data["expires_in"] == 3600
    assert download_data["file_name"] == file_name

    # 9. 驗證可下載
    download_response = httpx.get(download_data["presigned_url"])
    assert download_response.status_code == 200
    assert download_response.content == test_file_content
```

### 驗證方式

```bash
# 整合測試
docker exec os-acoustic-backend python -m pytest tests/integration/test_audio_upload_integration.py -v -k download

# 測試結果: 4 passed
```
