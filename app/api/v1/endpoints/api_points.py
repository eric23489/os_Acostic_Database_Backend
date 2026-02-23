from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.point import PointInfo
from app.models.user import UserRole
from app.schemas.pagination import PaginatedResponse, SortOrder
from app.schemas.point import (
    PointCreate,
    PointResponse,
    PointUpdate,
    PointWithProjectResponse,
)
from app.services.point_service import PointService

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/", response_model=PaginatedResponse[PointResponse])
def get_points(
    skip: int = 0,
    limit: int = 100,
    project_id: int | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.DESC,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得測點列表。

    - **project_id**: 篩選專案 ID (選填，不傳回傳所有)
    - **search**: 搜尋關鍵字 (搜尋 name, description)
    - **sort_by**: 排序欄位 (name, created_at)
    - **order**: 排序方向 (asc, desc)
    """
    items, total = PointService(db).get_points(
        skip=skip,
        limit=limit,
        project_id=project_id,
        search=search,
        sort_by=sort_by,
        order=order,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{point_id}", response_model=PointResponse)
def get_point(
    point_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PointService(db).get_point(point_id)


@router.get("/{point_id}/details", response_model=PointWithProjectResponse)
def get_point_details(
    point_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get a single point with its associated project details.
    """
    return PointService(db).get_point_details(point_id)


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


@router.delete("/{point_id}", response_model=PointResponse)
def delete_point(
    point_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PointService(db).delete_point(point_id, current_user.id)


@router.post("/{point_id}/restore", response_model=PointResponse)
def restore_point(
    point_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    point = db.query(PointInfo).filter(PointInfo.id == point_id).first()
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Point not found",
        )
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.id != point.deleted_by
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deleter or admin can restore this resource",
        )
    return PointService(db).restore_point(point_id)


@router.delete("/{point_id}/permanent", response_model=dict)
def hard_delete_point(
    point_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    永久刪除 Point 及所有相關資料。

    - 刪除 MinIO 中該 Point 下的所有物件
    - 刪除資料庫中的所有相關記錄
    - 釋放名稱，可重新使用

    需要 Admin 權限。
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required for permanent deletion",
        )
    return PointService(db).hard_delete_point(point_id)
