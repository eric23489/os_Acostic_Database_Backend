# Feature: 多檔案上傳 (Batch Audio Upload)

## 實作狀態：完成

兩條路徑均已實作並通過 PR review：

| 路徑 | 說明 | 狀態 |
|------|------|------|
| **路徑 A：UploadJob** | 上傳實際檔案到 MinIO（含分段上傳） | 完成 |
| **路徑 B：AudioBatch** | 僅建立 AudioInfo metadata（檔案已在 MinIO） | 完成 |

---

## 兩條路徑選擇

| 情境 | 使用路徑 |
|------|----------|
| 上傳實際檔案到 MinIO | **路徑 A：UploadJob** |
| 僅建立 AudioInfo metadata（檔案已在 MinIO） | **路徑 B：AudioBatch** |

### object_key 規則
- **路徑 A**：後端自動生成，格式 `{point_name}/{YYYY}/{MM}/Raw_Data/{filename}`
- **路徑 B**：前端提供，需自行按格式計算

---

## 修改的相關檔案

| 檔案 | 變更說明 |
|------|----------|
| `app/schemas/upload_job.py` | 移除 `FileInfo` Pydantic validator、新增 `SkippedFileInfo`、`UploadJobCreateResponse` 新增 `skipped_files` |
| `app/schemas/audio.py` | 新增 Batch Schema：`AudioBatchItem`、`AudioBatchCreateRequest`、`AudioBatchResultItem`、`AudioBatchCreateResponse`；PR#1 C5 跨欄位不變量；PR#2 新增 `MessageResponse` |
| `app/services/audio_service.py` | 新增 `create_audios_batch()`、`_get_existing_active_keys()`、`_get_existing_deleted_keys()`；PR#1 C4 IntegrityError 409；PR#2 C1 `restore_audio` 簽名（接受 `UserInfo`）、C7 `hard_delete` MinIO 失敗 502、C8 `create_audios_batch` commit guard、I1 sort bug 修正（dict index） |
| `app/services/upload_job_service.py` | `create_job()` per-file 驗證、`cancel_job()` 清理；PR#1 C1 `complete_task()`、C2 IDOR、C3 MinIO/DB 一致性；PR#2 C5 WAV header `except ClientError`、C6 `complete_task` commit guard；最終：抽取 `_estimate_remaining()` helper，`list_jobs` 補充剩餘時間估算，格式改為中文「X 小時 Y 分鐘」 |
| `app/api/v1/endpoints/api_audio.py` | 新增 `POST /batch` 路由；PR#1 C6 router 移除業務邏輯；PR#2 C1 `restore_audio` 只傳 `current_user`、C2 `hard_delete` 改用 `MessageResponse` |
| `app/api/v1/endpoints/api_audio_upload_jobs.py` | `create_upload_job` 動態 status code（201/207）；PR#1 C1/C2 所有端點傳入 `user_id` |
| `tests/integration/test_audio_upload_integration.py` | 新增：invalid filename 207、SN 不存在 207、全部無效 400 測試 |
| `tests/test_audio.py` | PR#1 C7 新增 18 測試；PR#2 C9 新增 `TestGetTaskIDOR`（總計 20 tests） |

---

## 使用情境
- **檔案數量**: ~800 個
- **檔案大小**: 1.29GB/檔 (總計 ~1TB)
- **上傳方式**: Multipart Upload
- **並行數量**: 3-5 個同時上傳
- **URL 策略**: 分批取得 (50-100 個/批)

---

## 上傳流程 (UX)

```
┌─────────────────────────────────────────────────────────────┐
│  前端上傳流程 (800 個 1.29GB 檔案)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 使用者選擇 800 個檔案                                    │
│                    ↓                                        │
│  2. 前端分批請求 presigned URLs (每批 50 個)                 │
│     → POST /audio/upload/presigned-urls                     │
│     → 取得 URL 後立即開始上傳，不等全部                      │
│                    ↓                                        │
│  3. 並行上傳 3-5 個檔案 (Multipart Upload)                   │
│     → 前端追蹤每個檔案進度                                   │
│     → 完成一個，開始下一個                                   │
│                    ↓                                        │
│  4. 每 50 個上傳完成，呼叫 POST /audio/batch                 │
│     → 建立 AudioInfo 記錄                                   │
│     → 回傳 created/skipped 統計                             │
│                    ↓                                        │
│  5. 全部完成，顯示總結報告                                   │
│     → 成功: 795 筆                                          │
│     → 跳過: 5 筆 (已存在)                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 上傳架構
```
前端 ──presigned URL請求──→ 後端 (FastAPI)
  │
  └──直接上傳 (PUT)──→ MinIO (S3 API)
  │
  └──POST /audio/batch──→ 後端 (建立 DB 記錄)
