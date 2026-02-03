from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, field_serializer
from app.enums.enums import RecorderStatus


class RecorderBase(BaseModel):
    brand: str
    model: str
    sn: str
    sensitivity: float
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

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))
