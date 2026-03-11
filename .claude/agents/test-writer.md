---
name: test-writer
description: >
  洋聲測試產生器。在新增 service 方法或 API endpoint 後，按照專案測試模式生成對應測試。
  Use after adding new service methods or API endpoints. Can write to tests/ directory.
tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - Bash
---

# Test Writer — 洋聲後端測試產生器

## 職責

按照專案既有的測試模式，為新增的 service 方法或 API endpoint 生成完整測試。

---

## 開始前的準備工作

### 1. 讀取 conftest.py 確認現有 fixtures

```
Read: tests/conftest.py
```

標準 fixtures：
- `mock_db` — `MagicMock()` 模擬的 DB session
- `mock_current_user` — 模擬的登入使用者
- `client` — `TestClient` + `dependency_overrides`

### 2. 讀取現有測試檔案作為範本

```
Glob: tests/test_*.py
```

選取與目標資源最相近的測試檔案讀取，了解既有命名慣例。

### 3. 讀取被測試的目標

```
Read: app/services/{resource}_service.py
Read: app/api/v1/endpoints/api_{resource}s.py（若存在）
Read: app/core/exceptions.py（確認相關 AppException 常數）
```

---

## 測試模式

### Service 測試

```python
class TestXxxServiceCreate:
    """測試 XxxService.create_xxx 方法"""

    def test_create_xxx_success(self, mock_db: MagicMock) -> None:
        """正常建立"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        payload = XxxCreate(field="value")

        # Act
        service = XxxService(mock_db)
        result = service.create_xxx(payload, created_by=1)

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.field == "value"

    def test_create_xxx_duplicate_raises(self, mock_db: MagicMock) -> None:
        """重複名稱應 raise AppException"""
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

        service = XxxService(mock_db)
        with pytest.raises(AppException) as exc_info:
            service.create_xxx(XxxCreate(field="value"), created_by=1)

        assert exc_info.value.error_code == "XXX_NAME_DUPLICATE"
```

### API 測試

```python
class TestApiXxxCreate:
    """測試 POST /api/v1/xxxs"""

    def test_create_xxx_success(
        self, client: TestClient, mock_db: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """201 正常建立"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post(
            "/api/v1/xxxs",
            json={"field": "value"},
            headers={"Authorization": "Bearer test"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["field"] == "value"

    def test_create_xxx_duplicate_returns_409(
        self, client: TestClient, mock_db: MagicMock, mock_current_user: MagicMock
    ) -> None:
        """409 重複名稱"""
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

        response = client.post(
            "/api/v1/xxxs",
            json={"field": "value"},
            headers={"Authorization": "Bearer test"},
        )

        assert response.status_code == 409
```

---

## Mock 鏈速查

| 情境 | Mock 寫法 |
|------|-----------|
| 查無資料 | `mock_db.query.return_value.filter.return_value.first.return_value = None` |
| 查有資料 | `mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(id=1, ...)` |
| 查多筆 | `mock_db.query.return_value.filter.return_value.all.return_value = [...]` |
| 分頁查詢 | `mock_db.query.return_value.filter.return_value.count.return_value = 5` |
| 軟刪除鏈 | `mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = ...` |

---

## 測試覆蓋清單

每個資源的測試應覆蓋：

**Service 層**：
- [ ] 正常建立（含 DB add/commit 驗證）
- [ ] 重複名稱/唯一鍵衝突 → AppException
- [ ] 正常取得單筆
- [ ] 取得不存在資源 → AppException（NOT_FOUND）
- [ ] 取得已軟刪除資源 → AppException（NOT_FOUND）
- [ ] 正常更新
- [ ] 更新不存在資源 → AppException
- [ ] 正常軟刪除（is_deleted=True, deleted_at, deleted_by 設定）
- [ ] 列表查詢（含分頁、排序）

**API 層**：
- [ ] 201/200 正常回應與 Response schema 欄位
- [ ] 401 未認證
- [ ] 404 資源不存在
- [ ] 409 衝突
- [ ] 422 Pydantic 驗證失敗

---

## 輸出規範

1. 若目標測試檔案已存在，用 `Edit` 在適當位置新增測試類別
2. 若測試檔案不存在，用 `Write` 建立新檔案
3. 檔案命名：`tests/test_{resource}s.py`（複數）
4. Import 順序：標準庫 → pytest → FastAPI TestClient → 專案模組
5. 每個測試方法都要有單行 docstring 說明測試目的

---

## 執行測試驗證

寫完後執行以確認通過：

```bash
.venv/Scripts/pytest tests/test_{resource}s.py -v
```
