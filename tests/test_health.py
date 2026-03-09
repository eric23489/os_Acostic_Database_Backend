from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def health_client():
    """Test client with real get_db dependency overridden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock_db
    app.dependency_overrides.pop(get_db, None)


def test_health_all_ok(health_client):
    client, mock_db = health_client
    with patch("app.api.v1.endpoints.api_health.get_s3_health_client") as mock_s3:
        mock_s3.return_value.list_buckets.return_value = {}
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["minio"] == "ok"


def test_health_db_failure(health_client):
    client, mock_db = health_client
    mock_db.execute.side_effect = Exception("connection refused")
    with patch("app.api.v1.endpoints.api_health.get_s3_health_client") as mock_s3:
        mock_s3.return_value.list_buckets.return_value = {}
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "error"
    assert data["minio"] == "ok"


def test_health_minio_failure(health_client):
    client, mock_db = health_client
    with patch("app.api.v1.endpoints.api_health.get_s3_health_client") as mock_s3:
        mock_s3.return_value.list_buckets.side_effect = Exception(
            "endpoint unreachable"
        )
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "ok"
    assert data["minio"] == "error"


def test_health_both_failure(health_client):
    client, mock_db = health_client
    mock_db.execute.side_effect = Exception("db down")
    with patch("app.api.v1.endpoints.api_health.get_s3_health_client") as mock_s3:
        mock_s3.return_value.list_buckets.side_effect = Exception("minio down")
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] == "error"
    assert data["minio"] == "error"
