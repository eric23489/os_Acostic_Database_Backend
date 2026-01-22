from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.audio import AudioCreate, AudioResponse, AudioUpdate
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
