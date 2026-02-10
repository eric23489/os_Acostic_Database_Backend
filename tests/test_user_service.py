"""
UserService 測試 - P0 (必須)

測試 user_service.py 的業務邏輯:
1. create_user - 建立使用者
2. authenticate_user - 認證使用者
3. get_users - 取得使用者列表
4. update_user - 更新使用者
5. delete_user - 軟刪除使用者
6. restore_user - 還原使用者
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.enums.enums import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

# =============================================================================
# create_user 測試
# =============================================================================


class TestUserServiceCreateUser:
    """測試 UserService.create_user 方法。"""

    @patch("app.services.user_service.hash_password")
    @patch("app.services.user_service.format_welcome_message")
    def test_create_user_success(self, mock_welcome, mock_hash):
        """成功建立使用者。"""
        mock_hash.return_value = "hashed_password"
        mock_welcome.return_value = "Welcome!"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user_data = UserCreate(
            email="new@example.com",
            password="password123",
            full_name="New User",
        )

        service = UserService(mock_db)
        service.create_user(user_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        mock_hash.assert_called_once_with("password123")

    @patch("app.services.user_service.hash_password")
    def test_create_user_duplicate_email_raises_400(self, mock_hash):
        """重複 email 觸發 400 錯誤。"""
        mock_db = MagicMock()
        existing_user = MagicMock()
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = existing_user

        user_data = UserCreate(
            email="existing@example.com",
            password="password123",
        )

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    @patch("app.services.user_service.hash_password")
    @patch("app.services.user_service.format_welcome_message")
    def test_create_user_default_role_is_user(self, mock_welcome, mock_hash):
        """預設角色為 USER。"""
        mock_hash.return_value = "hashed"
        mock_welcome.return_value = "Welcome!"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # 捕獲傳入 db.add 的物件
        added_user = None

        def capture_add(user):
            nonlocal added_user
            added_user = user

        mock_db.add.side_effect = capture_add

        user_data = UserCreate(
            email="test@example.com",
            password="password123",
        )

        service = UserService(mock_db)
        service.create_user(user_data)

        assert added_user.role == UserRole.USER.value


# =============================================================================
# authenticate_user 測試
# =============================================================================


class TestUserServiceAuthenticateUser:
    """測試 UserService.authenticate_user 方法。"""

    @patch("app.services.user_service.verify_password")
    def test_authenticate_user_success(self, mock_verify):
        """成功認證使用者。"""
        mock_verify.return_value = True

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        result = service.authenticate_user("test@example.com", "password123")

        assert result == mock_user
        mock_verify.assert_called_once_with("password123", "hashed")

    def test_authenticate_user_not_found_returns_none(self):
        """使用者不存在回傳 None。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)
        result = service.authenticate_user("notfound@example.com", "password")

        assert result is None

    @patch("app.services.user_service.verify_password")
    def test_authenticate_user_wrong_password_returns_none(self, mock_verify):
        """密碼錯誤回傳 None。"""
        mock_verify.return_value = False

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = "hashed"
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        result = service.authenticate_user("test@example.com", "wrong_password")

        assert result is None

    @patch("app.services.user_service.verify_password")
    def test_authenticate_user_inactive_returns_none(self, mock_verify):
        """停用使用者回傳 None。"""
        mock_verify.return_value = True

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = "hashed"
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        result = service.authenticate_user("test@example.com", "password123")

        assert result is None


# =============================================================================
# get_users 測試
# =============================================================================


class TestUserServiceGetUsers:
    """測試 UserService.get_users 方法。"""

    def test_get_users_returns_list(self):
        """回傳使用者列表。"""
        mock_db = MagicMock()
        mock_users = [MagicMock(), MagicMock()]
        mock_chain = mock_db.query.return_value.filter.return_value
        mock_chain.offset.return_value.limit.return_value.all.return_value = mock_users

        service = UserService(mock_db)
        result = service.get_users()

        assert result == mock_users

    def test_get_users_with_pagination(self):
        """支援分頁參數。"""
        mock_db = MagicMock()
        mock_chain = mock_db.query.return_value.filter.return_value
        mock_chain.offset.return_value.limit.return_value.all.return_value = []

        service = UserService(mock_db)
        service.get_users(skip=10, limit=20)

        mock_chain.offset.assert_called_with(10)
        mock_chain.offset.return_value.limit.assert_called_with(20)

    def test_get_users_empty_list(self):
        """無使用者回傳空列表。"""
        mock_db = MagicMock()
        mock_chain = mock_db.query.return_value.filter.return_value
        mock_chain.offset.return_value.limit.return_value.all.return_value = []

        service = UserService(mock_db)
        result = service.get_users()

        assert result == []


