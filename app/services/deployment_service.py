from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.deployment import DeploymentInfo
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate


class DeploymentService:
    def __init__(self, db: Session):
        self.db = db

    def get_deployment(self, deployment_id: int) -> DeploymentInfo:
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.id == deployment_id)
            .first()
        )
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )
        return deployment

    def get_deployments(
        self, point_id: int, skip: int = 0, limit: int = 100
    ) -> list[DeploymentInfo]:
        return (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.point_id == point_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_deployment(self, deployment_in: DeploymentCreate) -> DeploymentInfo:
        # Auto-calculate Phase: Max phase for this point + 1
        max_phase = (
            self.db.query(func.max(DeploymentInfo.phase))
            .filter(DeploymentInfo.point_id == deployment_in.point_id)
            .scalar()
        )
        new_phase = (max_phase or 0) + 1

        deployment_data = deployment_in.model_dump()
        deployment_data["phase"] = new_phase

        db_obj = DeploymentInfo(**deployment_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_deployment(
        self, deployment_id: int, deployment_in: DeploymentUpdate
    ) -> DeploymentInfo:
        deployment = self.get_deployment(deployment_id)
        update_data = deployment_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(deployment, field, value)

        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment
