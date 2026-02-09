"""Unit tests for UserService."""

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate
from app.enums.enums import UserRole


class TestUserServiceCreateUser:
    """Tests for UserService.create_user."""

    def test_create_user_success(self):
        """Should create user successfully."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)

        with patch("app.services.user_service.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"

            user_data = UserCreate(
                email="test@example.com",
                password="password123",
                full_name="Test User",
            )
            result = service.create_user(user_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_user_email_exists(self):
        """Should raise error when email already exists."""
        mock_db = MagicMock()
        existing_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        service = UserService(mock_db)
        user_data = UserCreate(
            email="existing@example.com",
            password="password123",
        )

        with pytest.raises(HTTPException) as exc_info:
            service.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail


class TestUserServiceAuthenticateUser:
    """Tests for UserService.authenticate_user."""

    def test_authenticate_user_success(self):
        """Should authenticate user with valid credentials."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = "hashed_password"
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = True
            result = service.authenticate_user("test@example.com", "password123")

        assert result == mock_user

    def test_authenticate_user_not_found(self):
        """Should return None when user not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)
        result = service.authenticate_user("notfound@example.com", "password")

        assert result is None

    def test_authenticate_user_wrong_password(self):
        """Should return None when password is wrong."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = "hashed_password"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = False
            result = service.authenticate_user("test@example.com", "wrongpassword")

        assert result is None

    def test_authenticate_user_no_password_hash(self):
        """Should return None for OAuth-only user without password."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = None  # OAuth-only user
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        result = service.authenticate_user("oauth@example.com", "password")

        assert result is None

    def test_authenticate_user_inactive(self):
        """Should return None for inactive user."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = "hashed_password"
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = True
            result = service.authenticate_user("inactive@example.com", "password")

        assert result is None


class TestUserServiceGetUsers:
    """Tests for UserService.get_users."""

    def test_get_users_success(self):
        """Should return list of users."""
        mock_db = MagicMock()
        mock_users = [MagicMock(), MagicMock()]
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_users

        service = UserService(mock_db)
        result = service.get_users(skip=0, limit=100)

        assert result == mock_users


class TestUserServiceUpdateUser:
    """Tests for UserService.update_user."""

    def test_update_user_success(self):
        """Should update user successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        update_data = UserUpdate(full_name="Updated Name")
        result = service.update_user(1, update_data)

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result == mock_user

    def test_update_user_not_found(self):
        """Should raise error when user not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)
        update_data = UserUpdate(full_name="Updated Name")

        with pytest.raises(HTTPException) as exc_info:
            service.update_user(999, update_data)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_update_user_with_password(self):
        """Should update password when provided."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)

        with patch("app.services.user_service.hash_password") as mock_hash:
            mock_hash.return_value = "new_hashed_password"
            update_data = UserUpdate(password="newpassword123")
            result = service.update_user(1, update_data)

        mock_hash.assert_called_once_with("newpassword123")
        assert mock_user.password_hash == "new_hashed_password"


class TestUserServiceDeleteUser:
    """Tests for UserService.delete_user."""

    def test_delete_user_success(self):
        """Should soft delete user successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_deleted = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        result = service.delete_user(1, deleted_by_id=2)

        assert mock_user.is_deleted is True
        assert mock_user.deleted_by == 2
        mock_db.commit.assert_called_once()

    def test_delete_user_not_found(self):
        """Should raise error when user not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.delete_user(999, deleted_by_id=1)

        assert exc_info.value.status_code == 404


class TestUserServiceRestoreUser:
    """Tests for UserService.restore_user."""

    def test_restore_user_success(self):
        """Should restore user successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.is_deleted = True

        # First query finds the deleted user
        # Second query checks for email collision (returns None)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,
            None,
        ]

        service = UserService(mock_db)
        result = service.restore_user(1)

        assert mock_user.is_deleted is False
        assert mock_user.deleted_at is None
        assert mock_user.deleted_by is None

    def test_restore_user_not_found(self):
        """Should raise error when user not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.restore_user(999)

        assert exc_info.value.status_code == 404

    def test_restore_user_email_collision(self):
        """Should raise error when active user with same email exists."""
        mock_db = MagicMock()
        mock_deleted_user = MagicMock()
        mock_deleted_user.email = "test@example.com"
        mock_active_user = MagicMock()

        # First query finds the deleted user, second finds active user with same email
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_deleted_user,
            mock_active_user,
        ]

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.restore_user(1)

        assert exc_info.value.status_code == 400
        assert "Cannot restore" in exc_info.value.detail


class TestUserServiceSetPassword:
    """Tests for UserService.set_password."""

    def test_set_password_success(self):
        """Should set password successfully."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)

        with patch("app.services.user_service.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_new_password"
            result = service.set_password(1, "newpassword123")

        assert mock_user.password_hash == "hashed_new_password"
        mock_db.commit.assert_called_once()

    def test_set_password_user_not_found(self):
        """Should raise error when user not found."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.set_password(999, "newpassword123")

        assert exc_info.value.status_code == 404

    def test_set_password_too_short(self):
        """Should raise error when password is too short."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.set_password(1, "short")

        assert exc_info.value.status_code == 400
        assert "8 characters" in exc_info.value.detail
