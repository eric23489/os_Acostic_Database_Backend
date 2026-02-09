"""Unit tests for OAuthService."""

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.services.oauth_service import OAuthService, create_jwt_for_user


class TestGetGoogleAuthorizationUrl:
    """Tests for OAuthService.get_google_authorization_url."""

    def test_get_authorization_url_success(self):
        """Should return Google authorization URL."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "test_client_id"
            mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

            url = service.get_google_authorization_url()

        assert "accounts.google.com" in url
        assert "test_client_id" in url
        assert "redirect_uri" in url

    def test_get_authorization_url_with_state(self):
        """Should include state parameter when provided."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "test_client_id"
            mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

            url = service.get_google_authorization_url(state="csrf_state_123")

        assert "state=csrf_state_123" in url

    def test_get_authorization_url_not_configured(self):
        """Should raise error when OAuth not configured."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = None

            with pytest.raises(HTTPException) as exc_info:
                service.get_google_authorization_url()

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail


class TestExchangeCodeForTokens:
    """Tests for OAuthService.exchange_code_for_tokens."""

    def test_exchange_code_success(self):
        """Should exchange code for tokens successfully."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "client_id"
            mock_settings.google_oauth_client_secret = "client_secret"
            mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": "access_token_123",
                    "refresh_token": "refresh_token_123",
                }
                mock_post.return_value = mock_response

                tokens = service.exchange_code_for_tokens("auth_code_123")

        assert tokens["access_token"] == "access_token_123"

    def test_exchange_code_failure(self):
        """Should raise error on token exchange failure."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "client_id"
            mock_settings.google_oauth_client_secret = "client_secret"
            mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_post.return_value = mock_response

                with pytest.raises(HTTPException) as exc_info:
                    service.exchange_code_for_tokens("invalid_code")

        assert exc_info.value.status_code == 401

    def test_exchange_code_not_configured(self):
        """Should raise error when OAuth not configured."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = None
            mock_settings.google_oauth_client_secret = None

            with pytest.raises(HTTPException) as exc_info:
                service.exchange_code_for_tokens("auth_code")

        assert exc_info.value.status_code == 500


class TestAuthenticateWithGoogle:
    """Tests for OAuthService.authenticate_with_google."""

    def _setup_oauth_mocks(self, mock_settings):
        """Set up common OAuth settings mocks."""
        mock_settings.google_oauth_client_id = "client_id"
        mock_settings.google_oauth_client_secret = "client_secret"
        mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

    def test_authenticate_new_user(self):
        """Should create new user for first-time Google login."""
        mock_db = MagicMock()
        service = OAuthService(mock_db)

        # No existing users
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.oauth_service.settings") as mock_settings:
            self._setup_oauth_mocks(mock_settings)

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"access_token": "token123"}
                mock_post.return_value = mock_response

                with patch("app.services.oauth_service.requests.get") as mock_get:
                    mock_user_response = MagicMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = {
                        "sub": "google_user_id",
                        "email": "new@example.com",
                        "name": "New User",
                    }
                    mock_get.return_value = mock_user_response

                    user, is_new = service.authenticate_with_google("auth_code")

        assert is_new is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    def test_authenticate_returning_user(self):
        """Should login existing Google user."""
        mock_db = MagicMock()
        mock_existing_user = MagicMock()
        service = OAuthService(mock_db)

        # First query finds existing OAuth user
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_existing_user
        )

        with patch("app.services.oauth_service.settings") as mock_settings:
            self._setup_oauth_mocks(mock_settings)

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"access_token": "token123"}
                mock_post.return_value = mock_response

                with patch("app.services.oauth_service.requests.get") as mock_get:
                    mock_user_response = MagicMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = {
                        "sub": "google_user_id",
                        "email": "existing@example.com",
                        "name": "Existing User",
                    }
                    mock_get.return_value = mock_user_response

                    user, is_new = service.authenticate_with_google("auth_code")

        assert is_new is False
        assert user == mock_existing_user
        mock_db.add.assert_not_called()

    def test_authenticate_auto_link_existing_email(self):
        """Should auto-link Google to existing local account with same email."""
        mock_db = MagicMock()
        mock_local_user = MagicMock()
        mock_local_user.oauth_provider = None
        service = OAuthService(mock_db)

        # First query returns None (no OAuth user)
        # Second query returns local user with same email
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No existing OAuth user
            mock_local_user,  # Local user with same email
        ]

        with patch("app.services.oauth_service.settings") as mock_settings:
            self._setup_oauth_mocks(mock_settings)

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"access_token": "token123"}
                mock_post.return_value = mock_response

                with patch("app.services.oauth_service.requests.get") as mock_get:
                    mock_user_response = MagicMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = {
                        "sub": "google_user_id",
                        "email": "local@example.com",
                        "name": "Local User",
                    }
                    mock_get.return_value = mock_user_response

                    user, is_new = service.authenticate_with_google("auth_code")

        assert is_new is False
        assert mock_local_user.oauth_provider == "google"
        assert mock_local_user.oauth_sub == "google_user_id"

    def test_authenticate_deleted_user(self):
        """Should raise error for soft-deleted user."""
        mock_db = MagicMock()
        mock_deleted_user = MagicMock()
        service = OAuthService(mock_db)

        # No OAuth user, no local user, but found deleted user
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No OAuth user
            None,  # No local user
            mock_deleted_user,  # Deleted user with same email
        ]

        with patch("app.services.oauth_service.settings") as mock_settings:
            self._setup_oauth_mocks(mock_settings)

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"access_token": "token123"}
                mock_post.return_value = mock_response

                with patch("app.services.oauth_service.requests.get") as mock_get:
                    mock_user_response = MagicMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = {
                        "sub": "google_user_id",
                        "email": "deleted@example.com",
                        "name": "Deleted User",
                    }
                    mock_get.return_value = mock_user_response

                    with pytest.raises(HTTPException) as exc_info:
                        service.authenticate_with_google("auth_code")

        assert exc_info.value.status_code == 400
        assert "deactivated" in exc_info.value.detail