```
- 檔案直接上傳 MinIO，不經過後端
- 後端只處理 URL 生成和 metadata 記錄

### 進度顯示
- 前端可追蹤每個檔案的 Multipart Upload 進度
- 整體進度 = 已完成檔案數 / 總檔案數
- 建議 UI: 整體進度 + 當前上傳檔案進度 + 預估剩餘時間

### 關閉網頁處理
- **Phase 1**: 關閉會中斷上傳
- **Phase 2 (可選)**: 前端斷點續傳 (localStorage 記錄已完成檔案)

---

## 前端與後端溝通流程

### 完整上傳流程時序圖

```
┌─────────┐          ┌─────────┐          ┌─────────┐
│  前端   │          │  後端   │          │  MinIO  │
└────┬────┘          └────┬────┘          └────┬────┘
     │                    │                    │
     │ 1. POST /audio-upload-jobs/             │
     │    {deployment_id, files: [...]}        │
     │ ──────────────────>│                    │
     │                    │                    │
     │    {job_id, tasks: [{task_id, audio_id, object_key}, ...]}
     │ <──────────────────│                    │
     │                    │                    │
     │ ═══════════════════════════════════════════════════════
     │        對每個檔案重複以下步驟 (並行 3-5 個)
     │ ═══════════════════════════════════════════════════════
     │                    │                    │
     │ 2. POST /{job_id}/tasks/{task_id}/multipart/init
     │ ──────────────────>│                    │
     │                    │ create_multipart_upload
     │                    │ ──────────────────>│
     │                    │ <──────────────────│
     │    {upload_id, total_parts, part_size}  │
     │ <──────────────────│                    │
     │                    │                    │
     │ 3. POST /{job_id}/tasks/{task_id}/multipart/urls
     │    {part_numbers: [1,2,3,4,5]}          │
     │ ──────────────────>│                    │
     │                    │ generate_presigned_url (per part)
     │                    │ ──────────────────>│
     │    {parts: [{part_number, presigned_url}, ...]}
     │ <──────────────────│                    │
     │                    │                    │
     │ ═══════════════════════════════════════════════════════
     │        對每個 Part 重複以下步驟
     │ ═══════════════════════════════════════════════════════
     │                    │                    │
     │ 4. PUT presigned_url (上傳 Part)        │
     │ ───────────────────────────────────────>│
     │    (Response Header: ETag)              │
     │ <───────────────────────────────────────│
     │                    │                    │
     │ 5. POST /{job_id}/tasks/{task_id}/multipart/part-complete
     │    {part_number, etag}                  │
     │ ──────────────────>│                    │
     │    {"status": "ok"}│                    │
     │ <──────────────────│                    │
     │                    │                    │
     │ ═══════════════════════════════════════════════════════
     │        所有 Parts 完成後
     │ ═══════════════════════════════════════════════════════
     │                    │                    │
     │ 6. POST /{job_id}/tasks/{task_id}/multipart/complete
     │    {parts: [{part_number, etag}, ...]}  │
     │ ──────────────────>│                    │
     │                    │ complete_multipart_upload
     │                    │ ──────────────────>│
     │                    │ <──────────────────│
     │    {"status": "ok"}│                    │
     │ <──────────────────│                    │
     │                    │                    │
     │ ═══════════════════════════════════════════════════════
     │        (可選) 查詢進度 / 斷點續傳
     │ ═══════════════════════════════════════════════════════
     │                    │                    │
     │ 7. GET /{job_id}   │                    │
     │ ──────────────────>│                    │
     │    {job_id, status, progress, tasks}    │
     │ <──────────────────│                    │
     │                    │                    │
     │ 8. GET /{job_id}/tasks/{task_id}/progress
     │ ──────────────────>│                    │
     │    {completed_parts, remaining_parts}   │
     │ <──────────────────│                    │
     │                    │                    │
