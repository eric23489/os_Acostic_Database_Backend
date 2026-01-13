from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
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
