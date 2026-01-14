from unittest.mock import patch
from fastapi import HTTPException
from app.schemas.recorder import RecorderResponse
from app.core.config import settings


def test_get_recorders(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorders.return_value = []

        response = client.get(f"{settings.api_prefix}/recorders/")
        assert response.status_code == 200
        assert response.json() == []


def test_get_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123", sensitivity=-160.0
        )

        response = client.get(f"{settings.api_prefix}/recorders/1")
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123"


def test_create_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123", sensitivity=-160.0
        )

        response = client.post(
            f"{settings.api_prefix}/recorders/",
            json={
                "brand": "Brand",
                "model": "Model",
                "sn": "SN123",
                "sensitivity": -160.0,
            },
        )
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123"


def test_update_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123_UPDATED", sensitivity=-160.0
        )

        response = client.put(
            f"{settings.api_prefix}/recorders/1", json={"sn": "SN123_UPDATED"}
        )
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123_UPDATED"


def test_create_recorder_duplicate(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_recorder.side_effect = HTTPException(
            status_code=400,
            detail="Recorder with brand 'Brand', model 'Model', and SN 'SN123' already exists.",
        )

        response = client.post(
            f"{settings.api_prefix}/recorders/",
            json={
                "brand": "Brand",
                "model": "Model",
                "sn": "SN123",
                "sensitivity": -160.0,
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