```

### 路徑 A：API Endpoints（/api/v1/audio-upload-jobs 前綴）

| 步驟 | Method | Endpoint | 用途 |
|------|--------|----------|------|
| 1 | POST | `/` | 建立任務，預建 AudioInfo (status=PENDING)；201 全成功 / 207 有 skip |
| 2 | POST | `/{job_id}/tasks/{task_id}/multipart/init` | 初始化 Multipart Upload；冪等 |
| 3 | POST | `/{job_id}/tasks/{task_id}/multipart/urls` | 取得 Part presigned URLs（可分批） |
| 4 | PUT | `{presigned_url}` (直接傳 MinIO) | 上傳單一 Part，取得 ETag |
| 5 | POST | `/{job_id}/tasks/{task_id}/multipart/part-complete` | 回報 Part 完成 + ETag |
| 6 | POST | `/{job_id}/tasks/{task_id}/multipart/complete` | 完成整個檔案；WAV header 自動解析 |
| — | GET | `/{job_id}` | 查詢任務進度（含 estimated_remaining） |
| — | GET | `/{job_id}/tasks/{task_id}/progress` | 斷點續傳：查詢 completed/remaining parts |
| — | POST | `/{job_id}/cancel` | 取消任務：abort MinIO + 軟刪除 AudioInfo |

### 路徑 B：API Endpoints（/api/v1/audio 前綴）

| Method | Endpoint | 用途 |
|--------|----------|------|
| POST | `/batch` | 批量建立 AudioInfo（1–100 筆）；201 全成功 / 207 有 skip/fail |

### 錯誤代碼

| Code | 路徑 A | 路徑 B |
|------|--------|--------|
| 201 | 全部成功 | 全部成功 |
| 207 | 有 skipped_files | 有 skipped/failed results |
| 400 | 全部 skip（無有效檔案） | — |
| 404 | deployment 不存在 | deployment 不存在 |
| 409 | — | 並行寫入衝突（retry） |
| 422 | 格式驗證失敗 | audios 空列表 / 超過 100 筆 |
| 500 | DB commit 失敗 | DB commit 失敗 |
| 502 | MinIO complete 失敗 | — |

### Request/Response 範例

#### Step 1: 建立上傳任務
```json
// POST /api/v1/audio-upload-jobs/
// Request
{
  "deployment_id": 123,
  "priority": 5,
  "files": [
    {"name": "7505.240611130000.wav", "size": 1386217472},
    {"name": "7505.240611140000.wav", "size": 1386217472}
  ]
}

// Response (201 Created)
{
  "job_id": "job_abc123",
  "deployment_id": 123,
  "status": "pending",
  "total_files": 2,
  "tasks": [
    {
      "task_id": "task_001",
      "audio_id": 456,
      "file_name": "7505.240611130000.wav",
      "object_key": "PointA/2024/06/Raw_Data/7505.240611130000.wav"
    },
    {
      "task_id": "task_002",
      "audio_id": 457,
      "file_name": "7505.240611140000.wav",
      "object_key": "PointA/2024/06/Raw_Data/7505.240611140000.wav"
    }
  ]
}
```

#### Step 2: 初始化 Multipart Upload
```json
// POST /api/v1/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init
// Response
{
  "upload_id": "minio_upload_xyz789",
  "total_parts": 14,
  "part_size": 104857600  // 100MB
}
```

#### Step 3: 取得 Part URLs
```json
// POST /api/v1/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls
// Request
{
  "part_numbers": [1, 2, 3, 4, 5]
}

// Response
{
  "parts": [
    {"part_number": 1, "presigned_url": "https://minio/...?partNumber=1&..."},
    {"part_number": 2, "presigned_url": "https://minio/...?partNumber=2&..."},
    ...
  ]
}
```

#### Step 5: 回報 Part 完成
```json
// POST /api/v1/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete
// Request
{
  "part_number": 1,
  "etag": "\"d41d8cd98f00b204e9800998ecf8427e\""
}

