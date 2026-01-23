from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from app.schemas.project import ProjectResponse


class PointBase(BaseModel):
    project_id: int
    name: str
    gps_lat_plan: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon_plan: Optional[float] = Field(None, ge=-180, le=180)
    depth_plan: Optional[float] = None
    description: Optional[str] = None


class PointCreate(PointBase):
    pass


class PointUpdate(BaseModel):
    project_id: Optional[int] = None
    name: Optional[str] = None
    gps_lat_plan: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon_plan: Optional[float] = Field(None, ge=-180, le=180)
    depth_plan: Optional[float] = None
    description: Optional[str] = None


class PointResponse(PointBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class PointWithProjectResponse(PointResponse):
    project: ProjectResponse
