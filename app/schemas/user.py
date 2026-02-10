from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer

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

    model_config = ConfigDict(from_attributes=True)

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