// Response
{"status": "ok"}
```

#### Step 6: 完成上傳
```json
// POST /api/v1/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete
// Request
{
  "parts": [
    {"part_number": 1, "etag": "\"abc...\""},
    {"part_number": 2, "etag": "\"def...\""},
    ...
  ]
}

// Response
{"status": "ok"}
```

---

## 多角色審查摘要

### Questioner 關鍵問題
| 問題 | 優先級 | 處理方式 |
|------|--------|----------|
| MinIO 孤兒物件 | 高 | 定期 cleanup job (未來實作) |
| object_key 存在性驗證 | 高 | 可選參數 `verify_minio` |
| 越權上傳防護 | 高 | presigned URL 已限制路徑 |
| 部分成功處理 | 中 | 207 Multi-Status |
| 批次內重複 | 中 | 第一個通過，後續 skip |

### Architect 架構決策
- **批量處理方案**: 混合方案 (批量查詢 + 批量插入)
- **DB 往返**: 3 次 vs 逐筆 200 次
- **預估延遲**: 100-300ms (100筆)
- **程式碼重構**: 抽取 `_validate_object_keys_batch()` 共用

### Backend Engineer 實作建議
- **Schema**: 新增 `AudioBatchItem` (不含 deployment_id)
- **Status Code**: 201 全成功 / 207 部分成功
- **Transaction**: 整批 commit/rollback
- **Race Condition**: IntegrityError → 409 Conflict

### Test Engineer 測試策略
- **P0**: 6 tests (基本功能、冪等性、認證)
- **P1**: 6 tests (限制、驗證、回滾)
- **P2**: 6 tests (邊界情況)
- **覆蓋率目標**: 85%+

---

## API 設計

### Endpoint: `POST /api/v1/audio/batch`

**Request**:
```python
class AudioBatchItem(BaseModel):
    """單一 Audio 資料，deployment_id 由外層提供"""
    file_name: str
    object_key: str
    file_format: str | None = "wav"
    file_size: int | None = None
    checksum: str | None = None
    record_time: datetime | None = None
    record_duration: float | None = None
    fs: int | None = None
    recorder_channel: int | None = 0
    audio_channels: int | None = 1
    target: str | None = None
    target_type: int | None = None
    meta_json: dict[str, Any] | None = None
    is_cold_storage: bool | None = False

class AudioBatchCreateRequest(BaseModel):
    deployment_id: int
    audios: list[AudioBatchItem]  # 1-100 筆

    @field_validator("audios")
    @classmethod
    def validate_batch_size(cls, v):
        if len(v) == 0:
            raise ValueError("At least 1 audio required")
        if len(v) > 100:
            raise ValueError("Maximum 100 audios per batch")
        return v
```

**Response**:
```python
class AudioBatchResultItem(BaseModel):
    file_name: str
    object_key: str
    status: Literal["created", "skipped", "failed"]
    audio_id: int | None = None
    reason: str | None = None

class AudioBatchCreateResponse(BaseModel):
    deployment_id: int
    total_count: int
    success_count: int
    skipped_count: int
    failed_count: int
    results: list[AudioBatchResultItem]
```

---

## 冪等性設計

| 情境 | Status | 行為 |
|------|--------|------|
| object_key 不存在 | `created` | 建立新記錄 |
| object_key 已存在 (活躍) | `skipped` | 回傳既有 audio_id |
| object_key 已軟刪除 | `skipped` | 名稱保留，需 hard delete 釋放 |
| 批次內重複 | `skipped` | 第一個通過，後續跳過 |

---

## Multipart Upload API (新增)

大檔案 (>100MB) 需要 Multipart Upload:

### 1. 初始化上傳
```
POST /audio/upload/multipart/init
Request:  { project_name, point_name, filename }
Response: { upload_id, bucket, key }
```

### 2. 取得 Part URLs
```
POST /audio/upload/multipart/urls
Request:  { upload_id, bucket, key, part_count }
Response: { parts: [{ part_number, presigned_url }] }
```

### 3. 完成上傳
```
POST /audio/upload/multipart/complete
Request:  { upload_id, bucket, key, parts: [{ part_number, etag }] }
Response: { success: true }
```

### 4. 取消上傳
```
POST /audio/upload/multipart/abort
Request:  { upload_id, bucket, key }
Response: { success: true }
```

---

## 修改檔案

| 檔案 | 變更 |
|------|------|
| `app/schemas/audio.py` | +7 Schema (Batch + Multipart) |
| `app/services/audio_service.py` | +4 方法: validate, get_active, get_deleted, create_batch |
| `app/api/v1/endpoints/api_audio.py` | +5 路由: batch + multipart (4個) |
| `tests/test_audio_batch.py` | +18 測試案例 |
| `tests/test_multipart_upload.py` | +12 測試案例 |

---

## 實作步驟

### Step 1: Schema (`app/schemas/audio.py`)
新增 4 個 class: AudioBatchItem, AudioBatchCreateRequest, AudioBatchResultItem, AudioBatchCreateResponse

### Step 2: Service 輔助方法 (`app/services/audio_service.py`)
```python
def _validate_deployment_exists(self, deployment_id: int) -> None:
    """驗證 deployment 存在且未軟刪除，否則 raise 404"""

