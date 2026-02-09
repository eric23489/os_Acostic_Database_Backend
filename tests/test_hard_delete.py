"""
Hard Delete 功能測試模組。

本模組測試系統中的永久刪除（Hard Delete）功能，包含：
- Admin 權限檢查
- 單一資源永久刪除
- 級聯永久刪除（Project 層級）
- MinIO 物件刪除
- 名稱釋放後可重用

所有測試使用 mock，不連接真實資料庫或 MinIO。
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.enums.enums import UserRole


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_normal_user():
    """Mock 一般使用者（非 Admin）。"""
    user = MagicMock()
    user.id = 2
    user.email = "user@example.com"
    user.role = UserRole.USER.value
    user.full_name = "Normal User"
    user.is_active = True
    return user


# =============================================================================
# Project Hard Delete 測試
# =============================================================================


class TestProjectHardDelete:
    """測試 Project 永久刪除功能。"""

    def test_hard_delete_requires_admin(self, client, mock_normal_user):
        """
        測試一般使用者無法執行永久刪除。

        預期行為：
        - API 回傳 403 狀態碼
        - 錯誤訊息顯示需要 Admin 權限
        """
        from app.core.auth import get_current_user
        from app.main import app

        # 覆蓋為一般使用者
        app.dependency_overrides[get_current_user] = lambda: mock_normal_user

        response = client.delete(f"{settings.api_prefix}/projects/1/permanent")

        assert response.status_code == 403
        assert "Admin" in response.json()["detail"]

    def test_hard_delete_project_success(self, client):
        """
        測試成功永久刪除專案。

        預期行為：
        - API 回傳 200 狀態碼
        - Service 的 hard_delete_project 方法被呼叫
        - 回傳成功訊息
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_project.return_value = {
                "message": "Project 'test-project' permanently deleted",
                "deleted_audios": 10,
            }

            response = client.delete(f"{settings.api_prefix}/projects/1/permanent")

            assert response.status_code == 200
            assert "permanently deleted" in response.json()["message"]
            mock_service.hard_delete_project.assert_called_once_with(1)

    def test_hard_delete_project_not_found(self, client):
        """
        測試永久刪除不存在的專案。

        預期行為：
        - API 回傳 404 狀態碼
        """
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_project.side_effect = HTTPException(
                status_code=404, detail="Project not found"
            )

            response = client.delete(f"{settings.api_prefix}/projects/1/permanent")

            assert response.status_code == 404


# =============================================================================
# Point Hard Delete 測試
# =============================================================================


class TestPointHardDelete:
    """測試 Point 永久刪除功能。"""

    def test_hard_delete_requires_admin(self, client, mock_normal_user):
        """測試一般使用者無法執行永久刪除。"""
        from app.core.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: mock_normal_user

        response = client.delete(f"{settings.api_prefix}/points/1/permanent")

        assert response.status_code == 403

    def test_hard_delete_point_success(self, client):
        """測試成功永久刪除測站。"""
        with patch(
            "app.api.v1.endpoints.api_points.PointService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_point.return_value = {
                "message": "Point 'test-point' permanently deleted",
                "deleted_audios": 5,
            }

            response = client.delete(f"{settings.api_prefix}/points/1/permanent")

            assert response.status_code == 200
            mock_service.hard_delete_point.assert_called_once_with(1)


# =============================================================================
# Deployment Hard Delete 測試
# =============================================================================


class TestDeploymentHardDelete:
    """測試 Deployment 永久刪除功能。"""

    def test_hard_delete_requires_admin(self, client, mock_normal_user):
        """測試一般使用者無法執行永久刪除。"""
        from app.core.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: mock_normal_user

        response = client.delete(f"{settings.api_prefix}/deployments/1/permanent")

        assert response.status_code == 403

    def test_hard_delete_deployment_success(self, client):
        """測試成功永久刪除部署。"""
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_deployment.return_value = {
                "message": "Deployment permanently deleted",
                "deleted_audios": 3,
            }

            response = client.delete(f"{settings.api_prefix}/deployments/1/permanent")

            assert response.status_code == 200
            mock_service.hard_delete_deployment.assert_called_once_with(1)


