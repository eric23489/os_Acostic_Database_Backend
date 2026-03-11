# Codebase Codemap：洋聲聲學資料庫後端

讀這份文件以快速定位程式碼，不需要掃描整個專案。

---

## 資料模型層級（級聯關係）

```
ProjectInfo (project_info)
  └── PointInfo (point_info)  [FK: project_id]
        └── DeploymentInfo (deployment_info)  [FK: point_id, recorder_id]
              └── AudioInfo (audio_info)  [FK: deployment_id]
                    └── UploadJob / UploadTask（批次上傳管理）

RecorderInfo (recorder_info)  ← 被 DeploymentInfo 引用，獨立存在
UserInfo (user_info)          ← 認證主體，與業務資料無直接 FK
```

**軟刪除欄位（所有主要 Model 都有）**：`is_deleted`, `deleted_at`, `deleted_by`
**唯一索引**：均為 partial unique index，條件為 `WHERE is_deleted = false`
**級聯刪除順序**：Audios → Deployments → Points → Projects（先子後父）

---

## 關鍵 Model 欄位速查

### RecorderInfo (`app/models/recorder.py`)
- 識別鍵：`brand + model + sn`（三欄聯合唯一）
- 狀態：`status` (RecorderStatus enum)
- 校準欄位：`measured_sensitivity`, `standard_sensitivity`, `calibration_date`
- 音訊欄位：`sensitivity`, `high_gain`, `low_gain`, `recorder_channels`, `bits`

### DeploymentInfo (`app/models/deployment.py`)
- 位置：`gps_lat_exe`, `gps_lon_exe`, `geom_exe`（PostGIS Computed）
- 唯一鍵：`(point_id, phase)` 和 `(point_id, report_start_time)`
- 關聯：`point` (PointInfo), `recorder` (RecorderInfo)

### ProjectInfo (`app/models/project.py`)
- 唯一鍵：`name`（英文）、`name_zh`（中文）各自獨立 partial unique index
- 關聯：`points` relationship（過濾 `is_deleted=False`）

---

## 認證與權限

**檔案**：`app/core/auth.py`

| Dependency | 用途 | 失敗時拋出 |
|---|---|---|
| `get_current_user` | 驗證 JWT，取得 UserInfo | `AUTH_TOKEN_INVALID` |
| `get_current_admin_user` | 確認 role == "admin" | `PERMISSION_ADMIN_REQUIRED` |

**UserRole enum**：`admin`, `user`, `guest`
**JWT tokenUrl**：`/api/v1/users/login`

---

## AppException 系統

**定義**：`app/core/exceptions.py`（frozen dataclass，所有 exception 均繼承 AppException）
**使用方式**：`raise RECORDER_NOT_FOUND()` — 注意要加括號實例化
**新增 exception 前**：必須先讀 `docs/error-list.md` 確認無重複

### 現有 Exception 分類速查

| 模組 | Exception | HTTP |
|---|---|---|
| AUTH | AUTH_TOKEN_INVALID, AUTH_USER_INACTIVE, AUTH_INCORRECT_CREDENTIALS | 401/400 |
| PERMISSION | PERMISSION_DENIED, PERMISSION_ADMIN_REQUIRED, PERMISSION_RESTORE_DENIED | 403 |
| PROJECT | PROJECT_NOT_FOUND, PROJECT_NAME_DUPLICATE, PROJECT_NAME_RESERVED, PROJECT_NAME_COLLISION | 404/400 |
| POINT | POINT_NOT_FOUND, POINT_NAME_DUPLICATE, POINT_NAME_RESERVED, POINT_NAME_COLLISION | 404/400 |
| DEPLOYMENT | DEPLOYMENT_NOT_FOUND, DEPLOYMENT_PHASE_COLLISION | 404/400 |
| AUDIO | AUDIO_NOT_FOUND, AUDIO_OBJECT_KEY_DUPLICATE, AUDIO_OBJECT_KEY_RESERVED, AUDIO_OBJECT_KEY_COLLISION, AUDIO_UPLOAD_NOT_COMPLETED, AUDIO_CONCURRENT_CONFLICT, AUDIO_DB_COMMIT_FAILED | 404/400/409/500 |
| UPLOAD | UPLOAD_JOB_NOT_FOUND, UPLOAD_TASK_NOT_FOUND, UPLOAD_MULTIPART_NOT_INIT, UPLOAD_ALL_FILES_SKIPPED | 404/400 |
| MINIO | MINIO_DELETE_FAILED, MINIO_UPLOAD_FAILED | 502 |
| RECORDER | RECORDER_NOT_FOUND, RECORDER_IDENTIFIER_RESERVED, RECORDER_IDENTIFIER_DUPLICATE, RECORDER_HAS_DEPLOYMENTS | 404/400 |
| USER | USER_NOT_FOUND, USER_EMAIL_DUPLICATE, USER_EMAIL_COLLISION, USER_PASSWORD_TOO_SHORT | 404/400 |
| PASSWORD_RESET | PASSWORD_RESET_TOKEN_INVALID, PASSWORD_RESET_TOKEN_EXPIRED | 400 |
| QUERY | QUERY_SORT_INVALID | 400 |
| SYSTEM | INTERNAL_ERROR | 500 |
| OAUTH | OAUTH_NOT_CONFIGURED, OAUTH_CODE_EXCHANGE_FAILED, OAUTH_ALREADY_LINKED, OAUTH_ACCOUNT_IN_USE, OAUTH_NOT_LINKED, OAUTH_PASSWORD_REQUIRED, OAUTH_USERINFO_FETCH_FAILED | 500/401/400/502 |

