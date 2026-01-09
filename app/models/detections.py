from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    BigInteger,
    SmallInteger,
)
from sqlalchemy.sql import func

from app.db.base import Base
from app.enums.enums import CetaceanSpecies, CetaceanCallType, DetectionMethod


class CetaceanInfo(Base):
    __tablename__ = "cetacean_info"
    id = Column(BigInteger, primary_key=True)
    audio_id = Column(Integer, ForeignKey("audio_info.id"), nullable=False)
    audio_channel = Column(Integer, default=0)
    start_second = Column(Float)
    end_second = Column(Float)
    event_duration = Column(Float)

    cetacean_species = Column(
        SmallInteger, index=True, default=CetaceanSpecies.UNKNOWN.value
    )
    cetacean_call_type = Column(
        SmallInteger, index=True, default=CetaceanCallType.UNKNOWN.value
    )
    detection_method = Column(String(100), default=DetectionMethod.MANUAL.value)
    model_name = Column(String(100))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
