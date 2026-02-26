# 計畫：後端 API 列表端點改善

## 目標
根據前端需求，改善後端 API 列表端點，包含三項主要改動：
1. 必填參數改選填
2. 分頁元數據回傳
3. 伺服器端搜尋/篩選/排序

---

## Phase 1: 基礎設施建立

### 1.1 新建分頁 Schema
**檔案**: `app/schemas/pagination.py`

```python
from enum import Enum
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., description="符合條件的總筆數")
    skip: int = Field(..., description="跳過的筆數")
    limit: int = Field(..., description="每頁筆數上限")
```

### 1.2 新建查詢工具函式
**檔案**: `app/utils/query.py`

- `apply_search(query, model, fields, search)` - ILIKE 搜尋
- `apply_sorting(query, model, sort_by, order, allowed_fields)` - 排序 (含白名單驗證)
- `paginate(query, skip, limit)` - 分頁並回傳 (items, total)

---

## Phase 2: Service 層重構

### 2.1 回傳結構變更
所有 `get_xxx` 方法改為回傳 `tuple[list[Model], int]` (items, total)

### 2.2 修改順序與檔案

| 順序 | Service 檔案 | 方法 | 新增參數 |
|------|-------------|------|---------|
| 1 | `project_service.py` | `get_projects()` | search, is_finished, sort_by, order |
| 2 | `point_service.py` | `get_points()` | project_id 改選填, search, sort_by, order |
| 3 | `deployment_service.py` | `get_deployments()` | point_id 改選填, status, sort_by, order |
| 4 | `recorder_service.py` | `get_recorders()` | search, status, sort_by, order |
| 5 | `audio_service.py` | `get_audios()` | search, sort_by, order |
| 6 | `user_service.py` | `get_users()` | search, role, is_active, sort_by, order |

### 2.3 搜尋/篩選欄位對應

| 資源 | 搜尋欄位 | 篩選欄位 | 排序欄位 |
|------|----------|----------|----------|
| Projects | name, name_zh, area, owner, contractor | is_finished | name, created_at, start_time |
| Points | name, description | project_id | name, created_at |
| Deployments | - | point_id, status | phase, created_at, deploy_time, return_time |
| Recorders | brand, model, sn, owner | status | brand, model, sn, created_at |
| Audio | file_name, target | deployment_id | file_name, record_time, file_size, created_at |
| Users | full_name, email | role, is_active | email, created_at |

---

## Phase 3: API 層修改

### 3.1 修改順序與檔案

| 順序 | API 檔案 | response_model 變更 |
|------|---------|-------------------|
| 1 | `api_projects.py` | `List[ProjectResponse]` → `PaginatedResponse[ProjectResponse]` |
| 2 | `api_points.py` | `List[PointResponse]` → `PaginatedResponse[PointResponse]` |
| 3 | `api_deployments.py` | `List[DeploymentResponse]` → `PaginatedResponse[DeploymentResponse]` |
| 4 | `api_recorders.py` | `List[RecorderResponse]` → `PaginatedResponse[RecorderResponse]` |
| 5 | `api_audio.py` | `list[AudioResponse]` → `PaginatedResponse[AudioResponse]` |
| 6 | `api_users.py` | `list[UserResponse]` → `PaginatedResponse[UserResponse]` |

### 3.2 API 參數範例

**Projects**:
```
GET /api/v1/projects/?search=台電&is_finished=false&sort_by=created_at&order=desc&skip=0&limit=20
```

**Points** (project_id 改選填):
```
GET /api/v1/points/?project_id=1&search=A01&sort_by=name&order=asc&skip=0&limit=20
GET /api/v1/points/?skip=0&limit=100  # 不傳 project_id 回傳所有
```

**Deployments** (point_id 改選填):
```
GET /api/v1/deployments/?point_id=1&status=under-monitoring&sort_by=deploy_time&order=desc
GET /api/v1/deployments/?skip=0&limit=100  # 不傳 point_id 回傳所有
```

---

## Phase 4: 測試更新

### 4.1 需更新的測試檔案
- `tests/test_projects.py`
- `tests/test_points.py`
- `tests/test_deployments.py`
- `tests/test_recorders.py`
- `tests/test_audio.py`
- `tests/test_users.py`

### 4.2 測試重點
- 驗證回應結構包含 `items`, `total`, `skip`, `limit`
- 驗證搜尋/篩選/排序功能
- 驗證 project_id/point_id 選填時的行為

---

## 關鍵檔案清單

### 新建檔案
- `app/schemas/pagination.py`
- `app/utils/query.py`

### 修改檔案
| 層級 | 檔案路徑 |
|------|---------|
| Schema | `app/schemas/__init__.py` (匯出 PaginatedResponse) |
| Service | `app/services/project_service.py` |
| Service | `app/services/point_service.py` |
| Service | `app/services/deployment_service.py` |
| Service | `app/services/recorder_service.py` |
| Service | `app/services/audio_service.py` |
| Service | `app/services/user_service.py` |
| API | `app/api/v1/endpoints/api_projects.py` |
| API | `app/api/v1/endpoints/api_points.py` |
| API | `app/api/v1/endpoints/api_deployments.py` |
| API | `app/api/v1/endpoints/api_recorders.py` |
| API | `app/api/v1/endpoints/api_audio.py` |
| API | `app/api/v1/endpoints/api_users.py` |

