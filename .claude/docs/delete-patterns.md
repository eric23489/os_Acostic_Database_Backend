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

```python
class TestHardDelete:
    def test_hard_delete_requires_admin(self, client, user_token):
        """一般使用者無法執行 hard delete"""
        response = client.delete(
            "/api/v1/resources/1/permanent",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_hard_delete_releases_name(self, client, admin_token, db):
        """Hard delete 後名稱可重新使用"""
        # 建立 → 軟刪除 → Hard delete → 重新建立
        # ...

    def test_hard_delete_removes_minio_objects(self, client, admin_token, mock_s3):
        """Hard delete 應刪除 MinIO 物件"""
        # ...
        mock_s3.delete_object.assert_called_once()
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
- 測試策略
```

---

## Related Files
- 實作範例: `app/services/project_service.py:316` (hard_delete_project)
- 實作範例: `app/services/audio_service.py:149` (hard_delete_audio)
- API 範例: `app/api/v1/endpoints/api_projects.py:105`
