from unittest.mock import patch
from app.schemas.point import PointResponse


def test_get_points(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_points.return_value = []

        response = client.get("/points/?project_id=1")
        assert response.status_code == 200
        assert response.json() == []


def test_get_point(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_point.return_value = PointResponse(
            id=1, project_id=1, name="Point A"
        )

        response = client.get("/points/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Point A"


def test_create_point(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_point.return_value = PointResponse(
            id=1, project_id=1, name="New Point"
        )

        response = client.post(
            "/points/",
            json={
                "project_id": 1,
                "name": "New Point",
                "gps_lat_plan": 23.5,
                "gps_lon_plan": 121.5,
            },
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Point"


def test_update_point(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_point.return_value = PointResponse(
            id=1, project_id=1, name="Updated Point"
        )

        response = client.put("/points/1", json={"name": "Updated Point"})
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Point"
