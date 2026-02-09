# Feature: Batch Upload

## 目標
實作批量上傳 .wav 音檔功能，使用者上傳檔案後自動建立 AudioInfo 記錄。

## 需求摘要
- **前置條件**: 使用者已建立 Project → Point → Deployment
- **上傳規模**: ~1000 個檔案，每個 ~1.29GB (總計 ~1.29TB)
- **檔案類型**: .wav
- **MinIO 路徑格式**: `{Project}/{Point_Name}/{YYYY}/{MM}/Raw_Data/{Filename}`

---

## 多角色審查摘要

### Questioner 提出的關鍵問題
1. **部分成功時的 UX**: 90/100 成功時如何重試失敗的 10 個？
2. **MinIO/DB 不一致**: 上傳成功但 metadata 建立失敗，產生孤兒檔案
3. **並發衝突**: 上傳期間 Deployment 被刪除
4. **時間限制**: presigned URL 1小時有效期 vs 大檔案上傳
5. **權限驗證**: 缺少 Deployment 所有權檢查

### Architect 推薦方案
**方案 B (冪等批量建立) + 方案 C (前端分批) 混合**

| 方案 | 一致性 | 複雜度 | 效能 | 風險 |
|------|--------|--------|------|------|
| A. 兩階段提交 | 高 | 高 | 中 | MinIO 無 transaction |
| **B. 冪等批量建立** | 中 | 中 | 高 | 需 orphan cleanup |
| C. 前端分批重試 | 中 | 低 | 高 | 前端複雜度 |

**推薦理由**:
- 符合專案設計哲學 ("先 MinIO 後 DB，孤兒可清理")
- 冪等性支援重試
- 實作成本最低

---

## 實作規格

### API 設計
**Endpoint**: `POST /api/v1/audio/batch`

**Request**:
```python
class AudioBatchCreateRequest(BaseModel):
    deployment_id: int
    audios: List[AudioCreate]  # 最多 20 筆/批次

    @field_validator("audios")
    def validate_batch_size(cls, v):
        if len(v) > 20:
            raise ValueError("Maximum 20 audios per batch")
        return v
```

**Response**:
```python
class AudioBatchCreateResponse(BaseModel):
    success_count: int
    failed_count: int
    skipped_count: int
    results: List[AudioBatchResultItem]

class AudioBatchResultItem(BaseModel):
    file_name: str
    object_key: str
    status: str  # "created" | "skipped" | "failed"
    audio_id: Optional[int] = None
    reason: Optional[str] = None
```

### 冪等性設計
| 情境 | Status | 行為 |
|------|--------|------|
| object_key 不存在 | `created` | 建立新記錄 |
| object_key 已存在 (未刪除) | `skipped` | 跳過，回傳既有 audio_id |
| object_key 已存在 (已軟刪除) | `failed` | 名稱保留，拒絕建立 |

### 錯誤處理
| 層級 | HTTP Status | 說明 |
|------|-------------|------|
| deployment_id 不存在 | 404 | Deployment not found or deleted |
| 超過 20 筆限制 | 422 | Pydantic 驗證失敗 |
| 部分成功/失敗 | 200 | 回傳 results 細節 |

---

## 修改檔案清單

| 檔案 | 變更 |
|------|------|
| `app/schemas/audio.py` | 新增 `AudioBatchCreateRequest`, `AudioBatchCreateResponse`, `AudioBatchResultItem` |
| `app/services/audio_service.py` | 新增 `create_audio_batch()` 方法 |
| `app/api/v1/endpoints/api_audio.py` | 新增 `POST /audio/batch` endpoint |
| `tests/test_audio_batch.py` | 新增批量上傳測試 |

---

## 實作步驟

### Step 1: Schema 定義
**檔案**: `app/schemas/audio.py`
- 新增 `AudioBatchCreateRequest`
- 新增 `AudioBatchResultItem`
- 新增 `AudioBatchCreateResponse`

### Step 2: Service 層
**檔案**: `app/services/audio_service.py`
```python
def create_audio_batch(
    self, deployment_id: int, audios: list[AudioCreate]
) -> dict[str, Any]:
    """
    批量建立 Audio 記錄，具有冪等性。

    1. 驗證 deployment_id 存在且未軟刪除
    2. 逐筆處理：
       - object_key 已存在 (active) → 跳過
       - object_key 已存在 (deleted) → 失敗
       - 成功 → 建立記錄
    3. 使用 flush() 取得 ID，最後 commit()
    """
```

### Step 3: API 端點
**檔案**: `app/api/v1/endpoints/api_audio.py`
```python
@router.post("/batch", response_model=AudioBatchCreateResponse)
def create_audio_batch(
    request: AudioBatchCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).create_audio_batch(
        deployment_id=request.deployment_id,
        audios=request.audios,
    )
```

### Step 4: 測試
**檔案**: `tests/test_audio_batch.py`
- `test_create_audio_batch_success` - 全部成功
- `test_create_audio_batch_idempotent` - 冪等性跳過
- `test_create_audio_batch_reserved_name` - 軟刪除名稱保留
- `test_create_audio_batch_deployment_not_found` - 404 錯誤
- `test_create_audio_batch_exceed_limit` - 超過 20 筆
- `test_create_audio_batch_mixed_results` - 混合結果

---

## 上傳流程

```
使用者體驗:
1. 使用者選擇 1000 個 .wav 檔案
2. 點擊「上傳」按鈕
3. 看到進度條 (已上傳 300/1000...)
4. 完成後看到結果 (成功 990 個，失敗 10 個)

前端自動處理 (對使用者透明):
1. 前端呼叫 POST /audio/upload/presigned-urls 取得批量 presigned URLs
2. 前端使用 presigned URLs 直接上傳檔案到 MinIO (並行)
3. 上傳完成後，前端分批呼叫 POST /audio/batch (20 筆/批)
4. 回傳成功/失敗/跳過統計
5. 失敗項目可重試 (冪等)
```

---

## 驗證方式

1. **單元測試**: `pytest tests/test_audio_batch.py`
2. **Ruff 檢查**: `ruff check && ruff format`
3. **手動測試**: 使用 curl/Postman 測試完整流程

---

## 實作檢查清單

- [ ] Schema 定義
- [ ] Service 層方法
- [ ] API 端點
- [ ] 單元測試
- [ ] Ruff 檢查通過
- [ ] 更新 changelog.md
