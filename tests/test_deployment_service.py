"""
DeploymentService 測試 - P1 (重要)

測試 deployment_service.py 的業務邏輯:
1. get_deployment - 取得單一 Deployment
2. get_deployment_details - 取得 Deployment 含關聯
3. get_deployments - 取得 Deployment 列表
4. create_deployment - 建立 Deployment (含自動 phase)
5. update_deployment - 更新 Deployment
6. delete_deployment - 軟刪除 Deployment (含級聯)
7. restore_deployment - 還原 Deployment (含級聯)
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.enums.enums import DeploymentStatus
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate
from app.services.deployment_service import DeploymentService

# =============================================================================
# get_deployment 測試
# =============================================================================


class TestDeploymentServiceGetDeployment:
    """測試 DeploymentService.get_deployment 方法。"""

    def test_get_deployment_success(self):
        """成功取得 Deployment。"""
        mock_db = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )

        service = DeploymentService(mock_db)
        result = service.get_deployment(1)

        assert result == mock_deployment

    def test_get_deployment_not_found_raises_404(self):
        """Deployment 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = DeploymentService(mock_db)

        with pytest.raises(AppException) as exc_info:
            service.get_deployment(999)

        assert exc_info.value.http_status == 404
        assert "not found" in exc_info.value.message


# =============================================================================
# get_deployment_details 測試
# =============================================================================


