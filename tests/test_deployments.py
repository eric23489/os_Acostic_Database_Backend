from unittest.mock import patch
from app.schemas.deployment import DeploymentResponse
from app.core.config import settings


def test_get_deployments(client):
    with patch("app.api.v1.endpoints.api_deployments.DeploymentService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_deployments.return_value = []

        response = client.get(f"{settings.api_prefix}/deployments/?point_id=1")
        assert response.status_code == 200
        assert response.json() == []
        mock_service.get_deployments.assert_called_once()


def test_get_deployment(client):
    with patch("app.api.v1.endpoints.api_deployments.DeploymentService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_deployment.return_value = DeploymentResponse(
            id=1, point_id=1, recorder_id=1, phase=1
        )

        response = client.get(f"{settings.api_prefix}/deployments/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        mock_service.get_deployment.assert_called_once_with(1)


def test_create_deployment(client):
    with patch("app.api.v1.endpoints.api_deployments.DeploymentService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_deployment.return_value = DeploymentResponse(
            id=1, point_id=1, recorder_id=1, phase=1
        )

        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={"point_id": 1, "recorder_id": 1},
        )
        assert response.status_code == 200
        assert response.json()["phase"] == 1
        mock_service.create_deployment.assert_called_once()
        assert mock_service.create_deployment.call_args[0][0].point_id == 1


def test_update_deployment(client):
    with patch("app.api.v1.endpoints.api_deployments.DeploymentService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_deployment.return_value = DeploymentResponse(
            id=1, point_id=1, recorder_id=1, phase=1, description="Updated"
        )

        response = client.put(
            f"{settings.api_prefix}/deployments/1", json={"description": "Updated"}
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated"
        mock_service.update_deployment.assert_called_once()
        assert mock_service.update_deployment.call_args[0][0] == 1
        assert mock_service.update_deployment.call_args[0][1].description == "Updated"
