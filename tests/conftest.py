import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user
from app.db.session import get_db
from app.enums.enums import UserRole


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_current_user():
    """Mock a logged-in admin user."""
    user = MagicMock()
    user.id = 1
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN.value
    user.full_name = "Admin User"
    user.is_active = True
    user.password_hash = "hashed-password"
    user.oauth_provider = None
    return user


@pytest.fixture
def client(mock_db, mock_current_user):
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_s3_client():
    """Mock the S3 client for all tests."""
    with patch("app.api.v1.endpoints.api_audio.get_s3_client") as mock_get_s3:
        mock_client = MagicMock()
        mock_get_s3.return_value = mock_client
        yield mock_client
