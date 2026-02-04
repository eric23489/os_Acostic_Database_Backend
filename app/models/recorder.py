from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    SmallInteger,
    Boolean,
    Index,
    text,
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
    is_deleted = Column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, nullable=True)

    __table_args__ = (
        Index(
            "uq_recorder_brand_model_sn_active",
            "brand",
            "model",
            "sn",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
    )
