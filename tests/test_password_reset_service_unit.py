"""Unit tests for PasswordResetService."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.services.password_reset_service import PasswordResetService


class TestInitiatePasswordReset:
    """Tests for PasswordResetService.initiate_password_reset."""

    def test_initiate_password_reset_success_with_password(self):
        """Should generate reset token for user with password."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.password_hash = "hashed_password"
        mock_user.oauth_provider = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)
        token, has_password, has_google = service.initiate_password_reset(
            "test@example.com"
        )

        assert token is not None
        assert has_password is True
        assert has_google is False
        mock_db.commit.assert_called_once()

    def test_initiate_password_reset_oauth_only(self):
        """Should return None token for OAuth-only user."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.password_hash = None  # OAuth-only
        mock_user.oauth_provider = "google"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)
        token, has_password, has_google = service.initiate_password_reset(
            "oauth@example.com"
        )

        assert token is None
        assert has_password is False
        assert has_google is True

    def test_initiate_password_reset_user_not_found(self):
        """Should return None for non-existent user (security)."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PasswordResetService(mock_db)
        token, has_password, has_google = service.initiate_password_reset(
            "notfound@example.com"
        )

        assert token is None
        assert has_password is False
        assert has_google is False

    def test_initiate_password_reset_inactive_user(self):
        """Should raise error for inactive user."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.initiate_password_reset("inactive@example.com")

        assert exc_info.value.status_code == 400
        assert "deactivated" in exc_info.value.detail

    def test_initiate_password_reset_with_google_and_password(self):
        """Should generate token for user with both password and Google."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.password_hash = "hashed_password"
        mock_user.oauth_provider = "google"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)
        token, has_password, has_google = service.initiate_password_reset(
            "both@example.com"
        )

        assert token is not None
        assert has_password is True
        assert has_google is True


class TestResetPassword:
    """Tests for PasswordResetService.reset_password."""

    def test_reset_password_success(self):
        """Should reset password successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)

        with patch(
            "app.services.password_reset_service.hash_password"
        ) as mock_hash:
            mock_hash.return_value = "new_hashed_password"
            result = service.reset_password("valid_token", "newpassword123")

        assert mock_user.password_hash == "new_hashed_password"
        assert mock_user.reset_token is None
        assert mock_user.reset_token_expires_at is None
        mock_db.commit.assert_called()

    def test_reset_password_invalid_token(self):
        """Should raise error for invalid token."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PasswordResetService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.reset_password("invalid_token", "newpassword123")

        assert exc_info.value.status_code == 400
        assert "Invalid or expired" in exc_info.value.detail

    def test_reset_password_expired_token(self):
        """Should raise error for expired token."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.reset_token_expires_at = datetime.now(UTC) - timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.reset_password("expired_token", "newpassword123")

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail

    def test_reset_password_expired_at_none(self):
        """Should raise error when expires_at is None."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.reset_token_expires_at = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.reset_password("token", "newpassword123")

        assert exc_info.value.status_code == 400

    def test_reset_password_too_short(self):
        """Should raise error when password is too short."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.reset_password("valid_token", "short")

        assert exc_info.value.status_code == 400
        assert "8 characters" in exc_info.value.detail


class TestSendResetEmail:
    """Tests for PasswordResetService.send_reset_email."""

    def test_send_reset_email_console_mode(self):
        """Should print to console in development mode (no SMTP)."""
        mock_db = MagicMock()
        service = PasswordResetService(mock_db)

        with patch("app.services.password_reset_service.settings") as mock_settings:
            mock_settings.smtp_host = None
            mock_settings.smtp_user = None
            mock_settings.google_oauth_redirect_uri = (
                "http://localhost:8000/api/v1/oauth/google/callback"
            )

            result = service.send_reset_email("test@example.com", "reset_token_123")

        assert result is True

    def test_send_reset_email_smtp_success(self):
        """Should send email via SMTP when configured."""
        mock_db = MagicMock()
        service = PasswordResetService(mock_db)

        with patch("app.services.password_reset_service.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_from_email = "noreply@test.com"
            mock_settings.password_reset_token_expire_minutes = 30
            mock_settings.google_oauth_redirect_uri = (
                "http://localhost:8000/api/v1/oauth/google/callback"
            )

            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = service.send_reset_email("test@example.com", "token123")

        assert result is True

    def test_send_reset_email_smtp_failure_fallback(self):
        """Should fall back to console on SMTP failure."""
        mock_db = MagicMock()
        service = PasswordResetService(mock_db)

        with patch("app.services.password_reset_service.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.google_oauth_redirect_uri = (
                "http://localhost:8000/api/v1/oauth/google/callback"
            )

            with patch("smtplib.SMTP") as mock_smtp:
                mock_smtp.side_effect = Exception("SMTP error")

                result = service.send_reset_email("test@example.com", "token123")

        # Should still return True (fallback to console)
        assert result is True
