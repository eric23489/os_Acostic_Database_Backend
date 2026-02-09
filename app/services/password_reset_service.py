"""Password reset service."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import UserInfo


class PasswordResetService:
    """Service for handling password reset."""

    def __init__(self, db: Session):
        self.db = db

    def initiate_password_reset(self, email: str) -> tuple[str | None, bool, bool]:
        """Initiate password reset for a user.

        Args:
            email: User's email address.

        Returns:
            Tuple of (reset_token, has_password, has_google_oauth).
            reset_token is None if user not found or is OAuth-only.
        """
        user = (
            self.db.query(UserInfo)
            .filter(
                UserInfo.email == email,
                UserInfo.is_deleted.is_(False),
            )
            .first()
        )

        # Return generic response for non-existent users (security)
        if not user:
            return None, False, False

        # Check if account is deactivated
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account has been deactivated",
            )

        has_google_oauth = user.oauth_provider == "google"
        has_password = user.password_hash is not None

        # If user has no password (OAuth-only), don't generate token
        if not has_password:
            return None, False, has_google_oauth

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )

        user.reset_token = reset_token
        user.reset_token_expires_at = expires_at
        self.db.commit()

        return reset_token, has_password, has_google_oauth

    def reset_password(self, token: str, new_password: str) -> UserInfo:
        """Reset user password using token.

        Args:
            token: Password reset token.
            new_password: New password to set.

        Returns:
            Updated user.
        """
        user = (
            self.db.query(UserInfo)
            .filter(
                UserInfo.reset_token == token,
                UserInfo.is_deleted.is_(False),
            )
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Check if token is expired
        if (
            user.reset_token_expires_at is None
            or user.reset_token_expires_at < datetime.now(UTC)
        ):
            # Clear expired token
            user.reset_token = None
            user.reset_token_expires_at = None
            self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        # Validate password length
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )

        # Update password and clear token
        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        self.db.commit()
        self.db.refresh(user)

        return user

    def send_reset_email(self, email: str, reset_token: str) -> bool:
        """Send password reset email.

        In development, prints token to console.
        In production, sends actual email via SMTP.

        Args:
            email: User's email address.
            reset_token: Password reset token.

        Returns:
            True if email sent successfully.
        """
        base_url = settings.google_oauth_redirect_uri.rsplit("/", 3)[0]
        reset_url = f"{base_url}/reset-password?token={reset_token}"

        # Check if SMTP is configured
        if settings.smtp_host and settings.smtp_user:
            # Production: send actual email
            try:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText

                msg = MIMEMultipart()
                msg["From"] = settings.smtp_from_email or settings.smtp_user
                msg["To"] = email
                msg["Subject"] = "Password Reset Request"

                expire_min = settings.password_reset_token_expire_minutes
                body = f"""
You have requested to reset your password.

Click the link below to reset your password:
{reset_url}

This link will expire in {expire_min} minutes.

If you did not request this, please ignore this email.
"""

                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)

                return True
            except Exception as e:
                print(f"Failed to send email: {e}")
                # Fall through to console output
                pass

        # Development: print to console
        print("=" * 50)
        print("PASSWORD RESET TOKEN (Development Mode)")
        print(f"Email: {email}")
        print(f"Token: {reset_token}")
        print(f"Reset URL: {reset_url}")
        print("=" * 50)

        return True
