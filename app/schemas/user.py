from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, EmailStr, ConfigDict, field_serializer
from app.enums.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[str] = UserRole.USER.value
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False


class UserCreate(UserBase):
    password: str  # Plain text password for creation


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_login_at", "created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return dt.astimezone(timezone(timedelta(hours=8)))


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# 預留給 JWT token payload 使用
class TokenData(BaseModel):
    sub: Optional[str] = None  # subject, e.g., email
