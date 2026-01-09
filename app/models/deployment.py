from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Computed,
)
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from app.db.base import Base


class PointInfo(Base):
    __tablename__ = "point_info"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("project_info.id"), nullable=False)
    name = Column(String(50), nullable=False)

    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))

    # GIS Generated Columns
    gps_lat_plan = Column(Float)
    gps_lon_plan = Column(Float)
    geom_plan = Column(
        Geometry("POINT", srid=4326),
        Computed(
            "ST_SetSRID(ST_MakePoint(gps_lon_plan, gps_lat_plan), 4326)", persisted=True
        ),
    )
    depth_plan = Column(Float)

    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("project_id", "name", name="uix_project_point"),)


class DeploymentInfo(Base):
    __tablename__ = "deployment_info"
    id = Column(Integer, primary_key=True)
    point_id = Column(Integer, ForeignKey("point_info.id"), nullable=False)
    recorder_id = Column(Integer, ForeignKey("recorder_info.id"), nullable=False)

    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    deploy_time = Column(DateTime(timezone=True))
    return_time = Column(DateTime(timezone=True))

    # GIS Generated Columns
    gps_lat_exe = Column(Float)
    gps_lon_exe = Column(Float)
    geom_exe = Column(
        Geometry("POINT", srid=4326),
        Computed(
            "ST_SetSRID(ST_MakePoint(gps_lon_exe, gps_lat_exe), 4326)", persisted=True
        ),
    )
    depth_exe = Column(Float)

    fs = Column(Integer)
    sensitivity = Column(Float)
    gain = Column(Float)
    status = Column(String(50), default="un-deployed")
    description = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("point_id", "start_time", name="uix_point_start_time"),
    )