# =============================================================================
# update_user 測試
# =============================================================================


class TestUserServiceUpdateUser:
    """測試 UserService.update_user 方法。"""

    def test_update_user_success(self):
        """成功更新使用者。"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.full_name = "Old Name"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        update_data = UserUpdate(full_name="New Name")

        service = UserService(mock_db)
        service.update_user(1, update_data)

        assert mock_user.full_name == "New Name"
        mock_db.commit.assert_called_once()

    def test_update_user_not_found_raises_404(self):
        """使用者不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        update_data = UserUpdate(full_name="New Name")

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.update_user(999, update_data)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @patch("app.services.user_service.hash_password")
    def test_update_user_with_password(self, mock_hash):
        """更新密碼時重新 hash。"""
        mock_hash.return_value = "new_hashed_password"

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password_hash = "old_hash"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        update_data = UserUpdate(password="new_password")

        service = UserService(mock_db)
        service.update_user(1, update_data)

        mock_hash.assert_called_once_with("new_password")
        assert mock_user.password_hash == "new_hashed_password"

    def test_update_user_partial_update(self):
        """部分更新只修改指定欄位。"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.full_name = "Original Name"
        mock_user.email = "original@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # 只更新 full_name
        update_data = UserUpdate(full_name="Updated Name")

        service = UserService(mock_db)
        service.update_user(1, update_data)

        assert mock_user.full_name == "Updated Name"
        # email 不應被修改 (仍保持原值)
        assert mock_user.email == "original@example.com"


# =============================================================================
# delete_user 測試
# =============================================================================


class TestUserServiceDeleteUser:
    """測試 UserService.delete_user 方法。"""

    def test_delete_user_success(self):
        """成功軟刪除使用者。"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_deleted = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        service = UserService(mock_db)
        service.delete_user(1, deleted_by_id=2)

        assert mock_user.is_deleted is True
        assert mock_user.deleted_by == 2
        assert mock_user.deleted_at is not None
        mock_db.commit.assert_called_once()

    def test_delete_user_not_found_raises_404(self):
        """使用者不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.delete_user(999, deleted_by_id=1)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


# =============================================================================
# restore_user 測試
# =============================================================================


class TestUserServiceRestoreUser:
    """測試 UserService.restore_user 方法。"""

    def test_restore_user_success(self):
        """成功還原使用者。"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "deleted@example.com"
        mock_user.is_deleted = True
        mock_user.deleted_at = datetime.now(UTC)
        mock_user.deleted_by = 2

        # 第一次查詢找到使用者，第二次查詢確認無 email 衝突
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,
            None,
        ]

        service = UserService(mock_db)
        service.restore_user(1)

        assert mock_user.is_deleted is False
        assert mock_user.deleted_at is None
        assert mock_user.deleted_by is None
        mock_db.commit.assert_called_once()

    def test_restore_user_not_found_raises_404(self):
        """使用者不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.restore_user(999)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    def test_restore_user_email_collision_raises_400(self):
        """email 衝突觸發 400 錯誤。"""
        mock_db = MagicMock()
        deleted_user = MagicMock()
        deleted_user.id = 1
        deleted_user.email = "test@example.com"
        deleted_user.is_deleted = True

        active_user = MagicMock()
        active_user.id = 2
        active_user.email = "test@example.com"
        active_user.is_deleted = False

        # 第一次查詢找到已刪除使用者，第二次查詢發現有同 email 的活躍使用者
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            deleted_user,
            active_user,
        ]

        service = UserService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.restore_user(1)

        assert exc_info.value.status_code == 400
        assert "Cannot restore" in exc_info.value.detail
