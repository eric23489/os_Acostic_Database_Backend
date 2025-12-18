from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, 
    ForeignKey, BigInteger, JSON
)
from sqlalchemy.sql import func

from app.db.base import Base


class AudioInfo(Base):
    __tablename__ = "audio_info"
    id = Column(Integer, primary_key=True)
    deployment_id = Column(Integer, ForeignKey("deployment_info.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    object_key = Column(String(512), unique=True, nullable=False)
    file_format = Column(String(10), default='wav')
    file_size = Column(BigInteger)
    checksum = Column(String(64))
    record_time = Column(DateTime(timezone=True), index=True)
    record_duration = Column(Float)
    fs = Column(Integer)
    recorder_channel = Column(Integer, default=0)
    audio_channels = Column(Integer, default=1)
    target = Column(String(100))
    target_type = Column(Integer)
    meta_json = Column(JSON)
    is_cold_storage = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    