class TestDeploymentServiceGetDeploymentDetails:
    """測試 DeploymentService.get_deployment_details 方法。"""

    def test_get_deployment_details_success(self):
        """成功取得 Deployment 含關聯資料。"""
        mock_db = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.point = MagicMock()
        mock_deployment.recorder = MagicMock()
        mock_chain = mock_db.query.return_value.options.return_value.filter.return_value
        mock_chain.first.return_value = mock_deployment

        service = DeploymentService(mock_db)
        result = service.get_deployment_details(1)

        assert result == mock_deployment

    def test_get_deployment_details_not_found_raises_404(self):
        """Deployment 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_chain = mock_db.query.return_value.options.return_value.filter.return_value
        mock_chain.first.return_value = None

        service = DeploymentService(mock_db)

        with pytest.raises(AppException) as exc_info:
            service.get_deployment_details(999)

        assert exc_info.value.http_status == 404


# =============================================================================
# get_deployments 測試
# =============================================================================


class TestDeploymentServiceGetDeployments:
    """測試 DeploymentService.get_deployments 方法。"""

    @patch("app.services.deployment_service.paginate")
    def test_get_deployments_returns_tuple(self, mock_paginate):
        """回傳 (Deployment 列表, total) tuple。"""
        mock_db = MagicMock()
        mock_deployments = [MagicMock(), MagicMock()]
        mock_paginate.return_value = (mock_deployments, 2)

        service = DeploymentService(mock_db)
        items, total = service.get_deployments(point_id=1)

        assert items == mock_deployments
        assert total == 2
        mock_paginate.assert_called_once()

    @patch("app.services.deployment_service.paginate")
    def test_get_deployments_with_pagination(self, mock_paginate):
        """支援分頁參數。"""
        mock_db = MagicMock()
        mock_paginate.return_value = ([], 0)

        service = DeploymentService(mock_db)
        items, total = service.get_deployments(point_id=1, skip=5, limit=10)

        # 驗證 paginate 呼叫時帶入正確的 skip 和 limit
        call_args = mock_paginate.call_args
        assert call_args[0][1] == 5  # skip
        assert call_args[0][2] == 10  # limit
        assert items == []
        assert total == 0


# =============================================================================
# create_deployment 測試
# =============================================================================


class TestDeploymentServiceCreateDeployment:
    """測試 DeploymentService.create_deployment 方法。"""

    def test_create_deployment_success(self):
        """成功建立 Deployment。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.scalar.return_value = None

        deployment_data = DeploymentCreate(
            point_id=1,
            recorder_id=1,
            status=DeploymentStatus.UNDEPLOYED,
            deploy_personnel="王小明",
            retrieve_personnel="李大華",
        )

        service = DeploymentService(mock_db)
        service.create_deployment(deployment_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_deployment_auto_phase_first(self):
        """第一個 Deployment 的 phase 為 1。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.scalar.return_value = None

        added_deployment = None

        def capture_add(deployment):
            nonlocal added_deployment
            added_deployment = deployment

        mock_db.add.side_effect = capture_add

        deployment_data = DeploymentCreate(
            point_id=1,
            recorder_id=1,
        )

        service = DeploymentService(mock_db)
        service.create_deployment(deployment_data)

        assert added_deployment.phase == 1

    def test_create_deployment_auto_phase_increment(self):
        """後續 Deployment 的 phase 遞增。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.scalar.return_value = 3

        added_deployment = None

        def capture_add(deployment):
            nonlocal added_deployment
            added_deployment = deployment

        mock_db.add.side_effect = capture_add

        deployment_data = DeploymentCreate(
            point_id=1,
            recorder_id=1,
        )

        service = DeploymentService(mock_db)
        service.create_deployment(deployment_data)

        assert added_deployment.phase == 4


# =============================================================================
# update_deployment 測試
# =============================================================================


class TestDeploymentServiceUpdateDeployment:
    """測試 DeploymentService.update_deployment 方法。"""

    def test_update_deployment_success(self):
        """成功更新 Deployment。"""
        mock_db = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.status = "un-deployed"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )

        update_data = DeploymentUpdate(
            status=DeploymentStatus.SUCCESS, deploy_personnel="王小明"
        )

        service = DeploymentService(mock_db)
        service.update_deployment(1, update_data)

        assert mock_deployment.status == DeploymentStatus.SUCCESS.value
        mock_db.commit.assert_called_once()

    def test_update_deployment_not_found_raises_404(self):
        """Deployment 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        update_data = DeploymentUpdate(description="Updated")

        service = DeploymentService(mock_db)

        with pytest.raises(AppException) as exc_info:
            service.update_deployment(999, update_data)

        assert exc_info.value.http_status == 404


# =============================================================================
# delete_deployment 測試
# =============================================================================


class TestDeploymentServiceDeleteDeployment:
    """測試 DeploymentService.delete_deployment 方法。"""

    def test_delete_deployment_success(self):
        """成功軟刪除 Deployment。"""
        mock_db = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.is_deleted = False
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )

        service = DeploymentService(mock_db)
        service.delete_deployment(1, user_id=2)

        assert mock_deployment.is_deleted is True
        assert mock_deployment.deleted_by == 2
        mock_db.commit.assert_called_once()

    def test_delete_deployment_cascade_to_audios(self):
        """刪除 Deployment 級聯刪除 Audios。"""
        mock_db = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.is_deleted = False
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_deployment
        )

        service = DeploymentService(mock_db)
        service.delete_deployment(1, user_id=2)

        # 確認有執行級聯更新
        assert mock_db.query.return_value.filter.return_value.update.called


# =============================================================================
# restore_deployment 測試
# =============================================================================


class TestDeploymentServiceRestoreDeployment:
    """測試 DeploymentService.restore_deployment 方法。"""

    def test_restore_deployment_success(self):
        """成功還原 Deployment。"""
        mock_db = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.id = 1
        mock_deployment.point_id = 1
        mock_deployment.phase = 1
        mock_deployment.is_deleted = True
        mock_deployment.deleted_at = datetime.now(UTC)

        # 第一次查詢找到 deployment，第二次查詢確認無重複
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_deployment,
            None,
        ]

        service = DeploymentService(mock_db)
        service.restore_deployment(1)

        assert mock_deployment.is_deleted is False
        assert mock_deployment.deleted_at is None
        mock_db.commit.assert_called_once()

    def test_restore_deployment_not_found_raises_404(self):
        """Deployment 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = DeploymentService(mock_db)

        with pytest.raises(AppException) as exc_info:
            service.restore_deployment(999)

        assert exc_info.value.http_status == 404

    def test_restore_deployment_phase_collision_raises_400(self):
        """phase 衝突觸發 400 錯誤。"""
        mock_db = MagicMock()
        deleted_deployment = MagicMock()
        deleted_deployment.id = 1
        deleted_deployment.point_id = 1
        deleted_deployment.phase = 1
        deleted_deployment.is_deleted = True

        active_deployment = MagicMock()
        active_deployment.id = 2

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            deleted_deployment,
            active_deployment,
        ]

        service = DeploymentService(mock_db)

        with pytest.raises(AppException) as exc_info:
            service.restore_deployment(1)

        assert exc_info.value.http_status == 400
        assert "Cannot restore" in exc_info.value.message
