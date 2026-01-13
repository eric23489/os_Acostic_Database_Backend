from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.recorder import RecorderCreate, RecorderResponse
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
    recorder: RecorderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = RecorderService(db)
    return service.update_recorder(recorder_id, recorder)
