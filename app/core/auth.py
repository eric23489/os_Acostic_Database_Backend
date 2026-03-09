import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AUTH_TOKEN_INVALID,
    AUTH_USER_INACTIVE,
    PERMISSION_ADMIN_REQUIRED,
)
from app.db.session import get_db
from app.enums.enums import UserRole
from app.models.user import UserInfo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/users/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise AUTH_TOKEN_INVALID
    except PyJWTError:
        raise AUTH_TOKEN_INVALID from None

    user = db.query(UserInfo).filter(UserInfo.email == email).first()
    if not user:
        raise AUTH_TOKEN_INVALID
    if not user.is_active:
        raise AUTH_USER_INACTIVE
    return user


def get_current_admin_user(
    current_user: UserInfo = Depends(get_current_user),
) -> UserInfo:
    if current_user.role != UserRole.ADMIN.value:
        raise PERMISSION_ADMIN_REQUIRED
    return current_user
