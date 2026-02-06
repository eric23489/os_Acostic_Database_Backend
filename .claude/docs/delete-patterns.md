# Delete Patterns 刪除模式範本

本文件提供 Soft Delete、Hard Delete、Restore 的完整實作範本。

## 快速參考

| 操作 | API | 權限 | MinIO |
|------|-----|------|-------|
| Soft Delete | `DELETE /{id}` | 登入使用者 | 不影響 |
| Hard Delete | `DELETE /{id}/permanent` | Admin | 刪除物件 |
| Restore | `POST /{id}/restore` | 刪除者/Admin | 不影響 |

---

## 1. Soft Delete 範本

### Service 層
```python
def delete_resource(self, resource_id: int, user_id: int) -> ResourceInfo:
    resource = self.get_resource(resource_id)
    resource.is_deleted = True
    resource.deleted_at = datetime.now(UTC)
    resource.deleted_by = user_id
    self.db.add(resource)
    self.db.commit()
    self.db.refresh(resource)
    return resource
```

### API 層
```python
@router.delete("/{resource_id}", response_model=ResourceResponse)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ResourceService(db).delete_resource(resource_id, current_user.id)
```

---

## 2. Hard Delete 範本

### 設計決策
- **刪除順序** (4 步驟):
  1. MinIO 物件 (批量刪除 .wav 檔案)
  2. MinIO Bucket (必須為空才能刪除)
  3. DB 子記錄 (Audios → Deployments → Points)
  4. DB 父記錄 (Project)
- **原因**: MinIO 孤兒可定期清理，DB 失敗可回滾
- **名稱釋放**: Hard Delete 後名稱可重新使用

### Service 層 (單一資源)
```python
def hard_delete_resource(self, resource_id: int) -> dict:
    """
    永久刪除資源。

    包含：
    - 刪除 MinIO 物件
    - 刪除資料庫記錄
    - 釋放唯一識別欄位，可重新使用
    """
    # 1. 查詢資源 (包含已軟刪除)
    resource = self.db.query(ResourceInfo).filter(ResourceInfo.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    # 2. 取得 MinIO bucket 名稱 (從父層級)
    bucket_name = self._get_bucket_name(resource)

    # 3. 刪除 MinIO 物件
    s3_client = get_s3_client()
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=resource.object_key)
    except Exception as e:
        logger.warning(f"Failed to delete object {resource.object_key}: {e}")

    # 4. 刪除 DB 記錄
    self.db.query(ResourceInfo).filter(ResourceInfo.id == resource_id).delete()
    self.db.commit()

    return {"message": "Resource permanently deleted"}
```

### Service 層 (級聯刪除 - Project 層級)
```python
def hard_delete_project(self, project_id: int) -> dict:
    """
    永久刪除 Project 及所有相關資料。
    """
    # 1. 查詢 Project (包含已軟刪除)
    project = self.db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.name

    # 2. 建立子查詢
    point_ids_sub = self.db.query(PointInfo.id).filter(PointInfo.project_id == project_id)
    deployment_ids_sub = self.db.query(DeploymentInfo.id).filter(
        DeploymentInfo.point_id.in_(point_ids_sub)
    )

    # 3. 取得所有 Audio 的 object_key
    audios = self.db.query(AudioInfo).filter(
        AudioInfo.deployment_id.in_(deployment_ids_sub)
    ).all()

    # 4. 刪除 MinIO 物件 (批量)
    s3_client = get_s3_client()
    if audios:
        objects_to_delete = [{"Key": a.object_key} for a in audios]
        for i in range(0, len(objects_to_delete), 1000):  # S3 每次最多 1000
            batch = objects_to_delete[i:i + 1000]
            try:
                s3_client.delete_objects(Bucket=project_name, Delete={"Objects": batch})
            except Exception as e:
                logger.warning(f"Failed to delete objects: {e}")

    # 5. 刪除 MinIO Bucket
    try:
        s3_client.delete_bucket(Bucket=project_name)
    except Exception as e:
        logger.warning(f"Failed to delete bucket: {e}")

    # 6. 刪除 DB 記錄 (先子後父)
    deleted_audios = self.db.query(AudioInfo).filter(
        AudioInfo.deployment_id.in_(deployment_ids_sub)
    ).delete(synchronize_session=False)

    self.db.query(DeploymentInfo).filter(
        DeploymentInfo.point_id.in_(point_ids_sub)
    ).delete(synchronize_session=False)

    self.db.query(PointInfo).filter(
        PointInfo.project_id == project_id
    ).delete(synchronize_session=False)

    self.db.query(ProjectInfo).filter(
        ProjectInfo.id == project_id
    ).delete(synchronize_session=False)

    self.db.commit()

    return {"message": f"Project '{project_name}' permanently deleted", "deleted_audios": deleted_audios}
```

