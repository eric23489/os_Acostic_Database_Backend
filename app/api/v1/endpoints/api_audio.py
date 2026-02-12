from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.audio import AudioInfo
from app.models.user import UserRole
from app.schemas.audio import (
    AudioCreate,
    AudioResponse,
    AudioUpdate,
    AudioWithDetailsResponse,
)
from app.services.audio_service import AudioService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/", response_model=List[AudioResponse])
def get_audios(
    deployment_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).get_audios(
        deployment_id=deployment_id, skip=skip, limit=limit
    )


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
    current_user=Depends(get_current_user),
):
    audio = db.query(AudioInfo).filter(AudioInfo.id == audio_id).first()
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found",
        )
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.id != audio.deleted_by
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deleter or admin can restore this resource",
        )
    return AudioService(db).restore_audio(audio_id)


@router.delete("/{audio_id}/permanent", response_model=dict)
def hard_delete_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    永久刪除單一 Audio。

    - 刪除 MinIO 物件
    - 刪除資料庫記錄
    - 釋放 object_key，可重新使用

    需要 Admin 權限。
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required for permanent deletion",
        )
    return AudioService(db).hard_delete_audio(audio_id)
