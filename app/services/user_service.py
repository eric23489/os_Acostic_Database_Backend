from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import UserInfo
from app.schemas.user import UserCreate
from app.utils.common import format_welcome_message


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: UserCreate) -> UserInfo:
        existing_user = (
            self.db.query(UserInfo)
            .filter((UserInfo.email == user.email) | (UserInfo.username == user.username))
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="UserInfo with the same username or email already exists.",
            )

        db_user = UserInfo(
            username=user.username,
            email=user.email,
            role="admin",
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # Placeholder for welcome message side-effect
        print(format_welcome_message(db_user.username))

        return db_user
