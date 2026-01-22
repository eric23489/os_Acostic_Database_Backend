from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
    BigInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AudioInfo(Base):
    __tablename__ = "audio_info"
    id = Column(Integer, primary_key=True)
    deployment_id = Column(Integer, ForeignKey("deployment_info.id"), nullable=False)
    deployment = relationship("DeploymentInfo")
    file_name = Column(String(255), nullable=False)
    object_key = Column(String(512), unique=True, nullable=False)
    file_format = Column(String(10))
    file_size = Column(BigInteger)
    checksum = Column(String(64))
    record_time = Column(DateTime(timezone=True), index=True)
    record_duration = Column(Float)
    fs = Column(Integer)
    recorder_channel = Column(Integer)
    audio_channels = Column(Integer)
    target = Column(String(100))
    target_type = Column(Integer)
    meta_json = Column(JSON)
    is_cold_storage = Column(Boolean, default=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