---

## 風險與注意事項

1. **破壞性變更**: #2 分頁元數據會改變回應格式，需與前端同步部署
2. **效能**: `count()` 會增加一次 DB 查詢，大表需觀察
3. **排序白名單**: 必須驗證 sort_by 參數防止 SQL Injection
4. **搜尋效能**: ILIKE 在大量資料時較慢，未來可考慮 GIN 索引

---

## 驗證方式

1. 執行 `pytest` 確保所有測試通過
2. 手動測試各端點的分頁、搜尋、篩選、排序功能
3. 使用 Swagger UI (`/docs`) 驗證 API 文件正確顯示新參數

---

# 自定義 Error Code 實作（已完成）

## 目標

將全專案 63 個 `HTTPException(detail="...")` 字串錯誤統一為機器可讀的 `AppException` 系統，前端改用 `error_code` 決定行為，`message` 僅用於顯示。

## 統一回應格式

```json
{ "error_code": "PROJECT_NOT_FOUND", "message": "Project not found", "detail": null }
```

422 驗證錯誤：
```json
{ "error_code": "VALIDATION_ERROR", "message": "Request validation failed", "detail": [{"field": "files.0.name", "message": "Invalid filename format"}] }
```

## 新增/修改檔案

### 基礎設施

| 檔案 | 操作 |
|------|------|
| `app/core/exceptions.py` | 新增：`AppException` frozen dataclass + ~50 個 error code 常數 |
| `app/schemas/common.py` | 新增：`ErrorResponse` Pydantic schema |
| `app/main.py` | 修改：註冊 `AppException` 與 `RequestValidationError` exception handler |

### Service / Core 遷移

| 檔案 | 遷移的 error code 前綴 |
|------|----------------------|
| `app/core/auth.py` | AUTH_* |
| `app/services/project_service.py` | PROJECT_* |
| `app/services/point_service.py` | POINT_* |
| `app/services/deployment_service.py` | DEPLOYMENT_* |
| `app/services/audio_service.py` | AUDIO_* |
| `app/services/upload_job_service.py` | UPLOAD_*, MINIO_* |
| `app/services/recorder_service.py` | RECORDER_*（動態訊息的 HTTPException 保留） |
| `app/services/user_service.py` | USER_* |
| `app/services/password_reset_service.py` | PASSWORD_RESET_* |
| `app/services/oauth_service.py` | OAUTH_*（unlink_no_password 的 HTTPException 保留） |
| `app/api/v1/endpoints/api_projects.py` | PERMISSION_ADMIN_REQUIRED, PERMISSION_RESTORE_DENIED, PROJECT_NOT_FOUND |
| `app/api/v1/endpoints/api_audio.py` | 對應 AUDIO_* |
| `app/api/v1/endpoints/api_users.py` | AUTH_INCORRECT_CREDENTIALS, PERMISSION_DENIED |
| `app/api/v1/endpoints/api_recorders.py` | RECORDER_NOT_FOUND, PERMISSION_RESTORE_DENIED, PERMISSION_ADMIN_REQUIRED |

### 測試同步更新

| 檔案 | 主要變更 |
|------|---------|
| `tests/test_soft_delete.py` | mock side_effect → AppException 常數；`["detail"]` → `["message"]` |
| `tests/test_hard_delete.py` | 單元測試 AppException；`["detail"]` → `["message"]`（動態 HTTPException 保留） |
| `tests/test_audio.py` | mock → DEPLOYMENT_NOT_FOUND；`["detail"]` → `["message"]` |
| `tests/test_enum_validation_api.py` | 422 斷言完全重寫（`loc/msg/type` → `field/message`） |
| `tests/test_password_reset.py` | mock → AppException 常數；`["detail"]` → `["message"]` |
| `tests/test_oauth.py` | `["detail"]` → `["message"]` |
| `tests/test_recorders.py` | mock → RECORDER_IDENTIFIER_COLLISION；`["detail"]` → `["message"]` |
| `tests/integration/test_audio_upload_integration.py` | `["detail"]` → `["message"]` |
| `tests/test_soft_delete_service.py` | HTTPException → AppException；`status_code` → `http_status`；`detail` → `message` |
| `tests/test_auth.py` | HTTPException → AppException；全欄位更新 |
| `tests/test_user_service.py` | HTTPException → AppException；全欄位更新 |
| `tests/test_point_service.py` | HTTPException → AppException；全欄位更新 |
| `tests/test_deployment_service.py` | HTTPException → AppException；全欄位更新 |
| `tests/test_password_reset_service_unit.py` | HTTPException → AppException；`"deactivated"` → `"Inactive"` |
| `tests/test_project_service.py` | collision → AppException；no_name 保留 HTTPException |
| `tests/test_oauth_service_unit.py` | 7 個 → AppException；unlink_no_password 保留 HTTPException；`"deactivated"` → `"Inactive"` |

## 保留 HTTPException 的三個例外

1. `recorder_service.hard_delete_recorder`：動態 f-string 訊息（部署數量）
2. `project_service.create_project`："Either 'name' or 'name_zh' must be provided"
3. `oauth_service.unlink_google_account`：no_password 情境（"set a password before unlinking"）

## 驗證結果

- 358 個非整合測試全部通過
- ruff check 無警告（N818 和 E501 在 exceptions.py 已加 `# noqa`）
