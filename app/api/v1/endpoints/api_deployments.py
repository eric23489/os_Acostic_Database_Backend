from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.deployment import DeploymentInfo
from app.enums.enums import UserRole
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
    DeploymentWithDetailsResponse,
)
from app.schemas.pagination import PaginatedResponse, SortOrder
from app.services.deployment_service import DeploymentService

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("/", response_model=PaginatedResponse[DeploymentResponse])
def get_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    point_id: int | None = None,
    deployment_status: str | None = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.DESC,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得佈放列表。

    - **point_id**: 篩選測點 ID (選填，不傳回傳所有)
    - **deployment_status**: 篩選狀態
    - **sort_by**: 排序欄位 (phase, created_at, deploy_time, return_time)
    - **order**: 排序方向 (asc, desc)
    """
    items, total = DeploymentService(db).get_deployments(
        skip=skip,
        limit=limit,
        point_id=point_id,
        status=deployment_status,
        sort_by=sort_by,
        order=order,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DeploymentService(db).get_deployment(deployment_id)


@router.get("/{deployment_id}/details", response_model=DeploymentWithDetailsResponse)
def get_deployment_details(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DeploymentService(db).get_deployment_details(deployment_id)


@router.post("/", response_model=DeploymentResponse)
def create_deployment(
    deployment: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DeploymentService(db).create_deployment(deployment)


@router.put("/{deployment_id}", response_model=DeploymentResponse)
def update_deployment(
    deployment_id: int,
    deployment: DeploymentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DeploymentService(db).update_deployment(deployment_id, deployment)


@router.delete("/{deployment_id}", response_model=DeploymentResponse)
def delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DeploymentService(db).delete_deployment(deployment_id, current_user.id)


@router.post("/{deployment_id}/restore", response_model=DeploymentResponse)
def restore_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deployment = (
        db.query(DeploymentInfo).filter(DeploymentInfo.id == deployment_id).first()
    )
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    if (
        current_user.role != UserRole.ADMIN.value
        and current_user.id != deployment.deleted_by
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the deleter or admin can restore this resource",
        )
    return DeploymentService(db).restore_deployment(deployment_id)


@router.delete("/{deployment_id}/permanent", response_model=dict)
def hard_delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    永久刪除 Deployment 及所有相關資料。

    - 刪除 MinIO 中該 Deployment 下的所有物件
    - 刪除資料庫中的所有相關記錄
    - 釋放 phase，可重新使用

    需要 Admin 權限。
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required for permanent deletion",
        )
    return DeploymentService(db).hard_delete_deployment(deployment_id)
