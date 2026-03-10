from unittest.mock import patch

from app.core.config import settings
from app.core.exceptions import (
    RECORDER_HAS_DEPLOYMENTS,
    RECORDER_IDENTIFIER_DUPLICATE,
    RECORDER_IDENTIFIER_RESERVED,
)
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
            f"{settings.api_prefix}/recorders/?search=SN123&recorder_status=available"
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
        mock_service.create_recorder.side_effect = RECORDER_IDENTIFIER_DUPLICATE

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


def test_hard_delete_recorder_blocked_by_soft_deleted_deployment(client):
    """Issue B：soft-deleted deployment 引用的 recorder 執行 hard delete 應回 400 RECORDER_HAS_DEPLOYMENTS。"""
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.hard_delete_recorder.side_effect = RECORDER_HAS_DEPLOYMENTS

        response = client.delete(f"{settings.api_prefix}/recorders/1/permanent")
        assert response.status_code == 400
        assert response.json()["error_code"] == "RECORDER_HAS_DEPLOYMENTS"
        mock_service.hard_delete_recorder.assert_called_once_with(1)


def test_update_recorder_with_reserved_identifier(client):
    """Issue E：PUT 將 brand/model/sn 改為已軟刪除 recorder 保留的識別碼，應回 400 RECORDER_IDENTIFIER_RESERVED。"""
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        mock_service = MockService.return_value
        mock_service.update_recorder.side_effect = RECORDER_IDENTIFIER_RESERVED

        response = client.put(
            f"{settings.api_prefix}/recorders/1",
            json={"brand": "NewBrand", "model": "NewModel", "sn": "RESERVED_SN"},
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "RECORDER_IDENTIFIER_RESERVED"
        mock_service.update_recorder.assert_called_once()


def test_get_recorder_stats(client):
    """GET /recorders/stats 回傳 available 與 deploying 數量。"""
    with patch("app.api.v1.endpoints.api_recorders.RecorderService") as MockService:
        from app.schemas.recorder import RecorderStatsResponse

        mock_service = MockService.return_value
        mock_service.get_recorder_stats.return_value = RecorderStatsResponse(
            available_count=5, deploying_count=2
        )

        response = client.get(f"{settings.api_prefix}/recorders/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["available_count"] == 5
        assert data["deploying_count"] == 2
        mock_service.get_recorder_stats.assert_called_once()
