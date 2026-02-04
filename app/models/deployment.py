from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Computed
from geoalchemy2 import Geometry
from app.db.base import Base


class DeploymentInfo(Base):
    __tablename__ = "deployment_info"

    id = Column(Integer, primary_key=True, index=True)
    point_id = Column(Integer, ForeignKey("point_info.id"), nullable=False, index=True)
    point = relationship("PointInfo", back_populates="deployments")
    recorder_id = Column(
        Integer, ForeignKey("recorder_info.id"), nullable=False, index=True
    )
    recorder = relationship("RecorderInfo")
    phase = Column(Integer, default=1)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    deploy_time = Column(DateTime(timezone=True))
    return_time = Column(DateTime(timezone=True))
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
    status = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_deleted = Column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, nullable=True)

    __table_args__ = (
        Index(
            "uq_deployment_point_start_time_active",
            "point_id",
            "start_time",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
        Index(
            "uq_deployment_point_phase_active",
            "point_id",
            "phase",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
    )
