"""Tests for Google OAuth functionality."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.auth import get_current_user
from app.core.config import settings
from app.enums.enums import UserRole
from app.main import app


class TestGoogleOAuthAuthorize:
    """Tests for Google OAuth authorize endpoint."""

    def test_get_authorization_url(self, client):
        """Test getting Google OAuth authorization URL."""
        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "test-client-id"
            mock_settings.google_oauth_redirect_uri = "http://test/callback"

            response = client.get(f"{settings.api_prefix}/oauth/google/authorize")

            assert response.status_code == 200
            data = response.json()
            assert "authorization_url" in data
            assert "accounts.google.com" in data["authorization_url"]

    def test_get_authorization_url_with_state(self, client):
        """Test getting authorization URL with state parameter."""
        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "test-client-id"
            mock_settings.google_oauth_redirect_uri = "http://test/callback"

            response = client.get(
                f"{settings.api_prefix}/oauth/google/authorize?state=csrf-token"
            )

            assert response.status_code == 200
            data = response.json()
            assert "state=csrf-token" in data["authorization_url"]

    def test_get_authorization_url_not_configured(self, client):
        """Test error when OAuth is not configured."""
        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = None

            response = client.get(f"{settings.api_prefix}/oauth/google/authorize")

            assert response.status_code == 500
            assert "not configured" in response.json()["detail"]


class TestGoogleOAuthCallback:
    """Tests for Google OAuth callback endpoint."""

    def test_callback_new_user(self, client, mock_db):
        """Test callback for new user registration."""
        with patch(
            "app.api.v1.endpoints.api_oauth.OAuthService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_user = MagicMock()
            mock_user.email = "newuser@gmail.com"
            mock_service.authenticate_with_google.return_value = (mock_user, True)

            with patch(
                "app.api.v1.endpoints.api_oauth.create_jwt_for_user"
            ) as mock_jwt:
                mock_jwt.return_value = "test-jwt-token"

                response = client.get(
                    f"{settings.api_prefix}/oauth/google/callback?code=auth-code"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "test-jwt-token"
                assert data["is_new_user"] is True

    def test_callback_existing_user(self, client, mock_db):
        """Test callback for existing user login."""
        with patch(
            "app.api.v1.endpoints.api_oauth.OAuthService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_user = MagicMock()
            mock_user.email = "existing@gmail.com"
            mock_service.authenticate_with_google.return_value = (mock_user, False)

            with patch(
                "app.api.v1.endpoints.api_oauth.create_jwt_for_user"
            ) as mock_jwt:
                mock_jwt.return_value = "test-jwt-token"

                response = client.get(
                    f"{settings.api_prefix}/oauth/google/callback?code=auth-code"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["is_new_user"] is False

    def test_callback_invalid_code(self, client, mock_db):
        """Test callback with invalid authorization code."""
        from fastapi import HTTPException

        with patch(
            "app.api.v1.endpoints.api_oauth.OAuthService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.authenticate_with_google.side_effect = HTTPException(
                status_code=401, detail="Failed to exchange authorization code"
            )

            response = client.get(
                f"{settings.api_prefix}/oauth/google/callback?code=invalid-code"
            )

            assert response.status_code == 401


class TestSetPassword:
    """Tests for setting password on OAuth account."""

    def test_set_password_success(self, client, mock_current_user):
        """Test successfully setting password."""
        mock_current_user.password_hash = None

        with patch("app.api.v1.endpoints.api_users.UserService") as MockService:
            mock_service = MockService.return_value
            mock_service.set_password.return_value = mock_current_user

            response = client.put(
                f"{settings.api_prefix}/users/me/password",
                json={"password": "newpassword123"},
            )

            assert response.status_code == 200
            assert "successfully" in response.json()["message"]

    def test_set_password_too_short(self, client, mock_current_user):
        """Test setting password that is too short."""
        from fastapi import HTTPException

        with patch("app.api.v1.endpoints.api_users.UserService") as MockService:
            mock_service = MockService.return_value
            mock_service.set_password.side_effect = HTTPException(
                status_code=400, detail="Password must be at least 8 characters"
            )

            response = client.put(
                f"{settings.api_prefix}/users/me/password",
                json={"password": "short"},
            )

            assert response.status_code == 400


class TestOAuthLink:
    """Tests for linking Google account."""

    def test_link_google_success(self, client, mock_current_user):
        """Test successfully linking Google account."""
        mock_current_user.oauth_provider = None

        with patch("app.api.v1.endpoints.api_users.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_current_user.oauth_provider = "google"
            mock_service.link_google_account.return_value = mock_current_user

            response = client.post(
                f"{settings.api_prefix}/users/me/oauth/link",
                json={"code": "google-auth-code"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["oauth_provider"] == "google"

    def test_link_google_already_linked(self, client, mock_current_user):
        """Test linking when already linked."""
        from fastapi import HTTPException

        mock_current_user.oauth_provider = "google"

        with patch("app.api.v1.endpoints.api_users.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.link_google_account.side_effect = HTTPException(
                status_code=400, detail="Account already linked to Google"
            )

            response = client.post(
                f"{settings.api_prefix}/users/me/oauth/link",
                json={"code": "google-auth-code"},
            )

            assert response.status_code == 400

    def test_link_google_account_in_use(self, client, mock_current_user):
        """Test linking when Google account is already used by another user."""
        from fastapi import HTTPException

        with patch("app.api.v1.endpoints.api_users.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.link_google_account.side_effect = HTTPException(
                status_code=400,
                detail="This Google account is already linked to another user",
            )

            response = client.post(
                f"{settings.api_prefix}/users/me/oauth/link",
                json={"code": "google-auth-code"},
            )

            assert response.status_code == 400


class TestOAuthUnlink:
    """Tests for unlinking Google account."""

    def test_unlink_google_success(self, client, mock_current_user):
        """Test successfully unlinking Google account."""
        mock_current_user.oauth_provider = "google"
        mock_current_user.password_hash = "hashed-password"

        with patch("app.api.v1.endpoints.api_users.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_current_user.oauth_provider = None
            mock_service.unlink_google_account.return_value = mock_current_user

            response = client.delete(f"{settings.api_prefix}/users/me/oauth/unlink")

            assert response.status_code == 200
            assert "successfully" in response.json()["message"]

    def test_unlink_google_no_password(self, client, mock_current_user):
        """Test unlinking when no password is set."""
        from fastapi import HTTPException

        mock_current_user.oauth_provider = "google"
        mock_current_user.password_hash = None

        with patch("app.api.v1.endpoints.api_users.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.unlink_google_account.side_effect = HTTPException(
                status_code=400,
                detail="Please set a password before unlinking Google account",
            )

            response = client.delete(f"{settings.api_prefix}/users/me/oauth/unlink")

            assert response.status_code == 400

    def test_unlink_google_not_linked(self, client, mock_current_user):
        """Test unlinking when not linked."""
        from fastapi import HTTPException

        mock_current_user.oauth_provider = None

        with patch("app.api.v1.endpoints.api_users.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.unlink_google_account.side_effect = HTTPException(
                status_code=400, detail="Account is not linked to Google"
            )

            response = client.delete(f"{settings.api_prefix}/users/me/oauth/unlink")

            assert response.status_code == 400
