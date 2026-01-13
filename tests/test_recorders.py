from unittest.mock import patch
from app.schemas.recorder import RecorderResponse


def test_get_recorders(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorders.return_value = []

        response = client.get("/recorders/")
        assert response.status_code == 200
        assert response.json() == []


def test_get_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123"
        )

        response = client.get("/recorders/1")
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123"


def test_create_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123"
        )

        response = client.post(
            "/recorders/", json={"brand": "Brand", "model": "Model", "sn": "SN123"}
        )
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123"


def test_update_recorder(client):
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_recorder.return_value = RecorderResponse(
            id=1, brand="Brand", model="Model", sn="SN123_UPDATED"
        )

        response = client.put("/recorders/1", json={"sn": "SN123_UPDATED"})
        assert response.status_code == 200
        assert response.json()["sn"] == "SN123_UPDATED"