### API 層
```python
@router.delete("/{resource_id}/permanent", response_model=dict)
def hard_delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    永久刪除資源。需要 Admin 權限。
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required for permanent deletion",
        )
    return ResourceService(db).hard_delete_resource(resource_id)
```

---

## 3. Restore 範本

### Service 層
```python
def restore_resource(self, resource_id: int) -> ResourceInfo:
    # 查詢資源 (包含已軟刪除)
    resource = self.db.query(ResourceInfo).filter(ResourceInfo.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # 檢查唯一欄位衝突
    if self.db.query(ResourceInfo).filter(
        ResourceInfo.unique_field == resource.unique_field,
        ResourceInfo.is_deleted.is_(False),
        ResourceInfo.id != resource_id,
    ).first():
        raise HTTPException(
            status_code=400,
            detail="Active resource with this identifier already exists. Cannot restore.",
        )

    resource.is_deleted = False
    resource.deleted_at = None
    resource.deleted_by = None
    self.db.add(resource)
    self.db.commit()
    self.db.refresh(resource)
    return resource
```

### API 層
```python
@router.post("/{resource_id}/restore", response_model=ResourceResponse)
def restore_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    resource = db.query(ResourceInfo).filter(ResourceInfo.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # 權限檢查: 刪除者或 Admin
    if current_user.role != UserRole.ADMIN.value and current_user.id != resource.deleted_by:
        raise HTTPException(
            status_code=403,
            detail="Only the deleter or admin can restore this resource",
        )
    return ResourceService(db).restore_resource(resource_id)
```

---

## 4. 名稱保留檢查 (Create 時)

```python
def create_resource(self, resource_in: ResourceCreate) -> ResourceInfo:
    # 檢查活躍記錄衝突
    if self.db.query(ResourceInfo).filter(
        ResourceInfo.name == resource_in.name,
        ResourceInfo.is_deleted.is_(False),
    ).first():
        raise HTTPException(status_code=400, detail="Resource with this name already exists")

    # 檢查軟刪除記錄保留
    if self.db.query(ResourceInfo).filter(
        ResourceInfo.name == resource_in.name,
        ResourceInfo.is_deleted.is_(True),
    ).first():
        raise HTTPException(
            status_code=400,
            detail="Name reserved by deleted resource. Hard delete to release.",
        )

    # ... 建立邏輯
```

---

## 5. 測試範本

### 測試案例清單

| 類型 | 測試名稱 | 驗證目標 |
|------|---------|----------|
| Permission | test_hard_delete_requires_admin | 非 Admin 回傳 403 |
| Happy | test_hard_delete_success | 成功刪除回傳 200 |
| Error | test_hard_delete_not_found | 資源不存在回傳 404 |
| Error | test_hard_delete_continues_when_minio_fails | MinIO 失敗不中斷 DB |
| Edge | test_hard_delete_empty_project | 空 Project 正常刪除 |
| Edge | test_hard_delete_batch_over_1000 | 分批刪除 >1000 物件 |
| Edge | test_soft_deleted_name_is_reserved | 軟刪除名稱保留 |
| Edge | test_name_available_after_hard_delete | Hard Delete 後名稱可用 |

