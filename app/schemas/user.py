from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer, model_validator

from app.enums.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: UserRole | None = UserRole.USER
    is_active: bool | None = True
    is_verified: bool | None = False


class UserCreate(UserBase):
    password: str  # Plain text password for creation


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    password: str | None = None


class UserResponse(UserBase):
    id: int
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    oauth_provider: str | None = None
    has_password: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def compute_has_password(cls, data: Any) -> Any:
        """Auto-compute has_password from password_hash."""
        if hasattr(data, "password_hash"):
            # ORM model
            if isinstance(data, dict):
                data["has_password"] = data.get("password_hash") is not None
            else:
                # Convert to dict for modification
                return {
                    "id": data.id,
                    "email": data.email,
                    "full_name": data.full_name,
                    "role": data.role,
                    "is_active": data.is_active,
                    "is_verified": data.is_verified,
                    "last_login_at": data.last_login_at,
                    "created_at": data.created_at,
                    "updated_at": data.updated_at,
                    "oauth_provider": data.oauth_provider,
                    "has_password": data.password_hash is not None,
                }
        return data

    @field_serializer("last_login_at", "created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))

    @field_serializer("role")
    def serialize_role(self, role: UserRole | None, _info):
        if role is None:
            return None
        return role.value


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 預留給 JWT token payload 使用
class TokenData(BaseModel):
    sub: str | None = None  # subject, e.g., email
