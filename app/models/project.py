from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy import Index
from app.db.base import Base


class ProjectInfo(Base):
    __tablename__ = "project_info"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    name_zh = Column(String(100), nullable=True)
    area = Column(String(100))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    is_finished = Column(Boolean, default=False)
    owner = Column(Text)
    contractor = Column(Text)
    contact_name = Column(Text)
    contact_phone = Column(Text)
    contact_email = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_project_name_active",
            "name",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
        Index(
            "ix_project_name_zh_active",
            "name_zh",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
    )
