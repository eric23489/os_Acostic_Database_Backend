from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict
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


class AudioWithDetailsResponse(AudioResponse):
    deployment: DeploymentWithDetailsResponse
