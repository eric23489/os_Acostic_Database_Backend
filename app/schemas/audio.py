from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator

from app.schemas.deployment import DeploymentWithDetailsResponse


class AudioBase(BaseModel):
    deployment_id: int
    file_name: str
    object_key: str
    file_format: str | None = "wav"
    file_size: int | None = None
    checksum: str | None = None
    record_time: datetime | None = None
    record_duration: float | None = None
    fs: int | None = None
    recorder_channel: int | None = 0
    audio_channels: int | None = 1
    target: str | None = None
    target_type: int | None = None
    meta_json: dict[str, Any] | None = None
    is_cold_storage: bool | None = False

    @field_validator("record_time")
    @classmethod
    def set_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v


class AudioCreate(AudioBase):
    pass


class AudioUpdate(BaseModel):
    deployment_id: int | None = None
    file_name: str | None = None
    object_key: str | None = None
    file_format: str | None = None
    file_size: int | None = None
    checksum: str | None = None
    record_time: datetime | None = None
    record_duration: float | None = None
    fs: int | None = None
    recorder_channel: int | None = None
    audio_channels: int | None = None
    target: str | None = None
    target_type: int | None = None
    meta_json: dict[str, Any] | None = None
    is_cold_storage: bool | None = None


class AudioResponse(AudioBase):
    id: int
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("record_time", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class AudioWithDetailsResponse(AudioResponse):
    deployment: DeploymentWithDetailsResponse


class PresignedUrlRequest(BaseModel):
    project_id: int
    project_name: str
    point_id: int
    point_name: str
    filename: str


class PresignedUrlResponse(BaseModel):
    presigned_url: str
    bucket: str
    key: str


class PresignedUrlBatchRequest(BaseModel):
    project_id: int
    project_name: str
    point_id: int
    point_name: str
    filenames: list[str]


class PresignedUrlBatchResponse(PresignedUrlResponse):
    filename: str


class AudioDownloadUrlResponse(BaseModel):
    """Audio 下載 URL 回應。"""

    presigned_url: str
    expires_in: int
    file_name: str
    file_size: int | None


# =============================================================================
# Batch Create Schemas
# =============================================================================


class AudioBatchItem(BaseModel):
    """單一 Audio 批量建立項目，deployment_id 由外層提供。"""

    file_name: str
    object_key: str
    file_format: str | None = "wav"
    file_size: int | None = None
    checksum: str | None = None
    record_time: datetime | None = None
    record_duration: float | None = None
    fs: int | None = None
    recorder_channel: int | None = 0
    audio_channels: int | None = 1
    target: str | None = None
    target_type: int | None = None
    meta_json: dict[str, Any] | None = None
    is_cold_storage: bool | None = False


class AudioBatchCreateRequest(BaseModel):
    """批量建立 Audio 請求。"""

    deployment_id: int
    audios: list[AudioBatchItem]

    @field_validator("audios")
    @classmethod
    def validate_batch_size(cls, v: list[AudioBatchItem]) -> list[AudioBatchItem]:
        """驗證批次大小介於 1 到 100 筆。"""
        if len(v) == 0:
            raise ValueError("At least 1 audio required")
        if len(v) > 100:
            raise ValueError("Maximum 100 audios per batch")
        return v


class AudioBatchResultItem(BaseModel):
    """批量建立單一結果。"""

    file_name: str
    object_key: str
    status: Literal["created", "skipped", "failed"]
    audio_id: int | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> "AudioBatchResultItem":
        """驗證 status 與 audio_id/reason 的跨欄位不變量。"""
        if self.status == "created" and self.audio_id is None:
            raise ValueError("audio_id is required when status is 'created'")
        if self.status in ("skipped", "failed") and self.reason is None:
            raise ValueError("reason is required when status is 'skipped' or 'failed'")
        return self


class AudioBatchCreateResponse(BaseModel):
    """批量建立 Audio 回應。"""

    deployment_id: int
    total_count: int
    success_count: int
    skipped_count: int
    failed_count: int
    results: list[AudioBatchResultItem]


class MessageResponse(BaseModel):
    message: str
