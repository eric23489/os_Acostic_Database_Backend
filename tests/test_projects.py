from unittest.mock import patch

from app.core.config import settings
from app.schemas.project import ProjectResponse


def test_get_projects(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_projects.return_value = (
            [ProjectResponse(id=1, name="project-a", area="Area A", project_type=None)],
            1,
        )

        response = client.get(f"{settings.api_prefix}/projects/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "project-a"
        mock_service.get_projects.assert_called_once()


def test_get_projects_with_search(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_projects.return_value = ([], 0)

        response = client.get(
            f"{settings.api_prefix}/projects/?search=test&is_finished=true&sort_by=name&order=asc"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        mock_service.get_projects.assert_called_once()


def test_get_project(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_project.return_value = ProjectResponse(
            id=1, name="project-a", area="Area A", project_type=None
        )

        response = client.get(f"{settings.api_prefix}/projects/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        mock_service.get_project.assert_called_once_with(1)


def test_create_project(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.create_project.return_value = ProjectResponse(
            id=1, name="new-project", area="New Area", project_type=None
        )

        response = client.post(
            f"{settings.api_prefix}/projects/",
            json={"name": "new-project", "area": "New Area"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "new-project"
        mock_service.create_project.assert_called_once()
        assert mock_service.create_project.call_args[0][0].name == "new-project"


def test_update_project(client):
    with patch("app.api.v1.endpoints.api_projects.ProjectService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_project.return_value = ProjectResponse(
            id=1, name="updated-project", area="Area A", project_type=None
        )

        response = client.put(
            f"{settings.api_prefix}/projects/1", json={"name": "updated-project"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "updated-project"
        mock_service.update_project.assert_called_once()
        assert mock_service.update_project.call_args[0][0] == 1
        assert mock_service.update_project.call_args[0][1].name == "updated-project"
