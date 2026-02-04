from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.deployment import DeploymentInfo
from app.models.user import UserRole
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
    DeploymentWithDetailsResponse,
)
from app.services.deployment_service import DeploymentService

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("/", response_model=List[DeploymentResponse])
def get_deployments(
    point_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DeploymentService(db).get_deployments(point_id, skip=skip, limit=limit)


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
