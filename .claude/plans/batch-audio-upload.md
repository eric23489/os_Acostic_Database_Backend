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
| `app/schemas/upload_job.py` | 移除 `FileInfo` Pydantic validator、新增 `SkippedFileInfo`、`UploadJobCreateResponse` 新增 `skipped_files`；SHA256：`PartCompleteRequest` 新增 `checksum_sha256`、`MultipartInitResponse` 新增 `checksum_algorithm` |
| `app/schemas/audio.py` | 新增 Batch Schema：`AudioBatchItem`、`AudioBatchCreateRequest`、`AudioBatchResultItem`、`AudioBatchCreateResponse`；新增 `MessageResponse` |
| `app/services/audio_service.py` | 新增 `create_audios_batch()`、`_get_existing_active_keys()`、`_get_existing_deleted_keys()` |
| `app/services/minio_service.py` | SHA256：`create_multipart_upload` 加入 `ChecksumAlgorithm="SHA256"`；`generate_part_upload_url` Params 加入 `ChecksumAlgorithm`；`complete_multipart_upload` 傳入含 `ChecksumSHA256` 的 parts |
| `app/services/upload_job_service.py` | `create_job()` per-file 驗證、`cancel_job()` 清理；`complete_task()` 實作；IDOR 防護；MinIO/DB 一致性；SHA256：`complete_multipart` 帶入 `ChecksumSHA256` per part |
| `app/api/v1/endpoints/api_audio.py` | 新增 `POST /batch` 路由 |
| `app/api/v1/endpoints/api_audio_upload_jobs.py` | `create_upload_job` 動態 status code（201/207） |
| `tests/integration/test_audio_upload_integration.py` | 整合測試（含 invalid filename 207、SN 不存在 207、全部無效 400）；SHA256：上傳各 part 加入 `x-amz-checksum-sha256` header |
| `tests/test_audio.py` | 20 個單元測試（含 `TestGetTaskIDOR`） |

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
│  2. 建立 UploadJob，取得 task_id 列表                        │
│     → POST /audio-upload-jobs/                              │
│                    ↓                                        │
│  3. 並行上傳 3-5 個檔案 (Multipart Upload)                   │
│     → 前端追蹤每個檔案進度                                   │
│     → 完成一個，開始下一個                                   │
│                    ↓                                        │
│  4. 全部完成，顯示總結報告                                   │
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
```
- 檔案直接上傳 MinIO，不經過後端
- 後端只處理 URL 生成和 metadata 記錄

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
     │                    │ create_multipart_upload (ChecksumAlgorithm=SHA256)
     │                    │ ──────────────────>│
     │                    │ <──────────────────│
     │    {upload_id, total_parts, part_size, checksum_algorithm}
     │ <──────────────────│                    │
     │                    │                    │
     │ 3. POST /{job_id}/tasks/{task_id}/multipart/urls
     │    {part_numbers: [1,2,3,4,5]}          │
     │ ──────────────────>│                    │
     │    {parts: [{part_number, presigned_url}, ...]}
     │ <──────────────────│                    │
     │                    │                    │
     │ ═══════════════════════════════════════════════════════
     │        對每個 Part 重複以下步驟
     │ ═══════════════════════════════════════════════════════
     │                    │                    │
     │ 4. PUT presigned_url (上傳 Part)        │
     │    Header: x-amz-checksum-sha256: {base64_sha256}
     │ ───────────────────────────────────────>│
     │    (Response Header: ETag)              │
     │    MinIO server-side 驗證 SHA256        │
     │ <───────────────────────────────────────│
     │                    │                    │
     │ 5. POST /{job_id}/tasks/{task_id}/multipart/part-complete
     │    {part_number, etag, checksum_sha256} │
     │ ──────────────────>│                    │
     │    {"status": "ok"}│                    │
     │ <──────────────────│                    │
     │                    │                    │
     │ ═══════════════════════════════════════════════════════
     │        所有 Parts 完成後
     │ ═══════════════════════════════════════════════════════
     │                    │                    │
     │ 6. POST /{job_id}/tasks/{task_id}/multipart/complete
     │    {parts: [{part_number, etag, checksum_sha256}, ...]}
     │ ──────────────────>│                    │
     │                    │ complete_multipart_upload (含 ChecksumSHA256)
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
| 4 | PUT | `{presigned_url}` (直接傳 MinIO) | 上傳單一 Part，需帶 SHA256 header |
| 5 | POST | `/{job_id}/tasks/{task_id}/multipart/part-complete` | 回報 Part 完成 + ETag + SHA256 |
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

---

## Request/Response 範例

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
    }
  ],
  "skipped_files": []
}

// Response (207 Multi-Status，部分跳過)
{
  "job_id": "job_abc123",
  "total_files": 1,
  "tasks": [...],
  "skipped_files": [
    {"name": "bad_file.wav", "reason": "Invalid filename format"},
    {"name": "9999.240611130000.wav", "reason": "Recorder SN '9999' not found in system"}
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
  "part_size": 104857600,
  "checksum_algorithm": "SHA256"
}
```

