import pytest
from unittest.mock import MagicMock
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
    return user


@pytest.fixture
def client(mock_db, mock_current_user):
    """Test client with mocked dependencies."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