### Fixture 範本
```python
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from app.core.config import settings
from app.enums.enums import UserRole

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
```

### API 層測試
```python
class TestResourceHardDelete:
    """測試 Resource 永久刪除功能。"""

    def test_hard_delete_requires_admin(self, client, mock_normal_user):
        """測試一般使用者無法執行永久刪除。"""
        from app.core.auth import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: mock_normal_user
        response = client.delete(f"{settings.api_prefix}/resources/1/permanent")

        assert response.status_code == 403
        assert "Admin" in response.json()["detail"]

    def test_hard_delete_success(self, client):
        """測試成功永久刪除。"""
        with patch("app.api.v1.endpoints.api_resources.ResourceService") as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_resource.return_value = {
                "message": "Resource permanently deleted",
            }

            response = client.delete(f"{settings.api_prefix}/resources/1/permanent")

            assert response.status_code == 200
            assert "permanently deleted" in response.json()["message"]
            mock_service.hard_delete_resource.assert_called_once_with(1)

    def test_hard_delete_not_found(self, client):
        """測試刪除不存在的資源。"""
        with patch("app.api.v1.endpoints.api_resources.ResourceService") as MockService:
            mock_service = MockService.return_value
            mock_service.hard_delete_resource.side_effect = HTTPException(
                status_code=404, detail="Resource not found"
            )

            response = client.delete(f"{settings.api_prefix}/resources/1/permanent")
            assert response.status_code == 404
```

### Service 層測試 (MinIO 整合)
```python
class TestResourceServiceHardDelete:
    """測試 ResourceService 的 hard_delete 方法。"""

    def test_hard_delete_removes_minio_objects(self):
        """測試永久刪除會刪除 MinIO 物件。"""
        with patch("app.services.resource_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            mock_db = MagicMock()
            mock_resource = MagicMock()
            mock_resource.id = 1
            mock_resource.name = "test-resource"

            mock_db.query.return_value.filter.return_value.first.return_value = mock_resource
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.delete.return_value = 0

            from app.services.resource_service import ResourceService
            service = ResourceService(mock_db)
            result = service.hard_delete_resource(1)

            mock_s3.delete_bucket.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_hard_delete_continues_when_minio_fails(self):
        """測試 MinIO 失敗時 DB 刪除仍執行。"""
        with patch("app.services.resource_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3
            mock_s3.delete_objects.side_effect = Exception("MinIO connection failed")
            mock_s3.delete_bucket.side_effect = Exception("MinIO connection failed")

            mock_db = MagicMock()
            mock_resource = MagicMock()
            mock_resource.id = 1
            mock_resource.name = "test-resource"

            mock_db.query.return_value.filter.return_value.first.return_value = mock_resource
            mock_db.query.return_value.filter.return_value.all.return_value = []
            mock_db.query.return_value.filter.return_value.delete.return_value = 0

            from app.services.resource_service import ResourceService
            service = ResourceService(mock_db)
            result = service.hard_delete_resource(1)

            # DB commit 仍被呼叫
            mock_db.commit.assert_called_once()
            assert "permanently deleted" in result["message"]

    def test_hard_delete_batch_over_1000_objects(self):
        """測試分批刪除超過 1000 個物件。"""
        with patch("app.services.resource_service.get_s3_client") as mock_get_s3:
            mock_s3 = MagicMock()
            mock_get_s3.return_value = mock_s3

            mock_db = MagicMock()
            mock_resource = MagicMock()
            mock_resource.id = 1
            mock_resource.name = "large-resource"

            # Mock 1500 個物件
            mock_items = [MagicMock(object_key=f"item_{i}.wav") for i in range(1500)]

            mock_db.query.return_value.filter.return_value.first.return_value = mock_resource
            mock_db.query.return_value.filter.return_value.all.return_value = mock_items
            mock_db.query.return_value.filter.return_value.delete.return_value = 1500

            from app.services.resource_service import ResourceService
            service = ResourceService(mock_db)
            result = service.hard_delete_resource(1)

            # 驗證分批呼叫 (1000 + 500)
            assert mock_s3.delete_objects.call_count == 2
```

