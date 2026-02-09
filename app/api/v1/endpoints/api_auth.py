"""Authentication API endpoints (password reset)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.password_reset_service import PasswordResetService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Initiate password reset.

    Sends a password reset email if the email exists and has a password.
    For OAuth-only accounts, suggests using Google login instead.

    For security, always returns success even if email doesn't exist.
    """
    service = PasswordResetService(db)
    reset_token, has_password, has_google_oauth = service.initiate_password_reset(
        request.email
    )

    # Build response message
    if reset_token:
        # User has password, send reset email
        service.send_reset_email(request.email, reset_token)

        if has_google_oauth:
            message = "Password reset email sent. You can also log in with Google."
        else:
            message = "If this email exists, a password reset link has been sent."
    elif has_google_oauth:
        # OAuth-only account
        message = "This account uses Google login. Please use Google to sign in."
    else:
        # User not found or other case - return generic message
        message = "If this email exists, a password reset link has been sent."

    return ForgotPasswordResponse(
        message=message,
        has_google_oauth=has_google_oauth,
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password using token.

    The token is obtained from the password reset email link.
    """
    service = PasswordResetService(db)
    service.reset_password(request.token, request.new_password)

    return ResetPasswordResponse(message="Password has been reset successfully")
