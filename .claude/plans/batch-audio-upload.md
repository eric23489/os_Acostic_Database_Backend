# Feature: 多檔案上傳 (Batch Audio Upload)

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

### 預估時間
- 單檔上傳: ~2 分鐘 @ 10MB/s
- 並行 5 個: 800 ÷ 5 × 2 = **~5.3 小時**

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

1. `pytest tests/test_audio_batch.py -v`
2. `ruff check && ruff format`
3. 手動測試:
   ```bash
   curl -X POST /api/v1/audio/batch \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"deployment_id": 1, "audios": [...]}'
   ```

---

## 預估時間

| 步驟 | 時間 |
|------|------|
| **Phase 1: Batch API** | |
| Schema (Batch) | 15 分鐘 |
| Service 輔助方法 | 15 分鐘 |
| Service 主方法 | 25 分鐘 |
| API Endpoint (batch) | 10 分鐘 |
| 測試 (18 案例) | 45 分鐘 |
| **Phase 2: Multipart Upload** | |
| Schema (Multipart) | 15 分鐘 |
| API Endpoints (4 個) | 30 分鐘 |
| 測試 (12 案例) | 30 分鐘 |
| **整合測試 + Ruff** | 15 分鐘 |
| **總計** | **~3.5 小時** |

---

## 實作順序建議

1. **Phase 1**: 先完成 Batch API，可用簡單 PUT 測試
2. **Phase 2**: 再加入 Multipart Upload，支援大檔案
