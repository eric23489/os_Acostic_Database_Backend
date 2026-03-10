from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.enums.enums import RecorderStatus


class RecorderBase(BaseModel):
    brand: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    sn: str = Field(..., min_length=1, max_length=50)
    sensitivity: float = Field(..., ge=-300, le=0)
    high_gain: float | None = Field(None, ge=-60, le=60)
    low_gain: float | None = Field(None, ge=-60, le=60)
    status: RecorderStatus | None = RecorderStatus.AVAILABLE
    owner: str | None = Field(default="Ocean Sound", max_length=100)
    bits: int | None = Field(default=16, ge=1, le=32)
    recorder_channels: int | None = Field(default=1, ge=1, le=16)
    description: str | None = Field(None, max_length=2000)
    measured_sensitivity: float | None = Field(None, ge=-300, le=0)
    standard_sensitivity: float | None = Field(None, ge=-300, le=0)
    calibration_date: date | None = None


class RecorderCreate(RecorderBase):
    pass


class RecorderUpdate(BaseModel):
    brand: str | None = Field(None, min_length=1, max_length=50)
    model: str | None = Field(None, min_length=1, max_length=50)
    sn: str | None = Field(None, min_length=1, max_length=50)
    sensitivity: float | None = Field(None, ge=-300, le=0)
    high_gain: float | None = Field(None, ge=-60, le=60)
    low_gain: float | None = Field(None, ge=-60, le=60)
    bits: int | None = Field(None, ge=1, le=32)
    status: RecorderStatus | None = None
    owner: str | None = Field(None, max_length=100)
    recorder_channels: int | None = Field(None, ge=1, le=16)
    description: str | None = Field(None, max_length=2000)
    measured_sensitivity: float | None = Field(None, ge=-300, le=0)
    standard_sensitivity: float | None = Field(None, ge=-300, le=0)
    calibration_date: date | None = None


class RecorderResponse(RecorderBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))

    @field_serializer("status")
    def serialize_status(self, status: RecorderStatus | None, _info):
        if status is None:
            return None
        return status.value

    @field_serializer("calibration_date")
    def serialize_date(self, d: date | None, _info):
        if d is None:
            return None
        return d.isoformat()


class RecorderStatsResponse(BaseModel):
    available_count: int
    deploying_count: int
