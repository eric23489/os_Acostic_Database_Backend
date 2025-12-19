from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.enums.enums import CetaceanCallType, DetectionMethod

class CetaceanBase(BaseModel):
    audio_id: int
    audio_channel: Optional[int] = 0
    start_second: Optional[float] = None
    end_second: Optional[float] = None
    event_duration: Optional[float] = None
    cetacean_call_type: Optional[int] = CetaceanCallType.UNKNOWN.value
    detection_method: Optional[str] = DetectionMethod.MANUAL.value
    model_name: Optional[str] = None

class CetaceanCreate(CetaceanBase):
    pass

class CetaceanUpdate(BaseModel):
    audio_id: Optional[int] = None
    audio_channel: Optional[int] = None
    start_second: Optional[float] = None
    end_second: Optional[float] = None
    event_duration: Optional[float] = None
    cetacean_call_type: Optional[int] = None
    detection_method: Optional[str] = None
    model_name: Optional[str] = None

class CetaceanResponse(CetaceanBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
