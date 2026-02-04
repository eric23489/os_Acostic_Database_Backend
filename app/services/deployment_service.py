from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate


class DeploymentService:
    def __init__(self, db: Session):
        self.db = db

    def get_deployment(self, deployment_id: int) -> DeploymentInfo:
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(
                DeploymentInfo.id == deployment_id, DeploymentInfo.is_deleted.is_(False)
            )
            .first()
        )
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )
        return deployment

    def get_deployment_details(self, deployment_id: int) -> DeploymentInfo:
        deployment = (
            self.db.query(DeploymentInfo)
            .options(
                joinedload(DeploymentInfo.point).joinedload(PointInfo.project),
                joinedload(DeploymentInfo.recorder),
            )
            .filter(
                DeploymentInfo.id == deployment_id, DeploymentInfo.is_deleted.is_(False)
            )
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
            .filter(
                DeploymentInfo.point_id == point_id, DeploymentInfo.is_deleted.is_(False)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_deployment(self, deployment_in: DeploymentCreate) -> DeploymentInfo:
        # Auto-calculate Phase: Max phase for this point + 1
        max_phase = (
            self.db.query(func.max(DeploymentInfo.phase))
            .filter(
                DeploymentInfo.point_id == deployment_in.point_id,
                DeploymentInfo.is_deleted.is_(False),
            )
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

    def delete_deployment(self, deployment_id: int, user_id: int) -> DeploymentInfo:
        deployment = self.get_deployment(deployment_id)

        now = datetime.now(timezone.utc)

        # 1. Mark Deployment as deleted
        deployment.is_deleted = True
        deployment.deleted_at = now
        deployment.deleted_by = user_id

        # 2. Cascade Soft Delete: Mark related Audios
        self.db.query(AudioInfo).filter(
            AudioInfo.deployment_id == deployment_id
        ).update(
            {
                AudioInfo.is_deleted: True,
                AudioInfo.deleted_at: now,
                AudioInfo.deleted_by: user_id,
            },
            synchronize_session=False,
        )

        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def restore_deployment(self, deployment_id: int) -> DeploymentInfo:
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

        # Check for unique constraint collision before restore
        # Constraint: point_id + phase
        if (
            self.db.query(DeploymentInfo)
            .filter(
                DeploymentInfo.point_id == deployment.point_id,
                DeploymentInfo.phase == deployment.phase,
                DeploymentInfo.is_deleted.is_(False),
                DeploymentInfo.id != deployment_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active deployment with this phase already exists for the point. Cannot restore.",
            )

        # Cascade Restore Logic
        # Only restore child records deleted at the same time as parent
        update_values = {
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by": None,
        }

        # Time threshold: only restore records deleted within 5 seconds of parent
        deleted_at = deployment.deleted_at
        time_min = deleted_at - timedelta(seconds=5)
        time_max = deleted_at + timedelta(seconds=5)

        # 1. Cascade to Audios (Children)
        self.db.query(AudioInfo).filter(
            AudioInfo.deployment_id == deployment_id,
            AudioInfo.deleted_at >= time_min,
            AudioInfo.deleted_at <= time_max,
        ).update(update_values, synchronize_session=False)

        deployment.is_deleted = False
        deployment.deleted_at = None
        deployment.deleted_by = None
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment
