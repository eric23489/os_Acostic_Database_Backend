from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user, get_current_user
from app.db.session import get_db
from app.models.user import UserInfo
from app.schemas.audio import (
    AudioBatchCreateRequest,
    AudioBatchCreateResponse,
    AudioCreate,
    AudioDownloadUrlResponse,
    AudioResponse,
    AudioUpdate,
    AudioWithDetailsResponse,
    MessageResponse,
)
from app.schemas.pagination import PaginatedResponse, SortOrder
from app.services.audio_service import AudioService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/", response_model=PaginatedResponse[AudioResponse])
def get_audios(
    skip: int = 0,
    limit: int = 100,
    deployment_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.DESC,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得音檔列表。

    - **deployment_id**: 篩選佈放 ID (選填)
    - **search**: 搜尋關鍵字 (搜尋 file_name, target)
    - **sort_by**: 排序欄位 (file_name, record_time, file_size, created_at)
    - **order**: 排序方向 (asc, desc)
    """
    items, total = AudioService(db).get_audios(
        skip=skip,
        limit=limit,
        deployment_id=deployment_id,
        search=search,
        sort_by=sort_by,
        order=order,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{audio_id}", response_model=AudioResponse)
def get_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).get_audio(audio_id)


@router.get("/{audio_id}/details", response_model=AudioWithDetailsResponse)
def get_audio_details(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).get_audio_details(audio_id)


@router.get("/{audio_id}/download-url", response_model=AudioDownloadUrlResponse)
def get_audio_download_url(
    audio_id: int,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得 Audio 下載 URL。

    需要 Audio 的 upload_status 為 completed。
    """
    return AudioService(db).get_download_url(audio_id, expires_in)


@router.post("/", response_model=AudioResponse)
def create_audio(
    audio: AudioCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).create_audio(audio)


@router.put("/{audio_id}", response_model=AudioResponse)
def update_audio(
    audio_id: int,
    audio: AudioUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).update_audio(audio_id, audio)


@router.delete("/{audio_id}", response_model=AudioResponse)
def delete_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).delete_audio(audio_id, current_user.id)


@router.post("/{audio_id}/restore", response_model=AudioResponse)
def restore_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> AudioResponse:
    return AudioService(db).restore_audio(audio_id, current_user)


@router.post("/batch", response_model=AudioBatchCreateResponse)
def create_audios_batch(
    request: AudioBatchCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    批量建立 AudioInfo。

    - 全部成功回傳 201
    - 部分跳過回傳 207
    - 冪等設計：重複的 object_key 回傳 skipped
    """
    result = AudioService(db).create_audios_batch(request)
    response.status_code = (
        status.HTTP_207_MULTI_STATUS
        if result.skipped_count > 0 or result.failed_count > 0
        else status.HTTP_201_CREATED
    )
    return result


@router.delete("/{audio_id}/permanent", response_model=MessageResponse)
def hard_delete_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_admin_user),
) -> MessageResponse:
    """
    永久刪除單一 Audio。需要 Admin 權限。

    - 刪除 MinIO 物件
    - 刪除資料庫記錄
    - 釋放 object_key，可重新使用
    """
    return AudioService(db).hard_delete_audio(audio_id)
