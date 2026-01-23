from typing import Optional, Any, Dict, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, field_validator, field_serializer
from app.schemas.deployment import DeploymentWithDetailsResponse


class AudioBase(BaseModel):
    deployment_id: int
    file_name: str
    object_key: str
    file_format: Optional[str] = "wav"
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    record_time: Optional[datetime] = None
    record_duration: Optional[float] = None
    fs: Optional[int] = None
    recorder_channel: Optional[int] = 0
    audio_channels: Optional[int] = 1
    target: Optional[str] = None
    target_type: Optional[int] = None
    meta_json: Optional[Dict[str, Any]] = None
    is_cold_storage: Optional[bool] = False

    @field_validator("record_time")
    @classmethod
    def set_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v


class AudioCreate(AudioBase):
    pass


class AudioUpdate(BaseModel):
    deployment_id: Optional[int] = None
    file_name: Optional[str] = None
    object_key: Optional[str] = None
    file_format: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    record_time: Optional[datetime] = None
    record_duration: Optional[float] = None
    fs: Optional[int] = None
    recorder_channel: Optional[int] = None
    audio_channels: Optional[int] = None
    target: Optional[str] = None
    target_type: Optional[int] = None
    meta_json: Optional[Dict[str, Any]] = None
    is_cold_storage: Optional[bool] = None


class AudioResponse(AudioBase):
    id: int
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("record_time", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class AudioWithDetailsResponse(AudioResponse):
    deployment: DeploymentWithDetailsResponse


class PresignedUrlRequest(BaseModel):
    project_id: str
    project_name: str
    point_id: str
    point_name: str
    filename: str


class PresignedUrlResponse(BaseModel):
    presigned_url: str
    bucket: str
    key: str


class PresignedUrlBatchRequest(BaseModel):
    project_id: str
    project_name: str
    point_id: str
    point_name: str
    filenames: List[str]


class PresignedUrlBatchResponse(PresignedUrlResponse):
    filename: str