# =============================================================================
# Audio Hard Delete 測試
# =============================================================================


class TestAudioHardDelete:
    """測試 Audio 永久刪除功能。"""

    def test_hard_delete_requires_admin(self, client, mock_normal_user):
        """測試一般使用者無法執行永久刪除。"""
        from app.core.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: mock_normal_user

        response = client.delete(f"{settings.api_prefix}/audio/1/permanent")

        assert response.status_code == 403

    def test_hard_delete_audio_success(self, client):
        """測試成功永久刪除音檔。"""
        with patch(
            "app.api.v1.endpoints.api_audio.AudioService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_audio.return_value = {
                "message": "Audio permanently deleted"
            }

            response = client.delete(f"{settings.api_prefix}/audio/1/permanent")

            assert response.status_code == 200
            mock_service.hard_delete_audio.assert_called_once_with(1)


# =============================================================================
# Recorder Hard Delete 測試
# =============================================================================


class TestRecorderHardDelete:
    """測試 Recorder 永久刪除功能。"""

    def test_hard_delete_requires_admin(self, client, mock_normal_user):
        """測試一般使用者無法執行永久刪除。"""
        from app.core.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: mock_normal_user

        response = client.delete(f"{settings.api_prefix}/recorders/1/permanent")

        assert response.status_code == 403
        assert "Admin" in response.json()["detail"]

    def test_hard_delete_recorder_success(self, client):
        """測試成功永久刪除 Recorder。"""
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_recorder.return_value = {
                "message": "Recorder 'SoundTrap/ST600/SN12345' permanently deleted"
            }

            response = client.delete(f"{settings.api_prefix}/recorders/1/permanent")

            assert response.status_code == 200
            assert "permanently deleted" in response.json()["message"]
            mock_service.hard_delete_recorder.assert_called_once_with(1)

    def test_hard_delete_recorder_not_found(self, client):
        """測試刪除不存在的 Recorder。"""
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_recorder.side_effect = HTTPException(
                status_code=404, detail="Recorder not found"
            )

            response = client.delete(f"{settings.api_prefix}/recorders/1/permanent")

            assert response.status_code == 404

    def test_hard_delete_recorder_with_deployments_fails(self, client):
        """測試刪除有 Deployment 引用的 Recorder 會失敗。"""
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_recorder.side_effect = HTTPException(
                status_code=400,
                detail="Cannot delete recorder: 3 deployment(s) reference this recorder. Delete deployments first.",
            )

            response = client.delete(f"{settings.api_prefix}/recorders/1/permanent")

            assert response.status_code == 400
            assert "deployment" in response.json()["detail"].lower()


# =============================================================================
# Service 層 Hard Delete 測試
# =============================================================================


