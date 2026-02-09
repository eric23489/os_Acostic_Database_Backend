from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer

from app.enums.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: str | None = UserRole.USER.value
    is_active: bool | None = True
    is_verified: bool | None = False


class UserCreate(UserBase):
    password: str  # Plain text password for creation


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
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

    @classmethod
    def from_orm_with_password_check(cls, user) -> "UserResponse":
        """Create UserResponse with has_password field computed."""
        response = cls.model_validate(user)
        response.has_password = user.password_hash is not None
        return response

    @field_serializer("last_login_at", "created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None, _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 預留給 JWT token payload 使用
class TokenData(BaseModel):
    sub: str | None = None  # subject, e.g., email
