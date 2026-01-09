from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.enums.enums import UserRole
from app.models.user import UserInfo
from app.schemas.user import UserCreate
from app.utils.common import format_welcome_message


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: UserCreate) -> UserInfo:
        existing_user = (
            self.db.query(UserInfo).filter((UserInfo.email == user.email)).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="UserInfo with the same email already exists.",
            )

        db_user = UserInfo(
            email=user.email,
            full_name=user.full_name,
            role=user.role or UserRole.USER.value,
            password_hash=hash_password(user.password),
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # Placeholder for welcome message side-effect
        print(format_welcome_message(db_user.full_name or db_user.email))

        return db_user

    def authenticate_user(self, email: str, password: str) -> UserInfo | None:
        user = self.db.query(UserInfo).filter(UserInfo.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
