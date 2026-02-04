from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.recorder import RecorderInfo
from app.models.user import UserRole
from app.schemas.recorder import RecorderCreate, RecorderResponse, RecorderUpdate
from app.services.recorder_service import RecorderService

router = APIRouter(prefix="/recorders", tags=["recorders"])


@router.get("/{recorder_id}", response_model=RecorderResponse)
def get_recorder(
    recorder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return RecorderService(db).get_recorder(recorder_id)


@router.get("/", response_model=List[RecorderResponse])
def get_recorders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return RecorderService(db).get_recorders(skip=skip, limit=limit)


@router.post("/", response_model=RecorderResponse)
def create_recorder(
    recorder: RecorderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = RecorderService(db)
    return service.create_recorder(recorder)


@router.put("/{recorder_id}", response_model=RecorderResponse)
def update_recorder(
    recorder_id: int,
    recorder: RecorderUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = RecorderService(db)
    return service.update_recorder(recorder_id, recorder)


@router.delete("/{recorder_id}", response_model=RecorderResponse)
def delete_recorder(
    recorder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return RecorderService(db).delete_recorder(recorder_id, current_user.id)


@router.post("/{recorder_id}/restore", response_model=RecorderResponse)
def restore_recorder(
    recorder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    recorder = db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).first()
    if not recorder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recorder not found",
        )
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.id != recorder.deleted_by
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deleter or admin can restore this resource",
        )
    return RecorderService(db).restore_recorder(recorder_id)
