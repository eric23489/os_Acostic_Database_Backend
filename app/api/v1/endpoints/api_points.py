from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.point import PointCreate, PointResponse, PointUpdate
from app.services.point_service import PointService

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/", response_model=List[PointResponse])
def get_points(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PointService(db).get_points(project_id, skip=skip, limit=limit)


@router.get("/{point_id}", response_model=PointResponse)
def get_point(
    point_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PointService(db).get_point(point_id)


@router.post("/", response_model=PointResponse)
def create_point(
    point: PointCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PointService(db).create_point(point)


@router.put("/{point_id}", response_model=PointResponse)
def update_point(
    point_id: int,
    point: PointUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PointService(db).update_point(point_id, point)
