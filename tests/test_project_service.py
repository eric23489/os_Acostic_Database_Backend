from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.services.project_service import ProjectService
from app.schemas.project import ProjectCreate
from app.models.project import ProjectInfo


def test_create_project_autogenerate_name(mock_db):
    """
    測試從 name_zh 自動生成 name。

    當只提供 name_zh 時，系統應自動根據中文名稱生成拼音作為 name。
    """
    # 1. 準備資料
    service = ProjectService(mock_db)
    # 只提供中文名稱
    project_in = ProjectCreate(name_zh="測試專案")

    # 2. 設定 Mock DB 行為
    # 模擬資料庫查詢：多次 filter().first() 都回傳 None（無名稱衝突）
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query

    # 3. 執行 Service 方法
    service.create_project(project_in)

    # 4. 驗證結果
    # 驗證 db.add 被呼叫
    mock_db.add.assert_called_once()

    # 驗證傳入 db.add 的物件中，name 是否已根據 name_zh 自動生成
    added_project = mock_db.add.call_args[0][0]
    assert isinstance(added_project, ProjectInfo)
    assert added_project.name == "ce-shi-zhuan-an"  # "測試專案" 的拼音
    assert added_project.name_zh == "測試專案"


def test_create_project_autogenerate_name_collision(mock_db):
    """
    Test name collision when auto-generating name.
    Should raise HTTPException if generated name exists.
    """
    # 1. 準備資料
    service = ProjectService(mock_db)
    project_in = ProjectCreate(name_zh="測試專案")

    # 2. 設定 Mock DB 行為
    # 模擬查詢名稱時回傳物件 (代表名稱已存在)
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    # 3. 執行 Service 方法並驗證是否拋出例外
    with pytest.raises(HTTPException) as exc_info:
        service.create_project(project_in)

    assert exc_info.value.status_code == 400
    assert "Project with this name already exists" in exc_info.value.detail


def test_create_project_no_name_provided(mock_db):
    """
    Test that an error is raised if neither name nor name_zh is provided.
    """
    service = ProjectService(mock_db)
    # 不提供 name 和 name_zh
    project_in = ProjectCreate()

    with pytest.raises(HTTPException) as exc_info:
        service.create_project(project_in)

    assert exc_info.value.status_code == 400
    assert "Either 'name' or 'name_zh' must be provided" in exc_info.value.detail
