from unittest.mock import patch
from app.schemas.point import PointResponse
from app.core.config import settings


def test_get_points(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_points.return_value = []

        response = client.get(f"{settings.api_prefix}/points/?project_id=1")
        assert response.status_code == 200
        assert response.json() == []
        mock_service.get_points.assert_called_once()


def test_get_point(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_point.return_value = PointResponse(
            id=1, project_id=1, name="Point A", gps_lat_plan=23.5, gps_lon_plan=121.5
        )

        response = client.get(f"{settings.api_prefix}/points/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["project_id"] == 1
        assert response.json()["name"] == "Point A"
        mock_service.get_point.assert_called_once_with(1)


def test_create_point(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_point.return_value = PointResponse(
            id=1,
            project_id=1,
            name="New Point",
            gps_lat_plan=23.5,
            gps_lon_plan=121.5,
        )

        response = client.post(
            f"{settings.api_prefix}/points/",
            json={
                "project_id": 1,
                "name": "New Point",
                "gps_lat_plan": 23.5,
                "gps_lon_plan": 121.5,
            },
        )
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert response.json()["project_id"] == 1
        assert response.json()["name"] == "New Point"
        mock_service.create_point.assert_called_once()
        assert mock_service.create_point.call_args[0][0].name == "New Point"


def test_update_point(client):
    with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_point.return_value = PointResponse(
            id=1, project_id=1, name="Updated Point"
        )

        response = client.put(
            f"{settings.api_prefix}/points/1", json={"name": "Updated Point"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Point"
        mock_service.update_point.assert_called_once()
        assert mock_service.update_point.call_args[0][0] == 1
        assert mock_service.update_point.call_args[0][1].name == "Updated Point"
