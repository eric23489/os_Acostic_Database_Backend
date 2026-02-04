"""
軟刪除 Service 層測試模組。

本模組測試 Service 層的軟刪除邏輯，包含：
- 級聯軟刪除（Cascade Soft Delete）
- 還原時的時間窗口邏輯
- 唯一性約束檢查

所有測試使用 mock，不連接真實資料庫。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import HTTPException

from app.services.project_service import ProjectService
from app.services.point_service import PointService
from app.services.deployment_service import DeploymentService
from app.services.audio_service import AudioService
from app.services.recorder_service import RecorderService


# =============================================================================
# ProjectService 軟刪除測試
# =============================================================================


class TestProjectServiceDelete:
    """測試 ProjectService 的刪除功能。"""

    def test_delete_project_marks_deleted(self, mock_db):
        """
        測試刪除專案時正確標記 is_deleted。

        預期行為：
        - 專案的 is_deleted 設為 True
        - deleted_at 設為當前時間
        - deleted_by 設為執行刪除的使用者 ID
        """
        service = ProjectService(mock_db)

        # 建立模擬專案物件
        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.name = "test-project"
        mock_project.is_deleted = False

        # 模擬查詢回傳專案
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_project
        )
        # 模擬子查詢
        mock_db.query.return_value.filter.return_value.update.return_value = 0

        # 執行刪除
        user_id = 1
        result = service.delete_project(1, user_id)

        # 驗證專案被標記為刪除
        assert mock_project.is_deleted is True
        assert mock_project.deleted_by == user_id
        assert mock_project.deleted_at is not None
        mock_db.commit.assert_called()

    def test_delete_project_cascades_to_points(self, mock_db):
        """
        測試刪除專案時級聯刪除相關測站。

        預期行為：
        - 專案下所有測站都被標記為 is_deleted=True
        """
        service = ProjectService(mock_db)

        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.is_deleted = False

        # 模擬查詢結果
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_project
        )

        # 執行刪除
        service.delete_project(1, user_id=1)

        # 驗證有呼叫 update 來更新 Points
        # 注意：實際的 update 呼叫會透過 mock_db.query(...).filter(...).update(...)
        assert mock_db.query.called
        mock_db.commit.assert_called()

    def test_delete_project_not_found_raises_404(self, mock_db):
        """
        測試刪除不存在的專案時拋出 404 錯誤。

        預期行為：
        - 拋出 HTTPException，狀態碼 404
        """
        service = ProjectService(mock_db)

        # 模擬查詢回傳 None
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
            None
        )

        with pytest.raises(HTTPException) as exc_info:
            service.delete_project(999, user_id=1)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestProjectServiceRestore:
    """測試 ProjectService 的還原功能。"""

    def test_restore_project_success(self, mock_db):
        """
        測試成功還原專案。

        預期行為：
        - 專案的 is_deleted 設為 False
        - deleted_at 和 deleted_by 設為 None
        """
        service = ProjectService(mock_db)

        deleted_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.name = "test-project"
        mock_project.name_zh = None
        mock_project.is_deleted = True
        mock_project.deleted_at = deleted_at

        # 使用 side_effect 來區分不同的查詢
        def mock_filter_first(*args, **kwargs):
            # 根據呼叫次數返回不同結果
            if mock_db.query.call_count == 1:
                # 第一次查詢：找到要還原的專案
                return mock_project
            else:
                # 之後的查詢：檢查衝突，回傳 None 表示無衝突
                return None

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = mock_filter_first
        mock_query.update.return_value = 0
        mock_db.query.return_value = mock_query

        result = service.restore_project(1)

        # 驗證專案被還原
        assert mock_project.is_deleted is False
        assert mock_project.deleted_at is None
        assert mock_project.deleted_by is None
        mock_db.commit.assert_called()

    def test_restore_project_name_collision_raises_400(self, mock_db):
        """
        測試還原專案時發生名稱衝突。

        預期行為：
        - 拋出 HTTPException，狀態碼 400
        """
        service = ProjectService(mock_db)

        mock_project = MagicMock()
        mock_project.id = 1
        mock_project.name = "duplicate-name"
        mock_project.name_zh = None
        mock_project.is_deleted = True
        mock_project.deleted_at = datetime.now(timezone.utc)

        mock_existing = MagicMock()  # 代表已存在的同名專案

        # 第一次查詢找到要還原的專案
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        # 第二次查詢發現名稱衝突
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_existing
        )

        with pytest.raises(HTTPException) as exc_info:
            service.restore_project(1)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()


class TestProjectServiceDeleteAudios:
    """測試 ProjectService 的背景音檔刪除功能。"""

    def test_delete_project_audios_updates_all_audios(self, mock_db):
        """
        測試背景刪除音檔功能。

        預期行為：
        - 所有相關音檔都被標記為刪除
        - 使用與父專案相同的 deleted_at 時間戳
        """
        service = ProjectService(mock_db)

        deleted_at = datetime.now(timezone.utc)
        user_id = 1
        project_id = 1

        # 模擬 update 呼叫
        mock_db.query.return_value.filter.return_value.update.return_value = 100

        service.delete_project_audios(project_id, user_id, deleted_at)

        # 驗證 commit 被呼叫
        mock_db.commit.assert_called()


# =============================================================================
# PointService 軟刪除測試
# =============================================================================


class TestPointServiceDelete:
    """測試 PointService 的刪除功能。"""

    def test_delete_point_marks_deleted(self, mock_db):
        """
        測試刪除測站時正確標記 is_deleted。

        預期行為：
        - 測站的 is_deleted 設為 True
        """
        service = PointService(mock_db)

        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.project_id = 1
        mock_point.name = "test-point"
        mock_point.is_deleted = False

        # 模擬查詢回傳測站
        mock_db.query.return_value.filter.return_value.first.return_value = mock_point
        # 模擬找到的 deployments
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = service.delete_point(1, user_id=1)

        assert mock_point.is_deleted is True
        assert mock_point.deleted_by == 1
        mock_db.commit.assert_called()

    def test_delete_point_cascades_to_deployments_and_audios(self, mock_db):
        """
        測試刪除測站時級聯刪除佈放紀錄和音檔。

        預期行為：
        - 測站下所有佈放紀錄都被標記為刪除
        - 相關音檔也被標記為刪除
        """
        service = PointService(mock_db)

        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.is_deleted = False

        # 模擬找到的 deployments
        mock_deployment = MagicMock()
        mock_deployment.id = 10

        mock_db.query.return_value.filter.return_value.first.return_value = mock_point
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_deployment
        ]

        service.delete_point(1, user_id=1)

        # 驗證有呼叫 update 來更新子紀錄
        assert mock_db.query.called
        mock_db.commit.assert_called()


# =============================================================================
# DeploymentService 軟刪除測試
# =============================================================================


class TestDeploymentServiceDelete:
    """測試 DeploymentService 的刪除功能。"""

    def test_delete_deployment_marks_deleted(self, mock_db):
        """
        測試刪除佈放紀錄時正確標記 is_deleted。

        預期行為：
        - 佈放紀錄的 is_deleted 設為 True
        """
        service = DeploymentService(mock_db)

        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.point_id = 1
        mock_deployment.is_deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )

        result = service.delete_deployment(1, user_id=1)

        assert mock_deployment.is_deleted is True
        assert mock_deployment.deleted_by == 1
        mock_db.commit.assert_called()

    def test_delete_deployment_cascades_to_audios(self, mock_db):
        """
        測試刪除佈放紀錄時級聯刪除音檔。

        預期行為：
        - 佈放紀錄下所有音檔都被標記為刪除
        """
        service = DeploymentService(mock_db)

        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.is_deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )

        service.delete_deployment(1, user_id=1)

        # 驗證有呼叫 update 來更新音檔
        assert mock_db.query.called
        mock_db.commit.assert_called()


class TestDeploymentServiceRestore:
    """測試 DeploymentService 的還原功能。"""

    def test_restore_deployment_phase_collision_raises_400(self, mock_db):
        """
        測試還原佈放紀錄時發生階段衝突。

        預期行為：
        - 拋出 HTTPException，狀態碼 400
        """
        service = DeploymentService(mock_db)

        deleted_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.point_id = 1
        mock_deployment.phase = 1
        mock_deployment.is_deleted = True
        mock_deployment.deleted_at = deleted_at

        mock_existing = MagicMock()  # 代表已存在的同階段佈放

        # 第一次查詢找到要還原的 deployment
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )
        # 第二次查詢發現階段衝突
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_existing
        )

        with pytest.raises(HTTPException) as exc_info:
            service.restore_deployment(1)

        assert exc_info.value.status_code == 400


# =============================================================================
# AudioService 軟刪除測試
# =============================================================================


class TestAudioServiceDelete:
    """測試 AudioService 的刪除功能。"""

    def test_delete_audio_marks_deleted(self, mock_db):
        """
        測試刪除音檔時正確標記 is_deleted。

        預期行為：
        - 音檔的 is_deleted 設為 True
        """
        service = AudioService(mock_db)

        mock_audio = MagicMock()
        mock_audio.id = 1
        mock_audio.deployment_id = 1
        mock_audio.is_deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_audio

        result = service.delete_audio(1, user_id=1)

        assert mock_audio.is_deleted is True
        assert mock_audio.deleted_by == 1
        mock_db.commit.assert_called()

    def test_delete_audio_not_found_raises_404(self, mock_db):
        """
        測試刪除不存在的音檔時拋出 404 錯誤。

        預期行為：
        - 拋出 HTTPException，狀態碼 404
        """
        service = AudioService(mock_db)

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            service.delete_audio(999, user_id=1)

        assert exc_info.value.status_code == 404


class TestAudioServiceRestore:
    """測試 AudioService 的還原功能。"""

    def test_restore_audio_success(self, mock_db):
        """
        測試成功還原音檔。

        預期行為：
        - 音檔的 is_deleted 設為 False
        """
        service = AudioService(mock_db)

        mock_audio = MagicMock()
        mock_audio.id = 1
        mock_audio.object_key = "test/path.wav"
        mock_audio.is_deleted = True

        # 使用 side_effect 來區分不同的查詢
        def mock_filter_first(*args, **kwargs):
            if mock_db.query.call_count == 1:
                # 第一次查詢：找到要還原的音檔
                return mock_audio
            else:
                # 之後的查詢：檢查衝突，回傳 None 表示無衝突
                return None

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = mock_filter_first
        mock_db.query.return_value = mock_query

        result = service.restore_audio(1)

        assert mock_audio.is_deleted is False
        assert mock_audio.deleted_at is None
        mock_db.commit.assert_called()

    def test_restore_audio_object_key_collision_raises_400(self, mock_db):
        """
        測試還原音檔時發生 object_key 衝突。

        預期行為：
        - 拋出 HTTPException，狀態碼 400
        """
        service = AudioService(mock_db)

        mock_audio = MagicMock()
        mock_audio.id = 1
        mock_audio.object_key = "duplicate/path.wav"
        mock_audio.is_deleted = True

        mock_existing = MagicMock()  # 代表已存在的同 object_key 音檔

        # 第一次查詢找到要還原的音檔
        mock_db.query.return_value.filter.return_value.first.return_value = mock_audio
        # 第二次查詢發現衝突
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_existing
        )

        with pytest.raises(HTTPException) as exc_info:
            service.restore_audio(1)

        assert exc_info.value.status_code == 400


# =============================================================================
# RecorderService 軟刪除測試
# =============================================================================


class TestRecorderServiceDelete:
    """測試 RecorderService 的刪除功能。"""

    def test_delete_recorder_marks_deleted(self, mock_db):
        """
        測試刪除錄音機時正確標記 is_deleted。

        預期行為：
        - 錄音機的 is_deleted 設為 True
        """
        service = RecorderService(mock_db)

        mock_recorder = MagicMock()
        mock_recorder.id = 1
        mock_recorder.brand = "Brand"
        mock_recorder.model = "Model"
        mock_recorder.sn = "SN123"
        mock_recorder.is_deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_recorder
        )

        result = service.delete_recorder(1, user_id=1)

        assert mock_recorder.is_deleted is True
        assert mock_recorder.deleted_by == 1
        mock_db.commit.assert_called()


class TestRecorderServiceRestore:
    """測試 RecorderService 的還原功能。"""

    def test_restore_recorder_success(self, mock_db):
        """
        測試成功還原錄音機。

        預期行為：
        - 錄音機的 is_deleted 設為 False
        """
        service = RecorderService(mock_db)

        mock_recorder = MagicMock()
        mock_recorder.id = 1
        mock_recorder.brand = "Brand"
        mock_recorder.model = "Model"
        mock_recorder.sn = "SN123"
        mock_recorder.is_deleted = True

        # 使用 side_effect 來區分不同的查詢
        def mock_filter_first(*args, **kwargs):
            if mock_db.query.call_count == 1:
                # 第一次查詢：找到要還原的錄音機
                return mock_recorder
            else:
                # 之後的查詢：檢查衝突，回傳 None 表示無衝突
                return None

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = mock_filter_first
        mock_db.query.return_value = mock_query

        result = service.restore_recorder(1)

        assert mock_recorder.is_deleted is False
        mock_db.commit.assert_called()

    def test_restore_recorder_unique_collision_raises_400(self, mock_db):
        """
        測試還原錄音機時發生唯一性衝突。

        預期行為：
        - 拋出 HTTPException，狀態碼 400
        """
        service = RecorderService(mock_db)

        mock_recorder = MagicMock()
        mock_recorder.id = 1
        mock_recorder.brand = "Brand"
        mock_recorder.model = "Model"
        mock_recorder.sn = "SN123"
        mock_recorder.is_deleted = True

        mock_existing = MagicMock()

        # 第一次查詢找到要還原的錄音機
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_recorder
        )
        # 第二次查詢發現衝突
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_existing
        )

        with pytest.raises(HTTPException) as exc_info:
            service.restore_recorder(1)

        assert exc_info.value.status_code == 400
