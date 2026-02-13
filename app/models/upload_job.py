"""
上传任务模型。

用于追踪批量音档上传的状态。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.enums.enums import JobStatus, TaskStatus


class UploadJob(Base):
    """上传任务。"""

    __tablename__ = "upload_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    deployment_id = Column(
        Integer, ForeignKey("deployment_info.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("user_info.id"), nullable=False, index=True)
    status = Column(String(20), default=JobStatus.PENDING, index=True)
    priority = Column(Integer, default=5)  # 0=高, 9=低

    total_files = Column(Integer, default=0)
    uploaded_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    deployment = relationship("DeploymentInfo")
    user = relationship("UserInfo")
    tasks = relationship(
        "UploadTask", back_populates="job", cascade="all, delete-orphan"
    )


class UploadTask(Base):
    """上传子任务 (单一档案)。"""

    __tablename__ = "upload_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id = Column(
        String(36), ForeignKey("upload_jobs.id"), nullable=False, index=True
    )

    file_name = Column(String(255), nullable=False)
    object_key = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=True)
    checksum = Column(String(64), nullable=True)

    status = Column(String(20), default=TaskStatus.PENDING, index=True)
    presigned_url = Column(Text, nullable=True)
    url_expires_at = Column(DateTime(timezone=True), nullable=True)

    audio_id = Column(
        Integer, ForeignKey("audio_info.id"), nullable=False, index=True
    )
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Multipart Upload 追踪
    upload_id = Column(String(255), nullable=True)  # MinIO multipart upload_id
    total_parts = Column(Integer, nullable=True)  # 总段数 (1.29GB / 100MB = 13)
    completed_parts = Column(Integer, default=0)  # 已完成段数
    part_size = Column(Integer, default=104857600)  # 每段大小 (预设 100MB)
    part_etags = Column(JSON, nullable=True)  # {"1": "etag1", "2": "etag2", ...}

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("UploadJob", back_populates="tasks")
    audio = relationship("AudioInfo")
