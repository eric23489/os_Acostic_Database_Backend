from unittest.mock import patch, MagicMock
from app.schemas.user import UserResponse, Token
from app.enums.enums import UserRole
from app.core.auth import get_current_user
from app.main import app


def test_create_user(client):
    with patch("app.api.v1.endpoints.api_users.UserService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_user.return_value = UserResponse(
            id=1,
            email="test@example.com",
            full_name="Test User",
            role=UserRole.USER.value,
            is_active=True,
        )

        response = client.post(
            "/users/",
            json={
                "email": "test@example.com",
                "password": "password",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"


def test_login(client):
    with patch("app.api.v1.endpoints.api_users.UserService") as MockService:
        mock_service = MockService.return_value
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_service.authenticate_user.return_value = mock_user

        response = client.post(
            "/users/login",
            data={"username": "test@example.com", "password": "password"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


def test_read_users_me(client, mock_current_user):
    response = client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == mock_current_user.email


def test_read_users_admin(client):
    with patch("app.api.v1.endpoints.api_users.UserService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_users.return_value = []

        response = client.get("/users/")
        assert response.status_code == 200
        assert response.json() == []


def test_read_users_forbidden(client):
    # Override dependency to simulate non-admin user
    non_admin = MagicMock()
    non_admin.role = UserRole.USER.value
    app.dependency_overrides[get_current_user] = lambda: non_admin

    response = client.get("/users/")
    assert response.status_code == 403


def test_update_user_me(client):
    with patch("app.api.v1.endpoints.api_users.UserService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_user.return_value = UserResponse(
            id=1,
            email="admin@example.com",
            full_name="Updated Name",
            role=UserRole.ADMIN.value,
            is_active=True,
        )

        response = client.put("/users/me", json={"full_name": "Updated Name"})
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"
