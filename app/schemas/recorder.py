from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, field_serializer

from app.enums.enums import RecorderStatus


class RecorderBase(BaseModel):
    brand: str
    model: str
    sn: str
    sensitivity: float
    high_gain: float | None = None
    low_gain: float | None = None
    status: RecorderStatus | None = RecorderStatus.IN_SERVICE
    owner: str | None = "Ocean Sound"
    recorder_channels: int | None = 1
    description: str | None = None


class RecorderCreate(RecorderBase):
    pass


class RecorderUpdate(BaseModel):
    brand: str | None = None
    model: str | None = None
    sn: str | None = None
    sensitivity: float | None = None
    high_gain: float | None = None
    low_gain: float | None = None
    status: RecorderStatus | None = None
    owner: str | None = None
    recorder_channels: int | None = None
    description: str | None = None


class RecorderResponse(RecorderBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))
