
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.security import create_access_token
from app.db.session import get_db
from app.enums.enums import UserRole
from app.schemas.oauth import (
    OAuthLinkRequest,
    OAuthLinkResponse,
    OAuthUnlinkResponse,
    SetPasswordRequest,
    SetPasswordResponse,
)
from app.schemas.user import Token, UserCreate, UserResponse, UserUpdate
from app.services.oauth_service import OAuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.create_user(user)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # OAuth2PasswordRequestForm uses the 'username' field to carry the user's email
    email = form_data.username
    user = UserService(db).authenticate_user(email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user=Depends(get_current_user)):
    """Get current logged-in user info."""
    return UserResponse.from_orm_with_password_check(current_user)


@router.get("/", response_model=list[UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin query all accounts."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return UserService(db).get_users(skip=skip, limit=limit)


@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update own data."""
    return UserService(db).update_user(current_user.id, user_in)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin update data."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return UserService(db).update_user(user_id, user_in)


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin delete user (soft delete)."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return UserService(db).delete_user(user_id, current_user.id)


@router.post("/{user_id}/restore", response_model=UserResponse)
def restore_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Admin restore user."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return UserService(db).restore_user(user_id)


@router.put("/me/password", response_model=SetPasswordResponse)
def set_password(
    request: SetPasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Set or update password for current user.

    OAuth-only users can use this to set a password for alternative login.
    """
    UserService(db).set_password(current_user.id, request.password)
    return SetPasswordResponse(message="Password has been set successfully")


@router.post("/me/oauth/link", response_model=OAuthLinkResponse)
def link_oauth(
    request: OAuthLinkRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Link Google account to current user.

    The code should be obtained by completing the Google OAuth flow
    from /oauth/google/authorize.
    """
    service = OAuthService(db)
    user = service.link_google_account(current_user, request.code)
    return OAuthLinkResponse(
        message="Google account linked successfully",
        oauth_provider=user.oauth_provider,
    )


@router.delete("/me/oauth/unlink", response_model=OAuthUnlinkResponse)
def unlink_oauth(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Unlink Google account from current user.

    Requires that the user has a password set first.
    """
    service = OAuthService(db)
    service.unlink_google_account(current_user)
    return OAuthUnlinkResponse(message="Google account unlinked successfully")
