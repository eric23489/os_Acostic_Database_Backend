"""
PointService 測試 - P1 (重要)

測試 point_service.py 的業務邏輯:
1. get_point - 取得單一 Point
2. get_point_details - 取得 Point 含關聯
3. get_points - 取得 Point 列表
4. create_point - 建立 Point
5. update_point - 更新 Point
6. delete_point - 軟刪除 Point (含級聯)
7. restore_point - 還原 Point (含級聯)
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.point import PointCreate, PointUpdate
from app.services.point_service import PointService

# =============================================================================
# get_point 測試
# =============================================================================


class TestPointServiceGetPoint:
    """測試 PointService.get_point 方法。"""

    def test_get_point_success(self):
        """成功取得 Point。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.name = "Test Point"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_point

        service = PointService(mock_db)
        result = service.get_point(1)

        assert result == mock_point

    def test_get_point_not_found_raises_404(self):
        """Point 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PointService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.get_point(999)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


# =============================================================================
# get_point_details 測試
# =============================================================================


class TestPointServiceGetPointDetails:
    """測試 PointService.get_point_details 方法。"""

    def test_get_point_details_success(self):
        """成功取得 Point 含關聯資料。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.project = MagicMock()
        mock_chain = mock_db.query.return_value.options.return_value.filter.return_value
        mock_chain.first.return_value = mock_point

        service = PointService(mock_db)
        result = service.get_point_details(1)

        assert result == mock_point

    def test_get_point_details_not_found_raises_404(self):
        """Point 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_chain = mock_db.query.return_value.options.return_value.filter.return_value
        mock_chain.first.return_value = None

        service = PointService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.get_point_details(999)

        assert exc_info.value.status_code == 404


# =============================================================================
# get_points 測試
# =============================================================================


class TestPointServiceGetPoints:
    """測試 PointService.get_points 方法。"""

    @patch("app.services.point_service.paginate")
    def test_get_points_returns_tuple(self, mock_paginate):
        """回傳 (Point 列表, total) tuple。"""
        mock_db = MagicMock()
        mock_points = [MagicMock(), MagicMock()]
        mock_paginate.return_value = (mock_points, 2)

        service = PointService(mock_db)
        items, total = service.get_points(project_id=1)

        assert items == mock_points
        assert total == 2
        mock_paginate.assert_called_once()

    @patch("app.services.point_service.paginate")
    def test_get_points_with_pagination(self, mock_paginate):
        """支援分頁參數。"""
        mock_db = MagicMock()
        mock_paginate.return_value = ([], 0)

        service = PointService(mock_db)
        items, total = service.get_points(project_id=1, skip=10, limit=20)

        # 驗證 paginate 呼叫時帶入正確的 skip 和 limit
        call_args = mock_paginate.call_args
        assert call_args[0][1] == 10  # skip
        assert call_args[0][2] == 20  # limit
        assert items == []
        assert total == 0


# =============================================================================
# create_point 測試
# =============================================================================


class TestPointServiceCreatePoint:
    """測試 PointService.create_point 方法。"""

    def test_create_point_success(self):
        """成功建立 Point。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        point_data = PointCreate(
            project_id=1,
            name="New Point",
            gps_lat=25.0,
            gps_lon=121.5,
            depth=100.0,
        )

        service = PointService(mock_db)
        service.create_point(point_data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_point_duplicate_name_raises_400(self):
        """同專案重複名稱觸發 400 錯誤。"""
        mock_db = MagicMock()
        existing_point = MagicMock()
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = existing_point

        point_data = PointCreate(
            project_id=1,
            name="Existing Point",
            gps_lat=25.0,
            gps_lon=121.5,
            depth=100.0,
        )

        service = PointService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.create_point(point_data)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail


# =============================================================================
# update_point 測試
# =============================================================================


class TestPointServiceUpdatePoint:
    """測試 PointService.update_point 方法。"""

    def test_update_point_success(self):
        """成功更新 Point。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.name = "Old Name"
        mock_point.project_id = 1

        # 第一次查詢找到 point，第二次查詢確認無重複
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_point,
            None,
        ]

        update_data = PointUpdate(name="New Name")

        service = PointService(mock_db)
        service.update_point(1, update_data)

        assert mock_point.name == "New Name"
        mock_db.commit.assert_called_once()

    def test_update_point_duplicate_name_raises_400(self):
        """更新為重複名稱觸發 400 錯誤。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.name = "Old Name"
        mock_point.project_id = 1

        other_point = MagicMock()
        other_point.id = 2

        # 第一次查詢找到 point，第二次查詢發現重複
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_point,
            other_point,
        ]

        update_data = PointUpdate(name="Duplicate Name")

        service = PointService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.update_point(1, update_data)

        assert exc_info.value.status_code == 400


# =============================================================================
# delete_point 測試
# =============================================================================


class TestPointServiceDeletePoint:
    """測試 PointService.delete_point 方法。"""

    def test_delete_point_success(self):
        """成功軟刪除 Point。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.is_deleted = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_point
        mock_db.query.return_value.filter.return_value.all.return_value = []

        service = PointService(mock_db)
        service.delete_point(1, user_id=2)

        assert mock_point.is_deleted is True
        assert mock_point.deleted_by == 2
        mock_db.commit.assert_called_once()

    def test_delete_point_cascade_to_deployments(self):
        """刪除 Point 級聯刪除 Deployments。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.is_deleted = False

        mock_deployment = MagicMock()
        mock_deployment.id = 10

        # 設置查詢返回
        mock_db.query.return_value.filter.return_value.first.return_value = mock_point
        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_deployment
        ]

        service = PointService(mock_db)
        service.delete_point(1, user_id=2)

        # 確認有執行級聯更新
        assert mock_db.query.return_value.filter.return_value.update.called


# =============================================================================
# restore_point 測試
# =============================================================================


class TestPointServiceRestorePoint:
    """測試 PointService.restore_point 方法。"""

    def test_restore_point_success(self):
        """成功還原 Point。"""
        mock_db = MagicMock()
        mock_point = MagicMock()
        mock_point.id = 1
        mock_point.name = "Deleted Point"
        mock_point.project_id = 1
        mock_point.is_deleted = True
        mock_point.deleted_at = datetime.now(UTC)

        # 第一次查詢找到 point，第二次查詢確認無重複
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_point,
            None,
        ]

        service = PointService(mock_db)
        service.restore_point(1)

        assert mock_point.is_deleted is False
        assert mock_point.deleted_at is None
        mock_db.commit.assert_called_once()

    def test_restore_point_not_found_raises_404(self):
        """Point 不存在觸發 404 錯誤。"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = PointService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.restore_point(999)

        assert exc_info.value.status_code == 404

    def test_restore_point_name_collision_raises_400(self):
        """名稱衝突觸發 400 錯誤。"""
        mock_db = MagicMock()
        deleted_point = MagicMock()
        deleted_point.id = 1
        deleted_point.name = "Test Point"
        deleted_point.project_id = 1
        deleted_point.is_deleted = True

        active_point = MagicMock()
        active_point.id = 2

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            deleted_point,
            active_point,
        ]

        service = PointService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.restore_point(1)

        assert exc_info.value.status_code == 400
        assert "Cannot restore" in exc_info.value.detail
