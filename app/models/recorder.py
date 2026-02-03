from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.db.base import Base
from app.enums.enums import RecorderStatus


class RecorderInfo(Base):
    __tablename__ = "recorder_info"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    sn = Column(String(50), nullable=False)
    sensitivity = Column(Float, nullable=False)
    high_gain = Column(Float)
    low_gain = Column(Float)
    status = Column(String(50), default=RecorderStatus.IN_SERVICE.value)
    owner = Column(String(100), default="Ocean Sound")
    recorder_channels = Column(SmallInteger, default=1)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("brand", "model", "sn", name="uq_recorder_brand_model_sn"),
    )
