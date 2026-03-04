from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.enums.enums import DeploymentStatus
from app.schemas.point import PointWithProjectResponse
from app.schemas.recorder import RecorderResponse


class DeploymentBase(BaseModel):
    point_id: int
    recorder_id: int
    phase: int | None = Field(default=1, ge=1)
    report_start_time: datetime | None = None
    report_end_time: datetime | None = None
    deploy_time: datetime | None = None
    return_time: datetime | None = None
    gps_lat_exe: float | None = Field(None, ge=-90, le=90)
    gps_lon_exe: float | None = Field(None, ge=-180, le=180)
    depth_exe: float | None = Field(None, ge=0, le=11000)
    fs: int | None = Field(None, ge=0, le=384000)
    sensitivity: float | None = Field(None, ge=-300, le=0)
    gain: float | None = Field(None, ge=-60, le=60)
    status: DeploymentStatus | None = DeploymentStatus.UNDEPLOYED
    description: str | None = Field(None, max_length=2000)
    deploy_personnel: str | None = Field(None, max_length=200)
    retrieve_personnel: str | None = Field(None, max_length=200)

    @field_validator(
        "report_start_time", "report_end_time", "deploy_time", "return_time"
    )
    @classmethod
    def set_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "DeploymentBase":
        if self.deploy_time and self.return_time and self.deploy_time > self.return_time:
            raise ValueError("deploy_time must be before or equal to return_time")
        return self


class DeploymentCreate(DeploymentBase):
    pass


class DeploymentUpdate(BaseModel):
    point_id: int | None = None
    recorder_id: int | None = None
    phase: int | None = Field(None, ge=1)
    report_start_time: datetime | None = None
    report_end_time: datetime | None = None
    deploy_time: datetime | None = None
    return_time: datetime | None = None
    gps_lat_exe: float | None = Field(None, ge=-90, le=90)
    gps_lon_exe: float | None = Field(None, ge=-180, le=180)
    depth_exe: float | None = Field(None, ge=0, le=11000)
    fs: int | None = Field(None, ge=0, le=384000)
    sensitivity: float | None = Field(None, ge=-300, le=0)
    gain: float | None = Field(None, ge=-60, le=60)
    status: DeploymentStatus | None = None
    description: str | None = Field(None, max_length=2000)
    deploy_personnel: str | None = Field(None, max_length=200)
    retrieve_personnel: str | None = Field(None, max_length=200)


class DeploymentResponse(DeploymentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "report_start_time",
        "report_end_time",
        "deploy_time",
        "return_time",
        "created_at",
        "updated_at",
    )
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))

    @field_serializer("status")
    def serialize_status(self, status: DeploymentStatus | None, _info):
        if status is None:
            return None
        return status.value


class DeploymentWithDetailsResponse(DeploymentResponse):
    point: PointWithProjectResponse
    recorder: RecorderResponse
