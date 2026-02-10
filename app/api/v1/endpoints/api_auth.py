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
    For security, always returns generic message to prevent account enumeration.
    """
    service = PasswordResetService(db)
    reset_token, _has_password, _has_google_oauth = service.initiate_password_reset(
        request.email
    )

    # Send reset email if token was generated
    if reset_token:
        service.send_reset_email(request.email, reset_token)

    # For security, always return a generic message and do not expose OAuth binding.
    message = "If this email exists, a password reset link has been sent."

    return ForgotPasswordResponse(
        message=message,
        has_google_oauth=False,
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
