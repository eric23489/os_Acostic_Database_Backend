from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PointBase(BaseModel):
    project_id: int
    name: str
    gps_lat_plan: Optional[float] = None
    gps_lon_plan: Optional[float] = None
    depth_plan: Optional[float] = None
    description: Optional[str] = None


class PointCreate(PointBase):
    pass


class PointUpdate(BaseModel):
    project_id: Optional[int] = None
    name: Optional[str] = None
    gps_lat_plan: Optional[float] = None
    gps_lon_plan: Optional[float] = None
    depth_plan: Optional[float] = None
    description: Optional[str] = None


class PointResponse(PointBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