def _get_existing_active_keys(self, object_keys: set[str]) -> set[str]:
    """批量查詢已存在的活躍 object_keys"""

def _get_existing_deleted_keys(self, object_keys: set[str]) -> set[str]:
    """批量查詢已軟刪除的 object_keys"""
```

### Step 3: Service 主方法 (`app/services/audio_service.py`)
```python
def create_audios_batch(
    self, deployment_id: int, audios: list[AudioBatchItem]
) -> AudioBatchCreateResponse:
    # 1. 驗證 deployment_id
    # 2. 檢查批次內重複
    # 3. 批量查詢 DB 衝突 (2 次查詢)
    # 4. 分類處理: created / skipped / failed
    # 5. db.add_all() + flush() 取得 ID
    # 6. commit() 或 rollback()
```

### Step 4: API (`app/api/v1/endpoints/api_audio.py`)
```python
@router.post("/batch", response_model=AudioBatchCreateResponse)
def create_audios_batch(
    request: AudioBatchCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = AudioService(db).create_audios_batch(
        deployment_id=request.deployment_id,
        audios=request.audios,
    )
    if result.skipped_count > 0 or result.failed_count > 0:
        response.status_code = status.HTTP_207_MULTI_STATUS
    else:
        response.status_code = status.HTTP_201_CREATED
    return result
```

### Step 5: 測試 (`tests/test_audio_batch.py`)
- P0: 成功建立、冪等性跳過、deployment 驗證、混合結果、認證
- P1: 100 筆上限、空陣列、軟刪除保留、交易回滾
- P2: 批次內重複、Unicode 檔名、大型 meta_json

---

## 驗證方式

1. `pytest tests/test_audio.py -v`
2. `ruff check && ruff format`
3. 手動測試:
   ```bash
   curl -X POST /api/v1/audio/batch \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"deployment_id": 1, "audios": [...]}'
   ```

---

## PR Review 修復記錄 (PR #16)

PR review 由 4 個 Agent 並行執行（code-reviewer、pr-test-analyzer、silent-failure-hunter、type-design-analyzer），發現 7 個 Critical issue，全部已修復。

### C1 — 未實作的佔位端點

**問題**: `complete_upload_task` 端點只回傳 `{"status": "placeholder"}`，呼叫端永遠收不到真實結果。

**修復**: 實作 `UploadJobService.complete_task(job_id, task_id, user_id, request)`：
- 冪等：已完成的 task 直接回傳 ok
- 更新 `UploadTask.status = COMPLETED`
- 更新 `AudioInfo.upload_status = COMPLETED`、`upload_completed_at`
- 更新 `UploadJob` 計數，若所有 task 完成則標記 job 為 COMPLETED

### C2 — IDOR（Insecure Direct Object Reference）

**問題**: `_get_task`、`get_job_status`、`cancel_job` 未驗證 `user_id`，任意使用者可操作其他人的 job/task。

**修復**:
- `_get_task`：JOIN `UploadJob` 並過濾 `UploadJob.user_id == user_id`，回傳 404（不回傳 403，避免洩漏資源存在）
- `get_job_status`：查詢時加入 `UploadJob.user_id == user_id` 條件
- `cancel_job`：查詢時加入 `UploadJob.user_id == user_id` 條件
- 所有 multipart 方法簽名新增 `user_id: int` 參數並傳遞

### C3 — MinIO 與 DB 操作不一致性

**問題**: `complete_multipart` 中若 MinIO 成功但 `db.commit()` 失敗，或 MinIO 失敗但繼續 commit，會造成資料與物件儲存不同步。

**修復**:
- MinIO `complete_multipart_upload` 失敗 → `ClientError` → HTTP 502（MinIO 問題，非客戶端問題）
- `db.commit()` 失敗 → `logger.critical(...)` + HTTP 500（提示用戶聯繫支援）
- 兩種失敗語義不同，分開處理

### C4 — TOCTOU 競爭條件（check-then-act）

**問題**: `create_audios_batch` 先查詢 `active_keys`，再插入，並行請求可能在查詢後插入相同 `object_key` 導致 IntegrityError 未被處理。

**修復**: `db.flush()` 包覆在 `try/except IntegrityError`：
- 失敗 → `db.rollback()` + logger.warning + HTTP 409 Conflict（"Please retry"）

### C5 — 型別不變量未強制 (AudioBatchResultItem)

**問題**: `status="created"` 時 `audio_id` 可為 `None`；`status="skipped"/"failed"` 時 `reason` 可為 `None`，下游可能產生 `None` 污染。

**修復**: 在 `AudioBatchResultItem` 新增 `@model_validator(mode="after")`：
```python
@model_validator(mode="after")
def validate_status_fields(self) -> "AudioBatchResultItem":
    if self.status == "created" and self.audio_id is None:
        raise ValueError("audio_id is required when status is 'created'")
    if self.status in ("skipped", "failed") and self.reason is None:
        raise ValueError("reason is required when status is 'skipped' or 'failed'")
    return self
