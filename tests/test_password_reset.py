"""Tests for password reset functionality."""

from unittest.mock import MagicMock, patch

from app.core.config import settings


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
        """Test forgot password for OAuth-only account.

        For security, the response should NOT reveal OAuth status.
        """
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.return_value = (
                None,  # no token
                False,  # has_password
                True,  # has_google_oauth (but should not be exposed)
            )

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "oauth@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            # Security: always return generic message, never expose OAuth status
            assert "email" in data["message"].lower() or "sent" in data["message"].lower()
            assert data["has_google_oauth"] is False  # Never expose for security

    def test_forgot_password_with_google_and_password(self, client, mock_db):
        """Test forgot password for account with both password and Google.

        For security, the response should NOT reveal OAuth status.
        """
        with patch(
            "app.api.v1.endpoints.api_auth.PasswordResetService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_password_reset.return_value = (
                "reset-token-123",
                True,  # has_password
                True,  # has_google_oauth (but should not be exposed)
            )
            mock_service.send_reset_email.return_value = True

            response = client.post(
                f"{settings.api_prefix}/auth/forgot-password",
                json={"email": "both@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["has_google_oauth"] is False  # Never expose for security

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
