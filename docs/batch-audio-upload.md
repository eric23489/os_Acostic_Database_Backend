# 批次音檔上傳功能文件

## 兩條路徑選擇

| 情境 | 使用路徑 |
|------|----------|
| 上傳實際檔案到 MinIO（含分段上傳） | **路徑 A：UploadJob** |
| 僅建立 AudioInfo metadata（檔案已在 MinIO） | **路徑 B：AudioBatch** |

### object_key 規則

- **路徑 A**：後端自動生成，格式 `{point_name}/{YYYY}/{MM}/Raw_Data/{filename}`
- **路徑 B**：前端提供，需自行按格式計算

---

## 路徑 A：UploadJob（分段上傳）

### API Endpoints（前綴 `/api/v1/audio-upload-jobs`）

| 步驟 | Method | Endpoint | 說明 |
|------|--------|----------|------|
| 1 | POST | `/` | 建立任務，預建 AudioInfo；201 全成功 / 207 有 skip |
| 2 | POST | `/{job_id}/tasks/{task_id}/multipart/init` | 初始化 Multipart Upload（冪等） |
| 3 | POST | `/{job_id}/tasks/{task_id}/multipart/urls` | 取得 Part presigned URLs（可分批） |
| 4 | PUT | `{presigned_url}` (直接傳 MinIO) | 上傳單一 Part，需帶 SHA256 checksum header |
| 5 | POST | `/{job_id}/tasks/{task_id}/multipart/part-complete` | 回報 Part 完成 + ETag + checksum_sha256 |
| 6 | POST | `/{job_id}/tasks/{task_id}/multipart/complete` | 完成整個檔案；WAV header 自動解析 |
| — | GET | `/{job_id}` | 查詢任務進度（含 estimated_remaining） |
| — | GET | `/{job_id}/tasks/{task_id}/progress` | 斷點續傳：查詢 completed/remaining parts |
| — | POST | `/{job_id}/cancel` | 取消任務：abort MinIO + 軟刪除 AudioInfo |

### 上傳架構

```
前端 ──presigned URL請求──> 後端 (FastAPI)
  │
  └──直接上傳 (PUT)──> MinIO (S3 API)
  │
  └──POST /multipart/complete──> 後端（完成 MinIO 並更新 DB）
```

- 檔案直接上傳 MinIO，不經過後端
- 後端只處理 URL 生成和 metadata 記錄

### 完整時序圖

```
前端                  後端                  MinIO
 │                     │                     │
 │ POST /              │                     │
 │ {deployment_id,     │                     │
 │  files: [...]}      │                     │
 │────────────────────>│                     │
 │ {job_id, tasks}     │                     │
 │<────────────────────│                     │
 │                     │                     │
 │ ═══════ 對每個檔案重複（並行 3-5 個）═══════
 │                     │                     │
 │ POST /multipart/init│                     │
 │────────────────────>│ create_multipart    │
 │                     │────────────────────>│
 │ {upload_id,         │<────────────────────│
 │  total_parts,       │                     │
 │  part_size}         │                     │
 │<────────────────────│                     │
 │                     │                     │
 │ POST /multipart/urls│                     │
 │ {part_numbers:[...]}│                     │
 │────────────────────>│                     │
 │ {parts:[presigned]} │                     │
 │<────────────────────│                     │
 │                     │                     │
 │ ═══════ 對每個 Part 重複 ═══════
 │                     │                     │
 │ PUT presigned_url   │                     │
 │ (x-amz-checksum-sha256: {base64})         │
 │────────────────────────────────────────── >│
 │ (ETag)              │                     │
 │< ──────────────────────────────────────────│
 │                     │                     │
 │ POST /part-complete │                     │
 │ {part_number, etag, checksum_sha256}      │
 │────────────────────>│                     │
 │ {status: "ok"}      │                     │
 │<────────────────────│                     │
 │                     │                     │
 │ POST /complete      │                     │
 │ {parts: [...]}      │                     │
 │────────────────────>│ complete_multipart  │
 │                     │────────────────────>│
 │                     │<────────────────────│
 │ {status: "ok"}      │                     │
 │<────────────────────│                     │
```

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

// Response 201 (全部成功)
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

// Response 207 (部分 skip)
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
    {"part_number": 1, "etag": "\"abc...\"", "checksum_sha256": "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="},
    {"part_number": 2, "etag": "\"def...\"", "checksum_sha256": "RBNvo1WzZ4oRRq0W9+hknpT7T8If536DEMBg9hyq/4o="}
  ]
}

// Response
{"status": "ok"}
```

### 檔案名稱格式

格式：`{recorder_sn}.{YYMMDDHHmmss}[.ext]`

範例：`7505.240611130000.wav`

驗證規則：`^\d+\.\d{12}(\.\w+)?$`

- SN 必須在 RecorderInfo 中存在（否則 skip）
- 格式錯誤或 SN 不存在均回傳 207（不中斷整批）

### 斷點續傳

前端保有 `job_id` 時可恢復上傳：

```
1. GET /audio-upload-jobs/{job_id}
   → 取得各 task 的 status

2. 對每個未完成的 task：
   status = PENDING（未 init）：
     → POST multipart/init → 正常走完上傳流程

   status = MULTIPART_INIT / UPLOADING（已有部分 parts）：
     → GET .../tasks/{task_id}/progress → 取得 remaining_parts
     → POST multipart/urls（只傳 remaining_parts）
     → 上傳 → part-complete → complete
```

---

## 路徑 B：AudioBatch（僅建立 metadata）

### API Endpoints（前綴 `/api/v1/audio`）

| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/batch` | 批量建立 AudioInfo（1–100 筆）；201 全成功 / 207 有 skip/fail |

### Schema

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

### 冪等性

| 情境 | Status | 行為 |
|------|--------|------|
| object_key 不存在 | `created` | 建立新記錄 |
| object_key 已存在（活躍） | `skipped` | 回傳既有 audio_id |
| object_key 已軟刪除 | `skipped` | 名稱保留，需 hard delete 釋放 |
| 批次內重複 | `skipped` | 第一個通過，後續跳過 |
| 並行寫入衝突 | 409 Conflict | IntegrityError → 請 retry |

---

## 錯誤代碼

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

## 使用情境與規模

- **檔案數量**: ~800 個
- **檔案大小**: 1.29GB/檔（總計 ~1TB）
- **上傳方式**: Multipart Upload
- **並行數量**: 3-5 個同時上傳
- **URL 策略**: 分批取得（50-100 個/批）

### 前端上傳流程概覽

```
1. 使用者選擇 800 個檔案
               ↓
2. POST /audio-upload-jobs/
   → 取得 job_id 與 tasks
               ↓
3. 並行上傳 3-5 個檔案（Multipart Upload）
   → 完成一個，開始下一個
               ↓
4. 全部完成，顯示總結報告
   → 成功: 795 筆
   → 跳過: 5 筆（已存在 / 格式錯誤）
```

---

## 關鍵設計決策

| 決策 | 選擇 | 原因 |
|------|------|------|
| 部分成功回傳碼 | 207 Multi-Status | 避免整批失敗，前端可回報明細 |
| 並行衝突處理 | 409 + retry | IntegrityError 可在應用層捕捉 |
| MinIO 操作失敗 | 502（不繼續 DB） | 避免 DB 有記錄但 MinIO 無物件 |
| DB commit 失敗 | 500 + rollback | 保持一致性，不留孤兒記錄 |
| 取消任務 | abort MinIO + 軟刪除 AudioInfo | 釋放 MinIO parts，保留可追溯性 |