```

### C6 — Router 層含業務邏輯（違反架構規範）

**問題**: `restore_audio` 端點在 router 中直接查詢 DB 取得 user role、判斷是否為 admin，違反「router 只接收請求和回傳回應」原則。

**修復**:
- `restore_audio` service 方法簽名改為 `(audio_id, current_user_id, is_admin)`，auth check 移入 service
- Router 只計算 `is_admin = current_user.role == UserRole.ADMIN.value` 後傳入
- `hard_delete_audio`：改用 `get_current_admin_user` dependency，移除 router 中的手動 admin 檢查

### C7 — 缺少型別不變量與端點測試

**問題**: C5 修復後無測試覆蓋；batch 端點關鍵路徑（201/207/409）無測試。

**修復**: 新建 `tests/test_audio.py`（18 個測試）：
- `TestAudioBatchResultItem`（7 tests）：驗證 created/skipped/failed 的欄位不變量
- `TestAudioBatchCreateRequest`（4 tests）：驗證 0/1/100/101 筆邊界
- `TestCreateAudiosBatchEndpoint`（7 tests）：201 全建立、207 部分跳過、404 deployment、422 驗證失敗、207 軟刪除鍵跳過、409 並行衝突

---

## 第二次 PR Review 修復記錄 (PR #16 Round 2)

第二次 review 由 4 個 Agent 並行執行，發現 9 個 Critical/Important issue，全部已修復。

### C1 — Router 含業務邏輯（restore_audio is_admin）

**問題**: `restore_audio` router 計算 `is_admin = current_user.role == UserRole.ADMIN.value`，業務邏輯外洩。

**修復**: `restore_audio` service 簽名改為 `(audio_id, current_user: UserInfo)`，is_admin 判斷移入 service；router 直接傳 `current_user`。

### C2 — response_model=dict

**問題**: `hard_delete_audio` 端點使用 `response_model=dict`，繞過 Pydantic 序列化與文件生成。

**修復**: 新增 `MessageResponse(message: str)` schema，`hard_delete_audio` 改用 `response_model=MessageResponse`。

### C5 — WAV header except Exception 吞噬非預期錯誤

**問題**: `complete_multipart` 中 WAV header 驗證的 `except Exception` 同時包覆 MinIO 網路呼叫與屬性存取，`recorder=None` 等程式錯誤會被靜默吞噬。

**修復**: `except ClientError` 只捕捉 MinIO 呼叫失敗；WAV 屬性存取移至 `else` 子句，程式錯誤會正確傳播。

### C6 — complete_task DB commit 未保護

**問題**: `complete_task`（簡單上傳路徑）的 `db.commit()` 無 try/except，DB 失敗後狀態不一致。

**修復**: 包覆 `try/except Exception`，失敗時 `logger.critical` + HTTP 500，與 `complete_multipart` 保持一致。

### C7 — hard_delete MinIO 失敗後繼續刪除 DB

**問題**: `hard_delete_audio` 若 MinIO 刪除失敗，原程式靜默繼續刪除 DB 記錄，造成永久孤兒物件。

**修復**: 使用 `MinioService()`，MinIO 失敗 `raise HTTPException(502)`，中止 DB 刪除。

### C8 — create_audios_batch commit 未保護

**問題**: `create_audios_batch` 的 `db.commit()` 無 try/except，flush 後取得的 ID 在 commit 失敗後無法使用。

**修復**: 包覆 `try/except Exception`，失敗時 rollback + logger.error + HTTP 500。

### C9 — 缺少 _get_task IDOR 測試

**問題**: `_get_task` 的 IDOR 防護（回傳 404 而非 403）無測試覆蓋。

**修復**: 新增 `TestGetTaskIDOR`：驗證錯誤使用者 → 404、正確使用者 → task 物件。

### I1 — 批次內重複 object_key 排序錯誤

**問題**: `create_audios_batch` 使用 `results.sort(key=lambda r: object_keys.index(r.object_key))`，`list.index()` 永遠回傳第一個出現位置，導致重複 key 的後續項目排序錯誤。

**修復**: 改用 `indexed_results: dict[int, AudioBatchResultItem]` 以原始 loop index 為 key，最後以 `[indexed_results[i] for i in range(len(request.audios))]` 重建順序。

---

## 實作順序建議

1. **Phase 1**: 先完成 Batch API，可用簡單 PUT 測試
2. **Phase 2**: 再加入 Multipart Upload，支援大檔案

---

## 設計確認：SN 驗證與部分成功（207）

### 背景
確認兩個設計問題後的修改方向：
1. Recorder SN 需對應 RecorderInfo（不存在則 skip）
2. 批次中含有錯誤 name 改為部分成功，不中斷整批

### `app/schemas/upload_job.py` 修改

**移除 `FileInfo` 的 Pydantic validator**（驗證移到 service 層）：
```python
# 移除這段
@field_validator("name")
@classmethod
def validate_filename_format(cls, v: str) -> str:
    ...
