"""Tests for password reset functionality."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.enums.enums import UserRole


class TestForgotPassword:
    """Tests for forgot password endpoint."""

    def test_forgot_password_with_password_account(self, client, mock_db):
        """Test forgot password for account with password."""
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.return_value = (
                "reset-token-123",
                True,  # has_password
                False,  # has_google_oauth
            )
            mock_service.send_reset_email.return_value = True

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "user@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "reset" in data["message"].lower() or "sent" in data["message"].lower()
            assert data["has_google_oauth"] is False

    def test_forgot_password_oauth_only_account(self, client, mock_db):
        """Test forgot password for OAuth-only account."""
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.return_value = (
                None,  # no token
                False,  # has_password
                True,  # has_google_oauth
            )

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "oauth@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "google" in data["message"].lower()
            assert data["has_google_oauth"] is True

    def test_forgot_password_with_google_and_password(self, client, mock_db):
        """Test forgot password for account with both password and Google."""
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.return_value = (
                "reset-token-123",
                True,  # has_password
                True,  # has_google_oauth
            )
            mock_service.send_reset_email.return_value = True

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "both@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_google_oauth"] is True

    def test_forgot_password_nonexistent_email(self, client, mock_db):
        """Test forgot password for non-existent email (should return success)."""
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.return_value = (
                None,
                False,
                False,
            )

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "nonexistent@example.com"},
            )

            # Should return success for security reasons
            assert response.status_code == 200

    def test_forgot_password_deactivated_account(self, client, mock_db):
        """Test forgot password for deactivated account."""
        from fastapi import HTTPException

        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.side_effect = HTTPException(
                status_code=400, detail="This account has been deactivated"
            )

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "deactivated@example.com"},
            )

            assert response.status_code == 400


class TestResetPassword:
    """Tests for reset password endpoint."""

    def test_reset_password_success(self, client, mock_db):
        """Test successfully resetting password."""
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_user = MagicMock()
            mock_service.reset_password.return_value = mock_user

            response = client.post(
                f"{settings.api_prefix}/auth/reset-password",
                json={"token": "valid-token", "new_password": "newpassword123"},
            )

            assert response.status_code == 200
            assert "successfully" in response.json()["message"]

    def test_reset_password_invalid_token(self, client, mock_db):
        """Test reset password with invalid token."""
        from fastapi import HTTPException

        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.reset_password.side_effect = HTTPException(
                status_code=400, detail="Invalid or expired reset token"
            )

            response = client.post(
                f"{settings.api_prefix}/auth/reset-password",
                json={"token": "invalid-token", "new_password": "newpassword123"},
            )

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()

    def test_reset_password_expired_token(self, client, mock_db):
        """Test reset password with expired token."""
        from fastapi import HTTPException

        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.reset_password.side_effect = HTTPException(
                status_code=400,
                detail="Reset token has expired. Please request a new one.",
            )

            response = client.post(
                f"{settings.api_prefix}/auth/reset-password",
                json={"token": "expired-token", "new_password": "newpassword123"},
            )

            assert response.status_code == 400
            assert "expired" in response.json()["detail"].lower()

    def test_reset_password_too_short(self, client, mock_db):
        """Test reset password with too short password."""
        from fastapi import HTTPException

        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.reset_password.side_effect = HTTPException(
                status_code=400, detail="Password must be at least 8 characters"
            )

            response = client.post(
                f"{settings.api_prefix}/auth/reset-password",
                json={"token": "valid-token", "new_password": "short"},
            )

            assert response.status_code == 400


class TestOAuthServiceUnit:
    """Unit tests for OAuthService."""

    def test_authenticate_with_google_new_user(self, mock_db):
        """Test authenticating a new user via Google."""
        from app.services.oauth_service import OAuthService

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with (
            patch.object(
                OAuthService, "exchange_code_for_tokens"
            ) as mock_exchange,
            patch.object(OAuthService, "get_google_user_info") as mock_user_info,
        ):
            mock_exchange.return_value = {"access_token": "test-token"}
            mock_user_info.return_value = {
                "sub": "google-123",
                "email": "new@gmail.com",
                "name": "New User",
            }

            service = OAuthService(mock_db)
            # This would require more setup to fully test
            # Just verify the service can be instantiated
            assert service.db == mock_db

    def test_unlink_requires_password(self, mock_db):
        """Test that unlinking requires a password."""
        from fastapi import HTTPException

        from app.services.oauth_service import OAuthService

        mock_user = MagicMock()
        mock_user.oauth_provider = "google"
        mock_user.password_hash = None

        service = OAuthService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.unlink_google_account(mock_user)

        assert exc_info.value.status_code == 400
        assert "password" in exc_info.value.detail.lower()


class TestPasswordResetServiceUnit:
    """Unit tests for PasswordResetService."""

    def test_initiate_reset_for_nonexistent_user(self, mock_db):
        """Test initiating reset for non-existent user."""
        from app.services.password_reset_service import PasswordResetService

        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PasswordResetService(mock_db)
        token, has_password, has_google = service.initiate_password_reset(
            "nonexistent@example.com"
        )

        assert token is None
        assert has_password is False
        assert has_google is False

    def test_initiate_reset_for_oauth_only_user(self, mock_db):
        """Test initiating reset for OAuth-only user."""
        from app.services.password_reset_service import PasswordResetService

        mock_user = MagicMock()
        mock_user.password_hash = None
        mock_user.oauth_provider = "google"
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)
        token, has_password, has_google = service.initiate_password_reset(
            "oauth@example.com"
        )

        assert token is None
        assert has_password is False
        assert has_google is True

    def test_reset_password_clears_token(self, mock_db):
        """Test that resetting password clears the reset token."""
        from datetime import UTC, datetime, timedelta

        from app.services.password_reset_service import PasswordResetService

        mock_user = MagicMock()
        mock_user.reset_token = "valid-token"
        mock_user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = PasswordResetService(mock_db)
        service.reset_password("valid-token", "newpassword123")

        assert mock_user.reset_token is None
        assert mock_user.reset_token_expires_at is None
        mock_db.commit.assert_called()
