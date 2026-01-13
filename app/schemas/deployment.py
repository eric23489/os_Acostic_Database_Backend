from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.enums.enums import DeploymentStatus


class DeploymentBase(BaseModel):
    point_id: int
    recorder_id: int
    phase: Optional[int] = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deploy_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    gps_lat_exe: Optional[float] = None
    gps_lon_exe: Optional[float] = None
    depth_exe: Optional[float] = None
    fs: Optional[int] = None
    sensitivity: Optional[float] = None
    gain: Optional[float] = None
    status: Optional[str] = DeploymentStatus.UNDEPLOYED.value
    description: Optional[str] = None


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
    gps_lat_exe: Optional[float] = None
    gps_lon_exe: Optional[float] = None
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

    class Config:
        from_attributes = True