class TestLinkGoogleAccount:
    """Tests for OAuthService.link_google_account."""

    def test_link_google_success(self):
        """Should link Google account successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.oauth_provider = None
        mock_user.id = 1
        service = OAuthService(mock_db)

        # No existing OAuth user with same Google ID
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "client_id"
            mock_settings.google_oauth_client_secret = "client_secret"
            mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"access_token": "token123"}
                mock_post.return_value = mock_response

                with patch("app.services.oauth_service.requests.get") as mock_get:
                    mock_user_response = MagicMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = {
                        "sub": "google_user_id",
                        "email": "user@example.com",
                    }
                    mock_get.return_value = mock_user_response

                    result = service.link_google_account(mock_user, "auth_code")

        assert mock_user.oauth_provider == "google"
        assert mock_user.oauth_sub == "google_user_id"

    def test_link_google_already_linked(self):
        """Should raise error when already linked."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.oauth_provider = "google"
        service = OAuthService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.link_google_account(mock_user, "auth_code")

        assert exc_info.value.status_code == 400
        assert "already linked" in exc_info.value.detail

    def test_link_google_account_already_used(self):
        """Should raise error when Google account is used by another user."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.oauth_provider = None
        mock_user.id = 1
        mock_other_user = MagicMock()
        service = OAuthService(mock_db)

        # Found another user with same Google ID
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_other_user
        )

        with patch("app.services.oauth_service.settings") as mock_settings:
            mock_settings.google_oauth_client_id = "client_id"
            mock_settings.google_oauth_client_secret = "client_secret"
            mock_settings.google_oauth_redirect_uri = "http://localhost/callback"

            with patch("app.services.oauth_service.requests.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"access_token": "token123"}
                mock_post.return_value = mock_response

                with patch("app.services.oauth_service.requests.get") as mock_get:
                    mock_user_response = MagicMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = {
                        "sub": "google_user_id",
                    }
                    mock_get.return_value = mock_user_response

                    with pytest.raises(HTTPException) as exc_info:
                        service.link_google_account(mock_user, "auth_code")

        assert exc_info.value.status_code == 400
        assert "already linked to another user" in exc_info.value.detail


class TestUnlinkGoogleAccount:
    """Tests for OAuthService.unlink_google_account."""

    def test_unlink_google_success(self):
        """Should unlink Google account successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.oauth_provider = "google"
        mock_user.password_hash = "hashed_password"
        service = OAuthService(mock_db)

        result = service.unlink_google_account(mock_user)

        assert mock_user.oauth_provider is None
        assert mock_user.oauth_sub is None
        mock_db.commit.assert_called_once()

    def test_unlink_google_not_linked(self):
        """Should raise error when not linked."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.oauth_provider = None
        service = OAuthService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.unlink_google_account(mock_user)

        assert exc_info.value.status_code == 400
        assert "not linked" in exc_info.value.detail

    def test_unlink_google_no_password(self):
        """Should raise error when user has no password."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.oauth_provider = "google"
        mock_user.password_hash = None
        service = OAuthService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.unlink_google_account(mock_user)

        assert exc_info.value.status_code == 400
        assert "set a password" in exc_info.value.detail


class TestCreateJwtForUser:
    """Tests for create_jwt_for_user function."""

    def test_create_jwt_for_user(self):
        """Should create JWT token for user."""
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        with patch("app.services.oauth_service.create_access_token") as mock_create:
            mock_create.return_value = "jwt_token_123"

            token = create_jwt_for_user(mock_user)

        assert token == "jwt_token_123"
        mock_create.assert_called_once_with({"sub": "test@example.com"})