class TestProjectServiceHardDelete:
    """測試 ProjectService 的 hard_delete_project 方法。"""

    def test_hard_delete_removes_minio_objects(self):
        """
        測試永久刪除會刪除 MinIO 物件。

        預期行為：
        - S3 client 的 delete_objects 被呼叫
        - S3 client 的 delete_bucket 被呼叫
        """
        with patch("app.services.project_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            mock_db = MagicMock()

            # Mock Project
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"

            # Mock Audios
            mock_audio1 = MagicMock()
            mock_audio1.object_key = "point1/2024/01/audio1.wav"
            mock_audio2 = MagicMock()
            mock_audio2.object_key = "point1/2024/01/audio2.wav"

            # Setup query chain
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_project
            )
            mock_db.query.return_value.filter.return_value.all.return_value = [
                mock_audio1,
                mock_audio2,
            ]
            mock_db.query.return_value.filter.return_value.delete.return_value = 2

            from app.services.project_service import ProjectService

            service = ProjectService(mock_db)
            result = service.hard_delete_project(1)

            # 驗證 MinIO 操作
            mock_s3.delete_objects.assert_called_once()
            mock_s3.delete_bucket.assert_called_once_with(Bucket="test-project")

    def test_hard_delete_project_not_found_raises_404(self):
        """測試刪除不存在的專案時拋出 404。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.project_service import ProjectService

        service = ProjectService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.hard_delete_project(999)

        assert exc_info.value.status_code == 404


class TestRecorderServiceHardDelete:
    """測試 RecorderService 的 hard_delete_recorder 方法。"""

    def test_hard_delete_recorder_success(self):
        """測試永久刪除沒有 Deployment 引用的 Recorder。"""
        mock_db = MagicMock()

        # Mock Recorder
        mock_recorder = MagicMock()
        mock_recorder.id = 1
        mock_recorder.brand = "SoundTrap"
        mock_recorder.model = "ST600"
        mock_recorder.sn = "SN12345"

        # Setup query chain
        mock_db.query.return_value.filter.return_value.first.return_value = mock_recorder
        mock_db.query.return_value.filter.return_value.count.return_value = 0  # 沒有 Deployment

        from app.services.recorder_service import RecorderService

        service = RecorderService(mock_db)
        result = service.hard_delete_recorder(1)

        assert "permanently deleted" in result["message"]
        assert "SoundTrap/ST600/SN12345" in result["message"]
        mock_db.commit.assert_called_once()

    def test_hard_delete_recorder_with_deployments_raises_400(self):
        """測試刪除有 Deployment 引用的 Recorder 時拋出 400。"""
        mock_db = MagicMock()

        # Mock Recorder
        mock_recorder = MagicMock()
        mock_recorder.id = 1
        mock_recorder.brand = "SoundTrap"
        mock_recorder.model = "ST600"
        mock_recorder.sn = "SN12345"

        # Setup query chain - 有 3 個 Deployment 引用
        mock_db.query.return_value.filter.return_value.first.return_value = mock_recorder
        mock_db.query.return_value.filter.return_value.count.return_value = 3

        from app.services.recorder_service import RecorderService

        service = RecorderService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.hard_delete_recorder(1)

        assert exc_info.value.status_code == 400
        assert "3 deployment(s)" in exc_info.value.detail

    def test_hard_delete_recorder_not_found_raises_404(self):
        """測試刪除不存在的 Recorder 時拋出 404。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.recorder_service import RecorderService

        service = RecorderService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.hard_delete_recorder(999)

        assert exc_info.value.status_code == 404


