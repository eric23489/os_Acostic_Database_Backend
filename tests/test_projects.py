from unittest.mock import patch
from app.schemas.project import ProjectResponse
from app.core.config import settings


def test_get_projects(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_projects.return_value = [
            ProjectResponse(id=1, name="Project A", area="Area A")
        ]

        response = client.get(f"{settings.api_prefix}/projects/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Project A"
        mock_service.get_projects.assert_called_once()


def test_get_project(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_project.return_value = ProjectResponse(
            id=1, name="Project A", area="Area A"
        )

        response = client.get(f"{settings.api_prefix}/projects/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        mock_service.get_project.assert_called_once_with(1)


def test_create_project(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_project.return_value = ProjectResponse(
            id=1, name="New Project", area="New Area"
        )

        response = client.post(
            f"{settings.api_prefix}/projects/",
            json={"name": "New Project", "area": "New Area"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Project"
        mock_service.create_project.assert_called_once()
        assert mock_service.create_project.call_args[0][0].name == "New Project"


def test_update_project(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_project.return_value = ProjectResponse(
            id=1, name="Updated Project", area="Area A"
        )

        response = client.put(
            f"{settings.api_prefix}/projects/1", json={"name": "Updated Project"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Project"
        mock_service.update_project.assert_called_once()
        assert mock_service.update_project.call_args[0][0] == 1
        assert mock_service.update_project.call_args[0][1].name == "Updated Project"
