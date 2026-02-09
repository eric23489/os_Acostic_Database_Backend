from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.sql import func

from app.db.base import Base
from app.enums.enums import UserRole


class UserInfo(Base):
    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)  # nullable for OAuth-only users
    full_name = Column(String(100))
    role = Column(String(100), default=UserRole.USER.value)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_deleted = Column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, nullable=True)

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # e.g., "google"
    oauth_sub = Column(String(255), nullable=True)  # OAuth provider's unique user ID

    # Password reset fields
    reset_token = Column(String(255), nullable=True)
    reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_user_email_active",
            "email",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
        Index(
            "uq_oauth_sub_active",
            "oauth_provider",
            "oauth_sub",
            unique=True,
            postgresql_where=(is_deleted.is_(False)),
        ),
    )
