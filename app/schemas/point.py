from typing import Any, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer
from app.schemas.project import ProjectResponse


class PointBase(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=50)
    gps_lat_plan: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon_plan: Optional[float] = Field(None, ge=-180, le=180)
    depth_plan: Optional[float] = Field(None, ge=0, le=11000)
    description: Optional[str] = Field(None, max_length=1000)


class PointCreate(PointBase):
    pass


class PointUpdate(BaseModel):
    project_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gps_lat_plan: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon_plan: Optional[float] = Field(None, ge=-180, le=180)
    depth_plan: Optional[float] = Field(None, ge=0, le=11000)
    description: Optional[str] = Field(None, max_length=1000)


class PointResponse(PointBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deployments: List[Any] = Field(default_factory=list, exclude=True)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def deployment_count(self) -> int:
        return len(self.deployments)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class PointWithProjectResponse(PointResponse):
    project: ProjectResponse
