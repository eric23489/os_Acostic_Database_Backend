from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user, get_current_user
from app.db.session import get_db
from app.enums.enums import RecorderStatus
from app.schemas.common import MessageResponse
from app.schemas.pagination import PaginatedResponse, SortOrder
from app.schemas.recorder import (
    RecorderCreate,
    RecorderResponse,
    RecorderStatsResponse,
    RecorderUpdate,
)
from app.services.recorder_service import RecorderService

router = APIRouter(prefix="/recorders", tags=["recorders"])


@router.get("/stats", response_model=RecorderStatsResponse)
def get_recorder_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RecorderStatsResponse:
    """回傳可用儀器數量與佈放中儀器數量。"""
    return RecorderService(db).get_recorder_stats()


@router.get("/{recorder_id}", response_model=RecorderResponse)
def get_recorder(
    recorder_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return RecorderService(db).get_recorder(recorder_id)


@router.get("/", response_model=PaginatedResponse[RecorderResponse])
def get_recorders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = None,
    recorder_status: RecorderStatus | None = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.DESC,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得錄音器列表。

    - **search**: 搜尋關鍵字 (搜尋 brand, model, sn, owner)
    - **recorder_status**: 篩選狀態
    - **sort_by**: 排序欄位 (brand, model, sn, created_at)
    - **order**: 排序方向 (asc, desc)
    """
    items, total = RecorderService(db).get_recorders(
        skip=skip,
        limit=limit,
        search=search,
        status=recorder_status,
        sort_by=sort_by,
        order=order,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


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
    return RecorderService(db).restore_recorder(
        recorder_id, current_user.id, current_user.role
    )


@router.delete("/{recorder_id}/permanent", response_model=MessageResponse)
def hard_delete_recorder(
    recorder_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_admin_user),
):
    """
    永久刪除 Recorder。需要 Admin 權限。

    注意：如果有 Deployment 引用此 Recorder，將無法刪除。
    """
    return RecorderService(db).hard_delete_recorder(recorder_id)
