from unittest.mock import patch

from fastapi import HTTPException

from app.core.config import settings
from app.core.exceptions import RECORDER_IDENTIFIER_COLLISION
from app.schemas.recorder import RecorderResponse


def test_get_recorders(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorders.return_value = ([], 0)

        response = client.get(f"{settings.api_prefix}/recorders/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["total"] == 0
        assert data["items"] == []
        mock_service.get_recorders.assert_called_once()


def test_get_recorders_with_search(client):
    """Test recorders search and filter."""
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorders.return_value = (
            [
                RecorderResponse(
                    id=1, brand="Brand", model="Model", sn="SN123", sensitivity=-160.0
                )
            ],
            1,
        )

        response = client.get(
            f"{settings.api_prefix}/recorders/?search=SN123&recorder_status=in-service"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        mock_service.get_recorders.assert_called_once()


def test_get_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123", sensitivity=-160.0
        )

        response = client.get(f"{settings.api_prefix}/recorders/1")
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123"
        mock_service.get_recorder.assert_called_once_with(1)


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
        mock_service.create_recorder.assert_called_once()
        assert mock_service.create_recorder.call_args[0][0].sn == "SN123"


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
        mock_service.update_recorder.assert_called_once()
        assert mock_service.update_recorder.call_args[0][0] == 1
        assert mock_service.update_recorder.call_args[0][1].sn == "SN123_UPDATED"


def test_create_recorder_duplicate(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_recorder.side_effect = RECORDER_IDENTIFIER_COLLISION

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
        assert "already exists" in response.json()["message"]
        mock_service.create_recorder.assert_called_once()