class TestAudioServiceHardDelete:
    """測試 AudioService 的 hard_delete_audio 方法。"""

    def test_hard_delete_removes_single_minio_object(self):
        """
        測試永久刪除單一音檔會刪除對應 MinIO 物件。

        預期行為：
        - S3 client 的 delete_object 被呼叫一次
        - 正確的 Bucket 和 Key
        """
        with patch("app.services.audio_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            mock_db = MagicMock()

            # Mock Audio
            mock_audio = MagicMock()
            mock_audio.id = 1
            mock_audio.object_key = "point1/2024/01/audio1.wav"
            mock_audio.deployment_id = 1

            # Mock Deployment -> Point -> Project chain
            mock_deployment = MagicMock()
            mock_deployment.point_id = 1
            mock_point = MagicMock()
            mock_point.project_id = 1
            mock_project = MagicMock()
            mock_project.name = "test-project"

            # Setup query chain
            def query_side_effect(model):
                mock_query = MagicMock()
                if "AudioInfo" in str(model):
                    mock_query.filter.return_value.first.return_value = mock_audio
                elif "DeploymentInfo" in str(model):
                    mock_query.filter.return_value.first.return_value = mock_deployment
                elif "PointInfo" in str(model):
                    mock_query.filter.return_value.first.return_value = mock_point
                elif "ProjectInfo" in str(model):
                    mock_query.filter.return_value.first.return_value = mock_project
                return mock_query

            mock_db.query.side_effect = query_side_effect

            from app.services.audio_service import AudioService

            service = AudioService(mock_db)
            result = service.hard_delete_audio(1)

            # 驗證 MinIO 操作
            mock_s3.delete_object.assert_called_once_with(
                Bucket="test-project", Key="point1/2024/01/audio1.wav"
            )


# =============================================================================
# 名稱釋放測試
# =============================================================================


# =============================================================================
# 錯誤處理測試
# =============================================================================


class TestHardDeleteErrorHandling:
    """測試 Hard Delete 的錯誤處理機制。"""

    def test_hard_delete_continues_when_minio_fails(self):
        """
        測試 MinIO 刪除失敗時，DB 刪除仍會執行。

        預期行為：
        - MinIO 失敗只記錄 warning，不中斷流程
        - DB 記錄仍被刪除
        - 回傳成功訊息
        """
        with patch("app.services.project_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            # MinIO 刪除物件時拋出異常
            mock_s3.delete_objects.side_effect = Exception("MinIO connection failed")
            mock_s3.delete_bucket.side_effect = Exception("MinIO connection failed")

            mock_db = MagicMock()

            # Mock Project
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"

            # Mock 空的 Audio 列表
            mock_db.query.return_value.filter.return_value.first.return_value = mock_project
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.delete.return_value = 0

            from app.services.project_service import ProjectService

            service = ProjectService(mock_db)
            result = service.hard_delete_project(1)

            # 驗證 DB commit 仍被呼叫
            mock_db.commit.assert_called_once()
            assert "permanently deleted" in result["message"]

    def test_hard_delete_empty_project(self):
        """
        測試刪除沒有任何 Audio 的空 Project。

        預期行為：
        - 不呼叫 delete_objects (沒有物件)
        - 呼叫 delete_bucket
        - DB 記錄被刪除
        """
        with patch("app.services.project_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            mock_db = MagicMock()

            # Mock Project
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "empty-project"

            # Mock 空的 Audio 列表
            mock_db.query.return_value.filter.return_value.first.return_value = mock_project
            mock_db.query.return_value.filter.return_value.all.return_value = []  # 空
            mock_db.query.return_value.filter.return_value.delete.return_value = 0

            from app.services.project_service import ProjectService

            service = ProjectService(mock_db)
            result = service.hard_delete_project(1)

            # 驗證沒有呼叫 delete_objects (因為沒有物件)
            mock_s3.delete_objects.assert_not_called()
            # 驗證有呼叫 delete_bucket
            mock_s3.delete_bucket.assert_called_once_with(Bucket="empty-project")


class TestHardDeleteBatchProcessing:
    """測試批量刪除處理。"""

    def test_hard_delete_batch_over_1000_objects(self):
        """
        測試刪除超過 1000 個物件時的分批處理。

        預期行為：
        - delete_objects 被呼叫多次
        - 每批最多 1000 個物件
        """
        with patch("app.services.project_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            mock_db = MagicMock()

            # Mock Project
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "large-project"

            # Mock 1500 個 Audio
            mock_audios = []
            for i in range(1500):
                audio = MagicMock()
                audio.object_key = f"point/2024/01/audio_{i}.wav"
                mock_audios.append(audio)

            mock_db.query.return_value.filter.return_value.first.return_value = mock_project
            mock_db.query.return_value.filter.return_value.all.return_value = mock_audios
            mock_db.query.return_value.filter.return_value.delete.return_value = 1500

            from app.services.project_service import ProjectService

            service = ProjectService(mock_db)
            result = service.hard_delete_project(1)

            # 驗證 delete_objects 被呼叫 2 次 (1000 + 500)
            assert mock_s3.delete_objects.call_count == 2

            # 驗證第一批有 1000 個物件
            first_call = mock_s3.delete_objects.call_args_list[0]
            assert len(first_call[1]["Delete"]["Objects"]) == 1000

            # 驗證第二批有 500 個物件
            second_call = mock_s3.delete_objects.call_args_list[1]
            assert len(second_call[1]["Delete"]["Objects"]) == 500


# =============================================================================
# 名稱釋放測試
# =============================================================================


class TestNameRelease:
    """測試 Hard Delete 後名稱可重新使用。"""

    def test_soft_deleted_name_is_reserved(self):
        """
        測試軟刪除的名稱被保留，無法建立同名資源。

        預期行為：
        - 建立同名資源時回傳 400
        - 錯誤訊息提示需要 Hard Delete
        """
        mock_db = MagicMock()

        # 模擬沒有活躍的同名記錄
        # 但有軟刪除的同名記錄
        call_count = [0]

        def filter_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            call_count[0] += 1
            if call_count[0] <= 2:
                # 前兩次查詢 (活躍記錄) 回傳 None
                mock_result.first.return_value = None
            else:
                # 第三次查詢 (軟刪除記錄) 回傳有記錄
                mock_deleted = MagicMock()
                mock_deleted.name = "reserved-name"
                mock_result.first.return_value = mock_deleted
            return mock_result

        mock_db.query.return_value.filter.return_value.filter.side_effect = filter_side_effect

        from app.schemas.project import ProjectCreate

        project_in = ProjectCreate(name="reserved-name", name_zh="保留的名稱")

        with patch("app.services.project_service.get_s3_client"):
            from app.services.project_service import ProjectService

            service = ProjectService(mock_db)

            with pytest.raises(HTTPException) as exc_info:
                service.create_project(project_in)

            assert exc_info.value.status_code == 400
            assert "Hard delete" in exc_info.value.detail

    def test_name_available_after_hard_delete(self):
        """
        測試 Hard Delete 後名稱可重新使用。

        預期行為：
        - 所有唯一性檢查都回傳 None
        - 建立成功
        """
        mock_db = MagicMock()

        # 模擬所有查詢都回傳 None (名稱可用)
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.schemas.project import ProjectCreate

        project_in = ProjectCreate(name="available-name", name_zh="可用的名稱")

        with patch("app.services.project_service.get_s3_client") as mock_s3:
            mock_s3.return_value = MagicMock()

            from app.services.project_service import ProjectService

            service = ProjectService(mock_db)

            # 不應該拋出異常
            # (實際建立會在 mock_db.add 中，這裡只測試檢查邏輯)
            try:
                service.create_project(project_in)
                # 驗證 db.add 被呼叫
                mock_db.add.assert_called_once()
            except HTTPException as e:
                if "reserved" in str(e.detail).lower():
                    pytest.fail(f"Name should be available: {e.detail}")


class TestRecorderNameRelease:
    """測試 Recorder Hard Delete 後識別碼可重新使用。"""

    def test_soft_deleted_recorder_identifier_is_reserved(self):
        """
        測試軟刪除的 Recorder 識別碼被保留。

        預期行為：
        - 建立同識別碼 Recorder 時回傳 400
        - 錯誤訊息提示需要 Hard Delete
        """
        mock_db = MagicMock()

        # 模擬沒有活躍的同識別碼記錄，但有軟刪除的
        mock_db.query.return_value.scalar.side_effect = [False, True]

        from app.schemas.recorder import RecorderCreate
        from app.services.recorder_service import RecorderService

        recorder_in = RecorderCreate(
            brand="SoundTrap",
            model="ST600",
            sn="SN12345",
            sensitivity=-176.0,
        )

        service = RecorderService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.create_recorder(recorder_in)

        assert exc_info.value.status_code == 400
        assert "Hard delete" in exc_info.value.detail