### 名稱釋放測試
```python
class TestNameRelease:
    """測試 Hard Delete 後名稱可重新使用。"""

    def test_soft_deleted_name_is_reserved(self):
        """測試軟刪除名稱被保留，無法建立同名資源。"""
        mock_db = MagicMock()

        # 模擬: 無活躍記錄，但有軟刪除記錄
        call_count = [0]
        def filter_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            call_count[0] += 1
            if call_count[0] <= 2:
                mock_result.first.return_value = None  # 無活躍記錄
            else:
                mock_result.first.return_value = MagicMock()  # 有軟刪除記錄
            return mock_result

        mock_db.query.return_value.filter.return_value.filter.side_effect = filter_side_effect

        from app.services.resource_service import ResourceService
        service = ResourceService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.create_resource(resource_in)

        assert exc_info.value.status_code == 400
        assert "Hard delete" in exc_info.value.detail

    def test_name_available_after_hard_delete(self):
        """測試 Hard Delete 後名稱可重新使用。"""
        mock_db = MagicMock()

        # 模擬: 所有查詢回傳 None (名稱可用)
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.resource_service.get_s3_client") as mock_s3:
            mock_s3.return_value = MagicMock()

            from app.services.resource_service import ResourceService
            service = ResourceService(mock_db)
            service.create_resource(resource_in)

            mock_db.add.assert_called_once()
```

---

## 6. 多角色討論提示詞

### 提問者
```
你是產品提問者。針對「{主題}」，從使用者和產品角度提出 5 個關鍵問題：
- 正常流程會如何運作？
- 如果失敗會怎樣？使用者會看到什麼？
- 有哪些邊界情況？
- 資料一致性如何保證？
- 是否有安全性考量？
```

### 架構師
```
你是系統架構師。針對「{主題}」，從架構角度進行分析：

**一致性 (Consistency):**
1. 跨資源操作的原子性如何保證？
2. 部分失敗時系統會處於什麼狀態？

**可靠性 (Reliability):**
3. 操作是否冪等？可否安全重試？
4. 失敗恢復機制是什麼？

**擴展性 (Scalability):**
5. 資料量 10x 時的瓶頸在哪？
6. 是否需要非同步/分批處理？

**依賴與耦合 (Dependencies):**
7. 依賴哪些外部服務？不可用時如何處理？
8. FK 約束如何處理？

**方案比較:**
列出 2-3 個可行方案，以表格比較：
| 方案 | 一致性 | 複雜度 | 效能 | 風險 |

最後給出推薦方案和理由。
```

### 後端工程師
```
你是後端工程師。針對選定的架構方案，提出實作細節：
- 程式碼結構和檔案組織
- 錯誤處理機制
- 範例程式碼
```

### 測試工程師
```
你是測試工程師。針對「{主題}」，設計完整的測試策略：

**測試層級:**
1. 單元測試: 哪些函式需要獨立測試？
2. 整合測試: 哪些元件互動需要驗證？
3. API 測試: 哪些端點和情境需要覆蓋？

**測試案例設計:**
- 正常路徑 (Happy Path)
- 錯誤處理 (Error Cases)
- 邊界條件 (Edge Cases)
- 權限檢查 (Permission)

**Mock 策略:**
- 哪些依賴需要 Mock？(DB, MinIO, 外部服務)
- Mock 的粒度？(函式層級 vs 類別層級)

**驗證清單:**
提供測試案例清單，格式：
| 測試名稱 | 類型 | 驗證目標 |
```

---

## Related Files
- 實作範例: `app/services/project_service.py:316` (hard_delete_project)
- 實作範例: `app/services/audio_service.py:149` (hard_delete_audio)
- API 範例: `app/api/v1/endpoints/api_projects.py:105`
