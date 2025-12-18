from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.common import format_welcome_message


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: UserCreate) -> User:
        existing_user = (
            self.db.query(User)
            .filter((User.email == user.email) | (User.username == user.username))
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with the same username or email already exists.",
            )

        db_user = User(
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
