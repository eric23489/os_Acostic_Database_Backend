from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.enums.enums import DeploymentStatus
from app.schemas.point import PointWithProjectResponse
from app.schemas.recorder import RecorderResponse


class DeploymentBase(BaseModel):
    point_id: int
    recorder_id: int
    phase: int | None = 1
    start_time: datetime | None = None
    end_time: datetime | None = None
    deploy_time: datetime | None = None
    return_time: datetime | None = None
    gps_lat_exe: float | None = Field(None, ge=-90, le=90)
    gps_lon_exe: float | None = Field(None, ge=-180, le=180)
    depth_exe: float | None = None
    fs: int | None = None
    sensitivity: float | None = None
    gain: float | None = None
    status: DeploymentStatus | None = DeploymentStatus.UNDEPLOYED
    description: str | None = None

    @field_validator("start_time", "end_time", "deploy_time", "return_time")
    @classmethod
    def set_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v


class DeploymentCreate(DeploymentBase):
    pass


class DeploymentUpdate(BaseModel):
    point_id: int | None = None
    recorder_id: int | None = None
    phase: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    deploy_time: datetime | None = None
    return_time: datetime | None = None
    gps_lat_exe: float | None = Field(None, ge=-90, le=90)
    gps_lon_exe: float | None = Field(None, ge=-180, le=180)
    depth_exe: float | None = None
    fs: int | None = None
    sensitivity: float | None = None
    gain: float | None = None
    status: DeploymentStatus | None = None
    description: str | None = None


class DeploymentResponse(DeploymentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "start_time",
        "end_time",
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
