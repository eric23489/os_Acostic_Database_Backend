from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, 
)
from sqlalchemy.sql import func

from app.db.base import Base

class ProjectInfo(Base):
    __tablename__ = "project_info"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    area = Column(String(100))
    description = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    is_finished = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    