#### Step 3: 取得 Part URLs
```json
// POST /api/v1/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls
// Request
{"part_numbers": [1, 2, 3, 4, 5]}

// Response
{
  "parts": [
    {"part_number": 1, "presigned_url": "https://minio/...?partNumber=1&..."},
    {"part_number": 2, "presigned_url": "https://minio/...?partNumber=2&..."}
  ]
}
```

#### Step 5: 回報 Part 完成
```json
// POST /api/v1/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete
// Request
{
  "part_number": 1,
  "etag": "\"d41d8cd98f00b204e9800998ecf8427e\"",
  "checksum_sha256": "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="
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
    {
      "part_number": 1,
      "etag": "\"abc...\"",
      "checksum_sha256": "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="
    },
    {
      "part_number": 2,
      "etag": "\"def...\"",
      "checksum_sha256": "RBNvo1WzZ4oRRq0W9+hknpT7T8If536DEMBg9hyq/4o="
    }
  ]
}

// Response
{"status": "ok"}
```

---

## 路徑 B：AudioBatch API 設計

### Schemas

```python
class AudioBatchItem(BaseModel):
    file_name: str
    object_key: str
    file_format: str | None = "wav"
    file_size: int | None = None
    checksum: str | None = None
    record_time: datetime | None = None
    record_duration: int | None = None
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

class AudioBatchResultItem(BaseModel):
    file_name: str
    object_key: str
    status: Literal["created", "skipped", "failed"]
    audio_id: int | None = None   # created 時必填
    reason: str | None = None     # skipped/failed 時必填

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

## SHA256 Checksum 驗證

利用 MinIO 內建 `ChecksumAlgorithm` 在 server-side 驗證每個 part 的完整性，防止傳輸損毀。

### 驗證層次

| 層次 | 驗證方式 | 何時執行 |
|------|---------|---------|
| Part 上傳 | MinIO 比對 `x-amz-checksum-sha256` vs 實際內容 | PUT part 時（MinIO 自動） |
| 完成上傳 | MinIO 比對傳入的 `ChecksumSHA256` per part | `complete_multipart_upload` 時 |

### 前端上傳每個 part 的步驟

```python
import hashlib, base64

chunk = file_bytes[start:end]
sha256 = base64.b64encode(hashlib.sha256(chunk).digest()).decode()

# 上傳 part
httpx.put(
    presigned_url,
    content=chunk,
    headers={"x-amz-checksum-sha256": sha256},
)

# 回報 part 完成
api.post(".../multipart/part-complete", json={
    "part_number": i,
    "etag": etag,
    "checksum_sha256": sha256,
})
```

### 後端修改摘要

**`minio_service.py`**：
- `create_multipart_upload` → 加入 `ChecksumAlgorithm="SHA256"`
- `generate_part_upload_url` → Params 加入 `ChecksumAlgorithm="SHA256"`
- `complete_multipart_upload` → parts 格式加入 `ChecksumSHA256` per part

**`schemas/upload_job.py`**：
- `MultipartInitResponse.checksum_algorithm: str = "SHA256"` （通知前端）
- `PartCompleteRequest.checksum_sha256: str | None = None` （暫時選填）

**`upload_job_service.py`**：
- `complete_multipart` → 組裝帶 `ChecksumSHA256` 的 parts 列表傳給 minio

### 錯誤行為

| 情境 | 錯誤來源 | 客戶端行為 |
|------|---------|----------|
| SHA256 不符 | MinIO 直接回 4xx 給 PUT 請求 | 前端重試 part 上傳 |
| `complete` 時 checksum 不符 | MinIO 拒絕合併 → ClientError | 後端回 502（現有處理） |

---

## 設計決策

### SN 驗證與 create_job per-file skip 邏輯

`create_job` 對每個檔案獨立驗證，失敗加入 `skipped_files`，不中斷整批：

| 驗證步驟 | 失敗 skip 原因 |
|---------|--------------|
| 檔名格式 (`{sn}.{YYMMDDHHmmss}.{ext}`) | `"Invalid filename format"` |
| Recorder SN 存在於 RecorderInfo | `"Recorder SN not found"` |
| object_key 未被活躍記錄占用 | `"Already exists"` |
| object_key 未被軟刪除記錄占用 | `"Reserved by deleted record"` |

全部 skip → 整批 400。

### 上傳中斷處理

**情境 A：斷點續傳（前端仍有 job_id）**
1. `GET /{job_id}` → 取得各 task status
2. PENDING → 正常走完 init → upload → complete
3. MULTIPART_INIT / UPLOADING → `GET .../progress` 取得 remaining_parts → 繼續上傳

後端已完備，無需修改。

**情境 B：重頭來過**
1. `POST /{job_id}/cancel` → abort MinIO parts、軟刪除 AudioInfo、Job 標記 CANCELLED
2. `DELETE /audio/{id}/permanent` (Admin) → Hard delete 釋放 object_key
3. `POST /audio-upload-jobs/` → 重新建立任務