```

**新增 `SkippedFileInfo`**：
```python
class SkippedFileInfo(BaseModel):
    name: str
    reason: str
```

**`UploadJobCreateResponse` 新增 `skipped_files`**：
```python
class UploadJobCreateResponse(BaseModel):
    job_id: str
    deployment_id: int
    status: str
    total_files: int
    tasks: list[UploadTaskInfo]
    skipped_files: list[SkippedFileInfo] = []  # 新增
```

### `app/services/upload_job_service.py` - `create_job()` 新流程

```
舊流程（全有或全無）:
  1. 驗證 deployment
  2. 生成所有 object_keys
  3. 批量查重（任一重複 → 400 整批失敗）
  4. 批量建立 AudioInfo

新流程（per-file skip）:
  1. 驗證 deployment（不變，仍整批失敗）
  2. Per-file 格式驗證（try parse_audio_filename）
     - 失敗 → skipped_files（reason: "Invalid filename format"）
  3. 批量查詢 RecorderInfo.sn（WHERE sn IN (...) AND is_deleted = false）
     - SN 不在結果中 → skipped_files（reason: "Recorder SN not found"）
  4. Per-file object_key 重複檢查（查 active + deleted）
     - active 重複 → skipped_files（reason: "Already exists"）
     - deleted 佔用 → skipped_files（reason: "Reserved by deleted record"）
  5. 若 final_files 為空 → raise HTTPException 400（"All files skipped"）
  6. 批量建立 AudioInfo、UploadJob、UploadTask（僅 final_files）
  7. 回傳含 skipped_files 的 response
```

SN 批量查詢（步驟 3）：
```python
from app.models.recorder import RecorderInfo

