from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.enums.enums import UserRole
from app.models.user import UserInfo
from app.schemas.user import UserCreate, UserUpdate
from app.utils.common import format_welcome_message


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: UserCreate) -> UserInfo:
        existing_user = (
            self.db.query(UserInfo)
            .filter(UserInfo.email == user.email, UserInfo.is_deleted.is_(False))
            .first()
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
        user = (
            self.db.query(UserInfo)
            .filter(UserInfo.email == email, UserInfo.is_deleted.is_(False))
            .first()
        )
        if not user:
            return None
        # OAuth-only users have no password
        if not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    def get_users(self, skip: int = 0, limit: int = 100) -> list[UserInfo]:
        return (
            self.db.query(UserInfo)
            .filter(UserInfo.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_user(self, user_id: int, user_in: UserUpdate) -> UserInfo:
        user = (
            self.db.query(UserInfo)
            .filter(UserInfo.id == user_id, UserInfo.is_deleted.is_(False))
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            password = update_data.pop("password")
            if password:
                user.password_hash = hash_password(password)

        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int, deleted_by_id: int) -> UserInfo:
        user = (
            self.db.query(UserInfo)
            .filter(UserInfo.id == user_id, UserInfo.is_deleted.is_(False))
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.is_deleted = True
        user.deleted_at = datetime.now(UTC)
        user.deleted_by = deleted_by_id
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def restore_user(self, user_id: int) -> UserInfo:
        user = self.db.query(UserInfo).filter(UserInfo.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check for email collision
        if (
            self.db.query(UserInfo)
            .filter(
                UserInfo.email == user.email,
                UserInfo.is_deleted.is_(False),
                UserInfo.id != user_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active user with this email already exists. Cannot restore.",
            )

        user.is_deleted = False
        user.deleted_at = None
        user.deleted_by = None
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_password(self, user_id: int, password: str) -> UserInfo:
        """Set or update password for user.

        Args:
            user_id: User ID.
            password: New password.

        Returns:
            Updated user.
        """
        user = (
            self.db.query(UserInfo)
            .filter(UserInfo.id == user_id, UserInfo.is_deleted.is_(False))
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Validate password length
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )

        user.password_hash = hash_password(password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
