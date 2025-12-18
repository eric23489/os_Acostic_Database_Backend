from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    ForeignKey, UniqueConstraint, Computed
)
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from app.db.base import Base

class DeploymentInfo(Base):
    __tablename__ = "deployment_info" 
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("project_info.id"), nullable=False)
    recorder_id = Column(Integer, ForeignKey("recorder_info.id"), nullable=False)
    name = Column(String(50), nullable=False)
    phase = Column(Integer, default=1)
    
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    deploy_time = Column(DateTime(timezone=True))
    return_time = Column(DateTime(timezone=True))
    
    # GIS Generated Columns
    gps_lat_plan = Column(Float)
    gps_lon_plan = Column(Float)
    geom_plan = Column(Geometry('POINT', srid=4326), 
                       Computed('ST_SetSRID(ST_MakePoint(gps_lon_plan, gps_lat_plan), 4326)', persisted=True))

    gps_lat_exe = Column(Float)
    gps_lon_exe = Column(Float)
    geom_exe = Column(Geometry('POINT', srid=4326), 
                      Computed('ST_SetSRID(ST_MakePoint(gps_lon_exe, gps_lat_exe), 4326)', persisted=True))

    depth = Column(Float)
    fs = Column(Integer)
    status = Column(String(50), default="un-deployed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('project_id', 'name', 'phase', name='uix_project_point_phase'),
    )