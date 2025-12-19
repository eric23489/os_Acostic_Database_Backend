from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.enums.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[str] = UserRole.USER.value
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False


class UserCreate(UserBase):
    password_hash: str


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

    class Config:
        from_attributes = True
