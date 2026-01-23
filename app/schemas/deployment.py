from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer

from app.enums.enums import DeploymentStatus
from app.schemas.point import PointWithProjectResponse
from app.schemas.recorder import RecorderResponse


class DeploymentBase(BaseModel):
    point_id: int
    recorder_id: int
    phase: Optional[int] = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deploy_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    gps_lat_exe: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon_exe: Optional[float] = Field(None, ge=-180, le=180)
    depth_exe: Optional[float] = None
    fs: Optional[int] = None
    sensitivity: Optional[float] = None
    gain: Optional[float] = None
    status: Optional[str] = DeploymentStatus.UNDEPLOYED.value
    description: Optional[str] = None

    @field_validator("start_time", "end_time", "deploy_time", "return_time")
    @classmethod
    def set_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            # 如果時間沒有時區資訊，預設加上台灣時區 (UTC+8)
            tw_tz = timezone(timedelta(hours=8))
            return v.replace(tzinfo=tw_tz)
        return v


class DeploymentCreate(DeploymentBase):
    pass


class DeploymentUpdate(BaseModel):
    point_id: Optional[int] = None
    recorder_id: Optional[int] = None
    phase: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deploy_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    gps_lat_exe: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon_exe: Optional[float] = Field(None, ge=-180, le=180)
    depth_exe: Optional[float] = None
    fs: Optional[int] = None
    sensitivity: Optional[float] = None
    gain: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None


class DeploymentResponse(DeploymentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "start_time",
        "end_time",
        "deploy_time",
        "return_time",
        "created_at",
        "updated_at",
    )
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class DeploymentWithDetailsResponse(DeploymentResponse):
    point: PointWithProjectResponse
    recorder: RecorderResponse
