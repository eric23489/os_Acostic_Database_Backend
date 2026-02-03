from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Computed
from geoalchemy2 import Geometry
from app.db.base import Base


class PointInfo(Base):
    __tablename__ = "point_info"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("project_info.id"), nullable=False)
    project = relationship("ProjectInfo")
    name = Column(String(50), nullable=False)
    gps_lat_plan = Column(Float)
    gps_lon_plan = Column(Float)
    geom_plan = Column(
        Geometry("POINT", srid=4326),
        Computed(
            "ST_SetSRID(ST_MakePoint(gps_lon_plan, gps_lat_plan), 4326)", persisted=True
        ),
    )
    depth_plan = Column(Float)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_point_project_name"),
    )
