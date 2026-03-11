# Plan: 批量下載音檔 Presigned URL 端點

## Status: 進行中 (部分完成)

## Context

研究人員需要一次取得多個音檔的下載連結，現有架構只有單一音檔的
`GET /audio/{id}/download-url`。本功能新增批量版本，讓前端傳入
audio_id 清單，後端一次回傳所有對應的 presigned URL，前端再
並行觸發瀏覽器下載。採用 presigned URL 方案（非 ZIP 串流），
原因是資料流量不經過伺服器，且 1000 筆大音檔不會造成超時問題。

---

## 需求確認

| 項目 | 決定 |
|------|------|
| 實作方式 | Presigned URL 清單（前端直連 MinIO） |
| 選取維度 | `audio_id` 清單 |
| 數量上限 | 1000 |
| 權限 | 登入用戶即可（`get_current_user`） |
| 部分失敗 | 回傳 `skipped`，不拋整體錯誤 |

---

## 修改檔案清單

| 檔案 | 操作 | 狀態 |
|------|------|------|
| `app/core/exceptions.py` | 新增 `MINIO_PRESIGN_FAILED` 常數 | **已完成** |
| `app/schemas/audio.py` | 新增 3 個 schema class | **已完成** |
| `app/services/audio_service.py` | 新增 `get_batch_download_urls` 方法 | 待完成 |
| `app/api/v1/endpoints/api_audio.py` | 新增 `POST /audio/batch-download-urls` 端點 | 待完成 |
| `tests/test_audio_batch_download.py` | 新建測試檔案 | 待完成 |

---

## 已完成的變更（尚未 commit）

### `app/core/exceptions.py`

在 `MINIO_UPLOAD_FAILED` 之後新增：

```python
MINIO_PRESIGN_FAILED = AppException(
    error_code="MINIO_PRESIGN_FAILED",
    message="Failed to generate presigned URL",
    http_status=status.HTTP_502_BAD_GATEWAY,
)
```

### `app/schemas/audio.py`

在 `MessageResponse` 之前新增：

```python
class AudioBatchDownloadRequest(BaseModel):
    audio_ids: list[int] = Field(..., min_length=1, max_length=1000)

class AudioBatchDownloadItem(BaseModel):
    audio_id: int
    status: Literal["ok", "skipped"]
    file_name: str | None = None
    file_size: int | None = None
    presigned_url: str | None = None
    reason: str | None = None

class AudioBatchDownloadResponse(BaseModel):
    total: int
    success_count: int
    skipped_count: int
    expires_in: int
    items: list[AudioBatchDownloadItem]
```

---

## 待完成實作細節

### `app/services/audio_service.py`

新增 import（`MINIO_PRESIGN_FAILED`、新 schema）：

```python
from app.core.exceptions import (
    ...
    MINIO_PRESIGN_FAILED,
    ...
)
from app.schemas.audio import (
    ...
    AudioBatchDownloadRequest,
    AudioBatchDownloadItem,
    AudioBatchDownloadResponse,
)
```

新增方法至 `AudioService`，緊接在 `get_download_url` 之後：

```python
def get_batch_download_urls(
    self, audio_ids: list[int], expires_in: int = 3600
) -> AudioBatchDownloadResponse:
    """
    批量取得 Audio 下載 presigned URL。

    - 找不到或尚未完成上傳的音檔以 skipped 回傳，不拋整體錯誤
    - 重用單一 MinioService 實例減少 boto3 client 建立開銷
    """
    audios = (
        self.db.query(AudioInfo)
        .options(
            joinedload(AudioInfo.deployment)
            .joinedload(DeploymentInfo.point)
            .joinedload(PointInfo.project)
        )
        .filter(
            AudioInfo.id.in_(audio_ids),
            AudioInfo.is_deleted.is_(False),
        )
        .all()
    )

    found_ids = {audio.id for audio in audios}
    minio_service = MinioService()
    items: list[AudioBatchDownloadItem] = []

    for audio_id in audio_ids:
        if audio_id not in found_ids:
            items.append(AudioBatchDownloadItem(
                audio_id=audio_id,
                status="skipped",
                reason="audio not found",
            ))
            continue

        audio = next(a for a in audios if a.id == audio_id)

        if audio.upload_status != UploadStatus.COMPLETED:
            items.append(AudioBatchDownloadItem(
                audio_id=audio_id,
                status="skipped",
                reason="upload not completed",
            ))
            continue

        try:
            bucket_name = audio.deployment.point.project.name
            presigned_url = minio_service.generate_presigned_url(
                bucket=bucket_name,
                key=audio.object_key,
                expires_in=expires_in,
                method="get_object",
            )
        except Exception:
            raise MINIO_PRESIGN_FAILED

        items.append(AudioBatchDownloadItem(
            audio_id=audio_id,
            status="ok",
            file_name=audio.file_name,
            file_size=audio.file_size,
            presigned_url=presigned_url,
        ))

    success_count = sum(1 for i in items if i.status == "ok")
    return AudioBatchDownloadResponse(
        total=len(audio_ids),
        success_count=success_count,
        skipped_count=len(items) - success_count,
        expires_in=expires_in,
        items=items,
    )
```

---

### `app/api/v1/endpoints/api_audio.py`

更新 import 區塊，加入新 schema：

```python
from app.schemas.audio import (
    ...
    AudioBatchDownloadRequest,
    AudioBatchDownloadResponse,
    ...
)
```

在 `get_audio_download_url` 端點之後新增：

```python
@router.post("/batch-download-urls", response_model=AudioBatchDownloadResponse)
def get_audio_batch_download_urls(
    request: AudioBatchDownloadRequest,
    expires_in: int = Query(3600, ge=60, le=86400),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    批量取得 Audio 下載 URL。

    - **audio_ids**: 最多 1000 個 Audio ID
    - **expires_in**: URL 有效秒數（60~86400，預設 3600）
    - 找不到或尚未完成上傳的音檔以 skipped 狀態回傳
    """
    return AudioService(db).get_batch_download_urls(request.audio_ids, expires_in)
```

---

### `tests/test_audio_batch_download.py`（新建）

測試案例（6 個）：

1. **全部成功**：2 個 audio 都 completed，回傳 2 個 `ok`
2. **部分 skipped**：1 個 not found、1 個 upload not completed、1 個成功
3. **全部 not found**：`success_count=0`，`skipped_count=N`
4. **audio_ids 超過 1000**：422 validation error
5. **audio_ids 為空**：422 validation error
6. **MinIO 失敗**：mock `generate_presigned_url` 拋 Exception，回傳 502

---

## 驗證方式

1. `pytest tests/test_audio_batch_download.py -v`
2. Swagger UI `POST /api/v1/audio/batch-download-urls`，傳入已完成/未完成/不存在的 ID 組合
3. 確認回傳的 presigned_url 可在瀏覽器直接開啟下載
