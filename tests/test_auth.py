"""
Auth 模組測試 - P0 (必須)

測試 auth.py 的認證邏輯:
1. get_current_user - JWT 驗證
2. get_current_admin_user - 權限檢查
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.auth import get_current_admin_user, get_current_user
from app.core.config import settings
from app.enums.enums import UserRole

# =============================================================================
# get_current_user 測試
# =============================================================================


class TestGetCurrentUser:
    """測試 get_current_user 函式。"""

    def test_valid_token_returns_user(self):
        """有效 token 回傳使用者。"""
        # 建立有效 token
        token = jwt.encode(
            {"sub": "test@example.com"},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        # Mock DB
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_current_user(token=token, db=mock_db)

        assert result == mock_user
        mock_db.query.assert_called_once()

    def test_invalid_token_raises_401(self):
        """無效 token 觸發 401 錯誤。"""
        invalid_token = "invalid.token.here"
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=invalid_token, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_token_without_sub_raises_401(self):
        """token 缺少 sub 欄位觸發 401 錯誤。"""
        # 建立沒有 sub 的 token
        token = jwt.encode(
            {"other": "data"},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_user_not_found_raises_401(self):
        """使用者不存在觸發 401 錯誤。"""
        token = jwt.encode(
            {"sub": "notfound@example.com"},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    def test_inactive_user_raises_400(self):
        """停用使用者觸發 400 錯誤。"""
        token = jwt.encode(
            {"sub": "inactive@example.com"},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "inactive@example.com"
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail

    def test_expired_token_raises_401(self):
        """過期 token 觸發 401 錯誤。"""
        # 建立過期的 token
        import time

        expired_token = jwt.encode(
            {"sub": "test@example.com", "exp": time.time() - 3600},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=expired_token, db=mock_db)

        assert exc_info.value.status_code == 401

    def test_wrong_secret_key_raises_401(self):
        """使用錯誤 secret key 簽名的 token 觸發 401 錯誤。"""
        wrong_secret_token = jwt.encode(
            {"sub": "test@example.com"},
            "wrong_secret_key",
            algorithm=settings.algorithm,
        )
        mock_db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=wrong_secret_token, db=mock_db)

        assert exc_info.value.status_code == 401


# =============================================================================
# get_current_admin_user 測試
# =============================================================================


class TestGetCurrentAdminUser:
    """測試 get_current_admin_user 函式。"""

    def test_admin_user_returns_user(self):
        """Admin 使用者成功通過。"""
        mock_admin = MagicMock()
        mock_admin.role = UserRole.ADMIN.value

        result = get_current_admin_user(current_user=mock_admin)

        assert result == mock_admin

    def test_non_admin_user_raises_403(self):
        """非 Admin 使用者觸發 403 錯誤。"""
        mock_user = MagicMock()
        mock_user.role = UserRole.USER.value

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(current_user=mock_user)

        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail

    def test_guest_user_raises_403(self):
        """Guest 使用者觸發 403 錯誤。"""
        mock_guest = MagicMock()
        mock_guest.role = UserRole.GUEST.value

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(current_user=mock_guest)

        assert exc_info.value.status_code == 403
        assert "doesn't have enough privileges" in exc_info.value.detail
