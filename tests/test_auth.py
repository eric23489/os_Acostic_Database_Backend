"""Unit tests for auth functions."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from jose import jwt

from app.core.auth import get_current_user, get_current_admin_user
from app.core.config import settings
from app.enums.enums import UserRole


class TestGetCurrentUser:
    """Tests for get_current_user function."""

    def test_get_current_user_valid_token(self):
        """Should return user with valid token."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # Create valid token
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "test@example.com", "exp": expire},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        result = get_current_user(token=token, db=mock_db)

        assert result == mock_user

    def test_get_current_user_invalid_token(self):
        """Should raise 401 for invalid token."""
        mock_db = MagicMock()
        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=invalid_token, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_get_current_user_expired_token(self):
        """Should raise 401 for expired token."""
        mock_db = MagicMock()

        # Create expired token
        expire = datetime.now(timezone.utc) - timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "test@example.com", "exp": expire},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401

    def test_get_current_user_no_email_in_token(self):
        """Should raise 401 when token has no email (sub)."""
        mock_db = MagicMock()

        # Create token without 'sub' field
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode(
            {"exp": expire},  # No 'sub' field
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401

    def test_get_current_user_user_not_found(self):
        """Should raise 401 when user not found in database."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Create valid token
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "notfound@example.com", "exp": expire},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401

    def test_get_current_user_inactive_user(self):
        """Should raise 400 for inactive user."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # Create valid token
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "inactive@example.com", "exp": expire},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail

    def test_get_current_user_wrong_algorithm(self):
        """Should raise 401 when token uses wrong algorithm."""
        mock_db = MagicMock()

        # Create token with different algorithm
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode(
            {"sub": "test@example.com", "exp": expire},
            "different_secret",  # Different secret
            algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401


class TestGetCurrentAdminUser:
    """Tests for get_current_admin_user function."""

    def test_get_current_admin_user_is_admin(self):
        """Should return user when user is admin."""
        mock_user = MagicMock()
        mock_user.role = UserRole.ADMIN.value

        result = get_current_admin_user(current_user=mock_user)

        assert result == mock_user

    def test_get_current_admin_user_not_admin(self):
        """Should raise 403 when user is not admin."""
        mock_user = MagicMock()
        mock_user.role = UserRole.USER.value

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(current_user=mock_user)

        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail

    def test_get_current_admin_user_other_role(self):
        """Should raise 403 for any non-admin role."""
        mock_user = MagicMock()
        mock_user.role = "editor"  # Some other role

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(current_user=mock_user)

        assert exc_info.value.status_code == 403