valid_sns = {parsed.recorder_sn for _, parsed in files_with_parsed}
existing_sns = {
    r[0]
    for r in self.db.query(RecorderInfo.sn)
    .filter(RecorderInfo.sn.in_(valid_sns), RecorderInfo.is_deleted.is_(False))
    .all()
}
```

### `app/api/v1/endpoints/api_audio_upload_jobs.py` - 動態 status code

```python
from fastapi import APIRouter, Depends, Response, status  # 新增 Response

@router.post("/", response_model=UploadJobCreateResponse)  # 移除 status_code=201
def create_upload_job(
    request: UploadJobCreateRequest,
    response: Response,  # 新增
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = UploadJobService(db).create_job(request, current_user.id)
    response.status_code = (
        status.HTTP_207_MULTI_STATUS if result.skipped_files else status.HTTP_201_CREATED
    )
    return result
```

### Response 範例

全部成功（201）：
```json
{"job_id": "...", "total_files": 2, "tasks": [...], "skipped_files": []}
```

部分成功（207）：
```json
{
  "job_id": "...",
  "total_files": 1,
  "tasks": [...],
  "skipped_files": [
    {"name": "bad_file.wav", "reason": "Invalid filename format: expected {sn}.{YYMMDDHHMMSS}.{ext}"},
    {"name": "9999.240611130000.wav", "reason": "Recorder SN '9999' not found in system"}
  ]
}
```

全部 skip（400）：
```json
{"detail": "All files skipped: no valid files to upload"}
```

---

## 設計確認：上傳中斷重新上傳

### 兩種中斷情境

#### 情境 A：斷點續傳（前端仍有 job_id）
後端 API 已完整，前端只需實作此流程：
```
1. GET /audio-upload-jobs/{job_id}
   → 取得各 task 的 status

2. 對每個未完成的 task：

   status = PENDING（尚未 init）:
     → POST multipart/init → 正常走完上傳流程

   status = MULTIPART_INIT / UPLOADING（已有部分 parts）:
     → GET .../tasks/{task_id}/progress → 取得 remaining_parts
     → POST multipart/urls（只傳 remaining_parts）
     → 上傳 → part-complete → complete
```

**後端不需修改，此路徑已完備。**

#### 情境 B：完全重頭來過
```
1. POST /audio-upload-jobs/{job_id}/cancel   （補強後）
   → 中止所有 MinIO multipart parts
   → 軟刪除所有關聯 AudioInfo
   → Job 標記 CANCELLED

2. DELETE /api/v1/audio/{audio_id}/permanent   （Admin）
   → Hard delete AudioInfo，釋放 object_key 名稱

3. POST /audio-upload-jobs/
   → 重新建立任務，正常進行
```

### 現有缺口：`cancel_job` 不完整

目前 `cancel_job()`（`upload_job_service.py:270`）只改 job 狀態，未處理：
- MinIO 孤兒 parts（已初始化的 multipart upload 未 abort）
- AudioInfo 仍是 `upload_status=pending`，`is_deleted=False`，導致重傳被 400 擋住

### `app/services/upload_job_service.py` - `cancel_job()` 補強

函式簽名新增 `user_id`：
```python
def cancel_job(self, job_id: str, user_id: int) -> None:
    job = ...
    if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
        return

    bucket = job.deployment.point.project.name

    for task in job.tasks:
        # 1. Abort MinIO multipart（若已初始化）
        if task.upload_id:
            self.minio.abort_multipart_upload(bucket, task.object_key, task.upload_id)

        # 2. 軟刪除 AudioInfo
        audio = task.audio
        if audio and not audio.is_deleted:
            audio.is_deleted = True
            audio.deleted_at = datetime.now(UTC)
            audio.deleted_by = user_id

        # 3. Task 標記失敗
        task.status = TaskStatus.FAILED

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(UTC)
    self.db.commit()
```

### `app/api/v1/endpoints/api_audio_upload_jobs.py` - cancel endpoint 補強

```python
@router.post("/{job_id}/cancel")
def cancel_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    UploadJobService(db).cancel_job(job_id, current_user.id)  # 傳入 user_id
    return {"status": "cancelled"}
```
