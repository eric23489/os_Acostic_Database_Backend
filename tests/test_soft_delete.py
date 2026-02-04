"""
軟刪除功能測試模組。

本模組測試系統中的軟刪除（Soft Delete）功能，包含：
- 單一實體軟刪除
- 級聯軟刪除（Cascade Soft Delete）
- 還原功能（Restore）
- 唯一性約束檢查

所有測試使用 mock，不連接真實資料庫。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import settings


# =============================================================================
# Project 軟刪除測試
# =============================================================================


class TestProjectSoftDelete:
    """測試 Project 軟刪除相關功能。"""

    def test_delete_project_success(self, client):
        """
        測試成功刪除專案。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 delete_project 方法被呼叫
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬已刪除的專案回傳（使用 MagicMock 模擬 ORM 物件）
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"
            mock_project.name_zh = None
            mock_project.area = None
            mock_project.description = None
            mock_project.start_time = None
            mock_project.end_time = None
            mock_project.is_finished = False
            mock_project.owner = None
            mock_project.contractor = None
            mock_project.contact_name = None
            mock_project.contact_phone = None
            mock_project.contact_email = None
            mock_project.created_at = datetime.now(timezone.utc)
            mock_project.updated_at = datetime.now(timezone.utc)
            mock_project.is_deleted = True
            mock_project.deleted_at = datetime.now(timezone.utc)
            mock_project.deleted_by = 1
            mock_service.delete_project.return_value = mock_project

            response = client.delete(f"{settings.api_prefix}/projects/1")

            assert response.status_code == 200
            mock_service.delete_project.assert_called_once()

    def test_delete_project_not_found(self, client):
        """
        測試刪除不存在的專案。

        預期行為：
        - API 回傳 404 狀態碼
        - 錯誤訊息顯示找不到專案
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.delete_project.side_effect = HTTPException(
                status_code=404, detail="Project not found"
            )

            response = client.delete(f"{settings.api_prefix}/projects/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_restore_project_success(self, client, mock_db):
        """
        測試成功還原專案。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 restore_project 方法被呼叫
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬還原後的專案
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"
            mock_project.name_zh = None
            mock_project.area = None
            mock_project.description = None
            mock_project.start_time = None
            mock_project.end_time = None
            mock_project.is_finished = False
            mock_project.owner = None
            mock_project.contractor = None
            mock_project.contact_name = None
            mock_project.contact_phone = None
            mock_project.contact_email = None
            mock_project.created_at = datetime.now(timezone.utc)
            mock_project.updated_at = datetime.now(timezone.utc)
            mock_project.is_deleted = False
            mock_project.deleted_at = None
            mock_project.deleted_by = 1  # 模擬原刪除者為當前使用者

            # 模擬 db.query 找到專案
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_project
            )
            mock_service.restore_project.return_value = mock_project

            response = client.post(f"{settings.api_prefix}/projects/1/restore")

            assert response.status_code == 200
            mock_service.restore_project.assert_called_once_with(1)

    def test_restore_project_name_collision(self, client, mock_db):
        """
        測試還原專案時發生名稱衝突。

        預期行為：
        - API 回傳 400 狀態碼
        - 錯誤訊息顯示名稱已存在
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬找到專案
            mock_project = MagicMock()
            mock_project.deleted_by = 1  # 當前使用者
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_project
            )
            mock_service.restore_project.side_effect = HTTPException(
                status_code=400,
                detail="Active project with this name already exists. Cannot restore.",
            )

            response = client.post(f"{settings.api_prefix}/projects/1/restore")

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


# =============================================================================
# Point 軟刪除測試
# =============================================================================


class TestPointSoftDelete:
    """測試 Point 軟刪除相關功能。"""

    def test_delete_point_success(self, client):
        """
        測試成功刪除測站。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 delete_point 方法被呼叫
        """
        with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
            mock_service = MockService.return_value
            # 模擬已刪除的測站
            mock_point = MagicMock()
            mock_point.id = 1
            mock_point.project_id = 1
            mock_point.name = "test-point"
            mock_point.gps_lat_plan = 23.5
            mock_point.gps_lon_plan = 121.5
            mock_point.depth_plan = None
            mock_point.description = None
            mock_point.created_at = datetime.now(timezone.utc)
            mock_point.updated_at = datetime.now(timezone.utc)
            mock_point.is_deleted = True
            mock_point.deleted_at = datetime.now(timezone.utc)
            mock_point.deleted_by = 1
            mock_service.delete_point.return_value = mock_point

            response = client.delete(f"{settings.api_prefix}/points/1")

            assert response.status_code == 200
            mock_service.delete_point.assert_called_once()

    def test_delete_point_not_found(self, client):
        """
        測試刪除不存在的測站。

        預期行為：
        - API 回傳 404 狀態碼
        """
        with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
            mock_service = MockService.return_value
            mock_service.delete_point.side_effect = HTTPException(
                status_code=404, detail="Point not found"
            )

            response = client.delete(f"{settings.api_prefix}/points/999")

            assert response.status_code == 404

    def test_restore_point_success(self, client, mock_db):
        """
        測試成功還原測站。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 restore_point 方法被呼叫
        """
        with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
            mock_service = MockService.return_value
            # 模擬還原後的測站
            mock_point = MagicMock()
            mock_point.id = 1
            mock_point.project_id = 1
            mock_point.name = "test-point"
            mock_point.gps_lat_plan = 23.5
            mock_point.gps_lon_plan = 121.5
            mock_point.depth_plan = None
            mock_point.description = None
            mock_point.created_at = datetime.now(timezone.utc)
            mock_point.updated_at = datetime.now(timezone.utc)
            mock_point.is_deleted = False
            mock_point.deleted_at = None
            mock_point.deleted_by = 1  # 模擬原刪除者為當前使用者

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_point
            )
            mock_service.restore_point.return_value = mock_point

            response = client.post(f"{settings.api_prefix}/points/1/restore")

            assert response.status_code == 200
            mock_service.restore_point.assert_called_once_with(1)

    def test_restore_point_name_collision(self, client, mock_db):
        """
        測試還原測站時發生名稱衝突。

        預期行為：
        - API 回傳 400 狀態碼
        """
        with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
            mock_service = MockService.return_value
            mock_point = MagicMock()
            mock_point.deleted_by = 1
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_point
            )
            mock_service.restore_point.side_effect = HTTPException(
                status_code=400,
                detail="Active point with this name already exists in the project. Cannot restore.",
            )

            response = client.post(f"{settings.api_prefix}/points/1/restore")

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


# =============================================================================
# Deployment 軟刪除測試
# =============================================================================


class TestDeploymentSoftDelete:
    """測試 Deployment 軟刪除相關功能。"""

    def test_delete_deployment_success(self, client):
        """
        測試成功刪除佈放紀錄。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 delete_deployment 方法被呼叫
        """
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬已刪除的佈放紀錄
            mock_deployment = MagicMock()
            mock_deployment.id = 1
            mock_deployment.point_id = 1
            mock_deployment.recorder_id = 1
            mock_deployment.phase = 1
            mock_deployment.start_time = None
            mock_deployment.end_time = None
            mock_deployment.deploy_time = None
            mock_deployment.return_time = None
            mock_deployment.gps_lat_exe = None
            mock_deployment.gps_lon_exe = None
            mock_deployment.depth_exe = None
            mock_deployment.fs = None
            mock_deployment.sensitivity = None
            mock_deployment.gain = None
            mock_deployment.status = "test"
            mock_deployment.description = None
            mock_deployment.created_at = datetime.now(timezone.utc)
            mock_deployment.updated_at = datetime.now(timezone.utc)
            mock_deployment.is_deleted = True
            mock_deployment.deleted_at = datetime.now(timezone.utc)
            mock_deployment.deleted_by = 1
            mock_service.delete_deployment.return_value = mock_deployment

            response = client.delete(f"{settings.api_prefix}/deployments/1")

            assert response.status_code == 200
            mock_service.delete_deployment.assert_called_once()

    def test_delete_deployment_not_found(self, client):
        """
        測試刪除不存在的佈放紀錄。

        預期行為：
        - API 回傳 404 狀態碼
        """
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.delete_deployment.side_effect = HTTPException(
                status_code=404, detail="Deployment not found"
            )

            response = client.delete(f"{settings.api_prefix}/deployments/999")

            assert response.status_code == 404

    def test_restore_deployment_success(self, client, mock_db):
        """
        測試成功還原佈放紀錄。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 restore_deployment 方法被呼叫
        """
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬還原後的佈放紀錄
            mock_deployment = MagicMock()
            mock_deployment.id = 1
            mock_deployment.point_id = 1
            mock_deployment.recorder_id = 1
            mock_deployment.phase = 1
            mock_deployment.start_time = None
            mock_deployment.end_time = None
            mock_deployment.deploy_time = None
            mock_deployment.return_time = None
            mock_deployment.gps_lat_exe = None
            mock_deployment.gps_lon_exe = None
            mock_deployment.depth_exe = None
            mock_deployment.fs = None
            mock_deployment.sensitivity = None
            mock_deployment.gain = None
            mock_deployment.status = "test"
            mock_deployment.description = None
            mock_deployment.created_at = datetime.now(timezone.utc)
            mock_deployment.updated_at = datetime.now(timezone.utc)
            mock_deployment.is_deleted = False
            mock_deployment.deleted_at = None
            mock_deployment.deleted_by = 1  # 模擬原刪除者為當前使用者

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_deployment
            )
            mock_service.restore_deployment.return_value = mock_deployment

            response = client.post(f"{settings.api_prefix}/deployments/1/restore")

            assert response.status_code == 200
            mock_service.restore_deployment.assert_called_once_with(1)

    def test_restore_deployment_phase_collision(self, client, mock_db):
        """
        測試還原佈放紀錄時發生階段衝突。

        預期行為：
        - API 回傳 400 狀態碼
        """
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_deployment = MagicMock()
            mock_deployment.deleted_by = 1
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_deployment
            )
            mock_service.restore_deployment.side_effect = HTTPException(
                status_code=400,
                detail="Active deployment with this phase already exists for the point. Cannot restore.",
            )

            response = client.post(f"{settings.api_prefix}/deployments/1/restore")

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


# =============================================================================
# Audio 軟刪除測試
# =============================================================================


class TestAudioSoftDelete:
    """測試 Audio 軟刪除相關功能。"""

    def test_delete_audio_success(self, client):
        """
        測試成功刪除音檔紀錄。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 delete_audio 方法被呼叫
        """
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            mock_service = MockService.return_value
            # 模擬已刪除的音檔
            mock_audio = MagicMock()
            mock_audio.id = 1
            mock_audio.deployment_id = 1
            mock_audio.file_name = "test.wav"
            mock_audio.object_key = "test/path/test.wav"
            mock_audio.file_format = "wav"
            mock_audio.file_size = 1024
            mock_audio.checksum = None
            mock_audio.record_time = None
            mock_audio.record_duration = None
            mock_audio.fs = None
            mock_audio.recorder_channel = 0
            mock_audio.audio_channels = 1
            mock_audio.target = None
            mock_audio.target_type = None
            mock_audio.meta_json = None
            mock_audio.is_cold_storage = False
            mock_audio.updated_at = datetime.now(timezone.utc)
            mock_audio.is_deleted = True
            mock_audio.deleted_at = datetime.now(timezone.utc)
            mock_audio.deleted_by = 1
            mock_service.delete_audio.return_value = mock_audio

            response = client.delete(f"{settings.api_prefix}/audio/1")

            assert response.status_code == 200
            mock_service.delete_audio.assert_called_once()

    def test_delete_audio_not_found(self, client):
        """
        測試刪除不存在的音檔紀錄。

        預期行為：
        - API 回傳 404 狀態碼
        """
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            mock_service = MockService.return_value
            mock_service.delete_audio.side_effect = HTTPException(
                status_code=404, detail="Audio not found"
            )

            response = client.delete(f"{settings.api_prefix}/audio/999")

            assert response.status_code == 404

    def test_restore_audio_success(self, client, mock_db):
        """
        測試成功還原音檔紀錄。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 restore_audio 方法被呼叫
        """
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            mock_service = MockService.return_value
            # 模擬還原後的音檔
            mock_audio = MagicMock()
            mock_audio.id = 1
            mock_audio.deployment_id = 1
            mock_audio.file_name = "test.wav"
            mock_audio.object_key = "test/path/test.wav"
            mock_audio.file_format = "wav"
            mock_audio.file_size = 1024
            mock_audio.checksum = None
            mock_audio.record_time = None
            mock_audio.record_duration = None
            mock_audio.fs = None
            mock_audio.recorder_channel = 0
            mock_audio.audio_channels = 1
            mock_audio.target = None
            mock_audio.target_type = None
            mock_audio.meta_json = None
            mock_audio.is_cold_storage = False
            mock_audio.updated_at = datetime.now(timezone.utc)
            mock_audio.is_deleted = False
            mock_audio.deleted_at = None
            mock_audio.deleted_by = 1  # 模擬原刪除者為當前使用者

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_audio
            )
            mock_service.restore_audio.return_value = mock_audio

            response = client.post(f"{settings.api_prefix}/audio/1/restore")

            assert response.status_code == 200
            mock_service.restore_audio.assert_called_once_with(1)

    def test_restore_audio_object_key_collision(self, client, mock_db):
        """
        測試還原音檔時發生 object_key 衝突。

        預期行為：
        - API 回傳 400 狀態碼
        """
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            mock_service = MockService.return_value
            mock_audio = MagicMock()
            mock_audio.deleted_by = 1
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_audio
            )
            mock_service.restore_audio.side_effect = HTTPException(
                status_code=400,
                detail="Active audio with this object_key already exists. Cannot restore.",
            )

            response = client.post(f"{settings.api_prefix}/audio/1/restore")

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


# =============================================================================
# Recorder 軟刪除測試
# =============================================================================


class TestRecorderSoftDelete:
    """測試 Recorder 軟刪除相關功能。"""

    def test_delete_recorder_success(self, client):
        """
        測試成功刪除錄音機。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 delete_recorder 方法被呼叫
        """
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬已刪除的錄音機
            mock_recorder = MagicMock()
            mock_recorder.id = 1
            mock_recorder.brand = "Brand"
            mock_recorder.model = "Model"
            mock_recorder.sn = "SN123"
            mock_recorder.sensitivity = -160.0
            mock_recorder.high_gain = None
            mock_recorder.low_gain = None
            mock_recorder.status = "in_service"
            mock_recorder.owner = "Ocean Sound"
            mock_recorder.recorder_channels = 1
            mock_recorder.description = None
            mock_recorder.created_at = datetime.now(timezone.utc)
            mock_recorder.updated_at = datetime.now(timezone.utc)
            mock_recorder.is_deleted = True
            mock_recorder.deleted_at = datetime.now(timezone.utc)
            mock_recorder.deleted_by = 1
            mock_service.delete_recorder.return_value = mock_recorder

            response = client.delete(f"{settings.api_prefix}/recorders/1")

            assert response.status_code == 200
            mock_service.delete_recorder.assert_called_once()

    def test_delete_recorder_not_found(self, client):
        """
        測試刪除不存在的錄音機。

        預期行為：
        - API 回傳 404 狀態碼
        """
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.delete_recorder.side_effect = HTTPException(
                status_code=404, detail="Recorder with ID 999 not found."
            )

            response = client.delete(f"{settings.api_prefix}/recorders/999")

            assert response.status_code == 404

    def test_restore_recorder_success(self, client, mock_db):
        """
        測試成功還原錄音機。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 restore_recorder 方法被呼叫
        """
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬還原後的錄音機
            mock_recorder = MagicMock()
            mock_recorder.id = 1
            mock_recorder.brand = "Brand"
            mock_recorder.model = "Model"
            mock_recorder.sn = "SN123"
            mock_recorder.sensitivity = -160.0
            mock_recorder.high_gain = None
            mock_recorder.low_gain = None
            mock_recorder.status = "in_service"
            mock_recorder.owner = "Ocean Sound"
            mock_recorder.recorder_channels = 1
            mock_recorder.description = None
            mock_recorder.created_at = datetime.now(timezone.utc)
            mock_recorder.updated_at = datetime.now(timezone.utc)
            mock_recorder.is_deleted = False
            mock_recorder.deleted_at = None
            mock_recorder.deleted_by = 1  # 模擬原刪除者為當前使用者

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_recorder
            )
            mock_service.restore_recorder.return_value = mock_recorder

            response = client.post(f"{settings.api_prefix}/recorders/1/restore")

            assert response.status_code == 200
            mock_service.restore_recorder.assert_called_once_with(1)

    def test_restore_recorder_unique_collision(self, client, mock_db):
        """
        測試還原錄音機時發生唯一性衝突（brand/model/sn 組合）。

        預期行為：
        - API 回傳 400 狀態碼
        """
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_recorder = MagicMock()
            mock_recorder.deleted_by = 1
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_recorder
            )
            mock_service.restore_recorder.side_effect = HTTPException(
                status_code=400,
                detail="Active recorder with this brand/model/sn already exists. Cannot restore.",
            )

            response = client.post(f"{settings.api_prefix}/recorders/1/restore")

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()


# =============================================================================
# 已刪除資料查詢過濾測試
# =============================================================================


class TestSoftDeleteFiltering:
    """測試軟刪除資料的過濾功能。"""

    def test_get_projects_excludes_deleted(self, client):
        """
        測試查詢專案列表時排除已刪除的專案。

        預期行為：
        - Service 的 get_projects 方法被呼叫
        - 只回傳活躍的專案
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            # 模擬只回傳活躍的專案
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "active-project"
            mock_project.name_zh = None
            mock_project.area = None
            mock_project.description = None
            mock_project.start_time = None
            mock_project.end_time = None
            mock_project.is_finished = False
            mock_project.owner = None
            mock_project.contractor = None
            mock_project.contact_name = None
            mock_project.contact_phone = None
            mock_project.contact_email = None
            mock_project.created_at = datetime.now(timezone.utc)
            mock_project.updated_at = datetime.now(timezone.utc)
            mock_service.get_projects.return_value = [mock_project]

            response = client.get(f"{settings.api_prefix}/projects/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            mock_service.get_projects.assert_called_once()

    def test_get_points_excludes_deleted(self, client):
        """
        測試查詢測站列表時排除已刪除的測站。

        預期行為：
        - Service 的 get_points 方法被呼叫
        - 只回傳活躍的測站
        """
        with patch("app.api.v1.endpoints.api_points.PointService") as MockService:
            mock_service = MockService.return_value
            mock_point = MagicMock()
            mock_point.id = 1
            mock_point.project_id = 1
            mock_point.name = "active-point"
            mock_point.gps_lat_plan = 23.5
            mock_point.gps_lon_plan = 121.5
            mock_point.depth_plan = None
            mock_point.description = None
            mock_point.created_at = datetime.now(timezone.utc)
            mock_point.updated_at = datetime.now(timezone.utc)
            mock_service.get_points.return_value = [mock_point]

            response = client.get(f"{settings.api_prefix}/points/?project_id=1")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            mock_service.get_points.assert_called_once()

    def test_get_deployments_excludes_deleted(self, client):
        """
        測試查詢佈放紀錄列表時排除已刪除的紀錄。

        預期行為：
        - Service 的 get_deployments 方法被呼叫
        - 只回傳活躍的佈放紀錄
        """
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_deployment = MagicMock()
            mock_deployment.id = 1
            mock_deployment.point_id = 1
            mock_deployment.recorder_id = 1
            mock_deployment.phase = 1
            mock_deployment.start_time = None
            mock_deployment.end_time = None
            mock_deployment.deploy_time = None
            mock_deployment.return_time = None
            mock_deployment.gps_lat_exe = None
            mock_deployment.gps_lon_exe = None
            mock_deployment.depth_exe = None
            mock_deployment.fs = None
            mock_deployment.sensitivity = None
            mock_deployment.gain = None
            mock_deployment.status = "test"
            mock_deployment.description = None
            mock_deployment.created_at = datetime.now(timezone.utc)
            mock_deployment.updated_at = datetime.now(timezone.utc)
            mock_service.get_deployments.return_value = [mock_deployment]

            response = client.get(f"{settings.api_prefix}/deployments/?point_id=1")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            mock_service.get_deployments.assert_called_once()

    def test_get_audios_excludes_deleted(self, client):
        """
        測試查詢音檔列表時排除已刪除的音檔。

        預期行為：
        - Service 的 get_audios 方法被呼叫
        - 只回傳活躍的音檔
        """
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            mock_service = MockService.return_value
            mock_audio = MagicMock()
            mock_audio.id = 1
            mock_audio.deployment_id = 1
            mock_audio.file_name = "test.wav"
            mock_audio.object_key = "test/path/test.wav"
            mock_audio.file_format = "wav"
            mock_audio.file_size = 1024
            mock_audio.checksum = None
            mock_audio.record_time = None
            mock_audio.record_duration = None
            mock_audio.fs = None
            mock_audio.recorder_channel = 0
            mock_audio.audio_channels = 1
            mock_audio.target = None
            mock_audio.target_type = None
            mock_audio.meta_json = None
            mock_audio.is_cold_storage = False
            mock_audio.updated_at = datetime.now(timezone.utc)
            mock_service.get_audios.return_value = [mock_audio]

            response = client.get(f"{settings.api_prefix}/audio/?deployment_id=1")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            mock_service.get_audios.assert_called_once()

    def test_get_recorders_excludes_deleted(self, client):
        """
        測試查詢錄音機列表時排除已刪除的錄音機。

        預期行為：
        - Service 的 get_recorders 方法被呼叫
        - 只回傳活躍的錄音機
        """
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_recorder = MagicMock()
            mock_recorder.id = 1
            mock_recorder.brand = "Brand"
            mock_recorder.model = "Model"
            mock_recorder.sn = "SN123"
            mock_recorder.sensitivity = -160.0
            mock_recorder.high_gain = None
            mock_recorder.low_gain = None
            mock_recorder.status = "in_service"
            mock_recorder.owner = "Ocean Sound"
            mock_recorder.recorder_channels = 1
            mock_recorder.description = None
            mock_recorder.created_at = datetime.now(timezone.utc)
            mock_recorder.updated_at = datetime.now(timezone.utc)
            mock_service.get_recorders.return_value = [mock_recorder]

            response = client.get(f"{settings.api_prefix}/recorders/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            mock_service.get_recorders.assert_called_once()
