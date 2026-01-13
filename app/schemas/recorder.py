from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.enums.enums import RecorderStatus


class RecorderBase(BaseModel):
    brand: str
    model: str
    sn: str
    sensitivity: Optional[float] = None
    high_gain: Optional[float] = None
    low_gain: Optional[float] = None
    status: Optional[str] = RecorderStatus.IN_SERVICE.value
    owner: Optional[str] = "Ocean Sound"
    recorder_channels: Optional[int] = 1
    description: Optional[str] = None


class RecorderCreate(RecorderBase):
    pass


class RecorderUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    sn: Optional[str] = None
    sensitivity: Optional[float] = None
    high_gain: Optional[float] = None
    low_gain: Optional[float] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    recorder_channels: Optional[int] = None
    description: Optional[str] = None


class RecorderResponse(RecorderBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