---

## 查詢工具（`app/utils/query.py`）

```python
# 搜尋（ILIKE，多欄位 OR）
apply_search(query, Model, fields=["brand", "model"], search="foo")

# 排序（白名單驗證，否則 raise QUERY_SORT_INVALID）
apply_sorting(query, Model, sort_by="created_at", order=SortOrder.DESC, allowed_fields=[...])

# 分頁（回傳 tuple[list, total]）
items, total = paginate(query, skip=0, limit=20)

# 單欄位相等過濾
apply_filter(query, Model, field="status", value="available")
```

**軟刪除過濾必須用**：`.filter(Model.is_deleted.is_(False))` 而非 `== False`

---

## Enums（`app/enums/enums.py`）

| Enum | 值 |
|---|---|
| UserRole | admin, user, guest |
| RecorderStatus | available, out-of-service, under-repair, under-calibration, broken, retired, lost, checked-out, deploying |
| DeploymentStatus | un-deployed, deploying, success, water-intrusion, lost, found |
| ProjectType | wind-farm |
| UploadStatus | pending, uploading, completed, failed |
| JobStatus | pending, processing, completed, failed, cancelled |
| TaskStatus | pending, multipart-init, uploading, uploaded, completed, failed |

---

## 共用 Schema（`app/schemas/common.py`）

```python
ErrorResponse       # error_code, message, detail
HealthResponse      # status, db, minio
MessageResponse     # message
```

**分頁 Schema**：`app/schemas/pagination.py` — `SortOrder` (asc/desc)

---

## Router 規則

**聚合點**：`app/api/v1/api.py`（新增 router 時在此 include）
**Router 只做**：接收請求、呼叫 service、回傳 schema
**Router 不做**：業務邏輯、try-catch、直接查 DB

---

## 測試模式（`tests/conftest.py`）

```python
# 三個共用 fixture
mock_db          # MagicMock()，取代 SQLAlchemy session
mock_current_user  # MagicMock，role=admin，id=1
client           # TestClient，已 override get_db / get_current_user / get_current_admin_user
```

**單元測試**：TestClient + MagicMock，不需要真實 DB
**整合測試**：`tests/integration/`，需要實際 DB（CI 排除：`pytest --ignore=tests/integration`）

---

## 檔案速查表

| 需求 | 檔案 |
|---|---|
| 新增 API endpoint | `app/api/v1/endpoints/api_xxx.py` + `app/api/v1/api.py` |
| 業務邏輯 | `app/services/xxx_service.py` |
| DB Model | `app/models/xxx.py` |
| Request/Response schema | `app/schemas/xxx.py` |
| 新增 exception | `app/core/exceptions.py` + `docs/error-list.md` |
| Enum 定義 | `app/enums/enums.py` |
| 環境變數 | `app/core/config.py` (pydantic-settings) |
| DB session | `app/db/session.py` → `get_db` dependency |
| MinIO 操作 | `app/services/minio_service.py` |
| Celery tasks | `app/tasks/audio_tasks.py` |
| 開發歷程 | `.claude/docs/changelog.md`, `.claude/docs/todo.md` |
| 錯誤清單 | `docs/error-list.md` |
| 刪除模式 | `docs/delete-patterns.md` |
