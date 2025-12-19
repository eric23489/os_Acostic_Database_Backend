from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.enums.enums import DeploymentStatus

class DeploymentBase(BaseModel):
    project_id: int
    recorder_id: int
    name: str
    phase: Optional[int] = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deploy_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    gps_lat_plan: Optional[float] = None
    gps_lon_plan: Optional[float] = None
    gps_lat_exe: Optional[float] = None
    gps_lon_exe: Optional[float] = None
    depth: Optional[float] = None
    fs: Optional[int] = None
    status: Optional[str] = DeploymentStatus.UNDEPLOYED.value

class DeploymentCreate(DeploymentBase):
    pass

class DeploymentUpdate(BaseModel):
    project_id: Optional[int] = None
    recorder_id: Optional[int] = None
    name: Optional[str] = None
    phase: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deploy_time: Optional[datetime] = None
    return_time: Optional[datetime] = None
    gps_lat_plan: Optional[float] = None
    gps_lon_plan: Optional[float] = None
    gps_lat_exe: Optional[float] = None
    gps_lon_exe: Optional[float] = None
    depth: Optional[float] = None
    fs: Optional[int] = None
    status: Optional[str] = None

class DeploymentResponse(DeploymentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
