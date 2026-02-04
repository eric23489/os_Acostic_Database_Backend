from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.schemas.point import PointCreate, PointUpdate


class PointService:
    def __init__(self, db: Session):
        self.db = db

    def get_point(self, point_id: int) -> PointInfo:
        point = (
            self.db.query(PointInfo)
            .filter(PointInfo.id == point_id, PointInfo.is_deleted.is_(False))
            .first()
        )
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Point not found",
            )
        return point

    def get_point_details(self, point_id: int) -> PointInfo:
        """
        Get a single point with its associated project details.
        Uses joinedload to prevent N+1 query problem.
        """
        point = (
            self.db.query(PointInfo)
            .options(joinedload(PointInfo.project))
            .filter(PointInfo.id == point_id, PointInfo.is_deleted.is_(False))
            .first()
        )
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Point not found"
            )
        return point

    def get_points(
        self, project_id: int, skip: int = 0, limit: int = 100
    ) -> list[PointInfo]:
        return (
            self.db.query(PointInfo)
            .filter(PointInfo.project_id == project_id, PointInfo.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_point(self, point_in: PointCreate) -> PointInfo:
        # Check unique constraint (project_id, name)
        if (
            self.db.query(PointInfo)
            .filter(
                PointInfo.project_id == point_in.project_id,
                PointInfo.name == point_in.name,
                PointInfo.is_deleted.is_(False),
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Point name already exists in this project",
            )

        point_data = point_in.model_dump()

        db_obj = PointInfo(**point_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_point(self, point_id: int, point_in: PointUpdate) -> PointInfo:
        point = self.get_point(point_id)
        update_data = point_in.model_dump(exclude_unset=True)

        # Check for duplicates if name or project_id is updated
        if "name" in update_data or "project_id" in update_data:
            new_name = update_data.get("name", point.name)
            new_project_id = update_data.get("project_id", point.project_id)

            if (
                self.db.query(PointInfo)
                .filter(
                    PointInfo.project_id == new_project_id,
                    PointInfo.name == new_name,
                    PointInfo.id != point_id,
                    PointInfo.is_deleted.is_(False),
                )
                .first()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Point name already exists in this project",
                )

        for field, value in update_data.items():
            setattr(point, field, value)

        self.db.add(point)
        self.db.commit()
        self.db.refresh(point)
        return point

    def delete_point(self, point_id: int, user_id: int) -> PointInfo:
        point = self.get_point(point_id)

        now = datetime.now(timezone.utc)

        # 1. Mark Point as deleted
        point.is_deleted = True
        point.deleted_at = now
        point.deleted_by = user_id

        # 2. Cascade Soft Delete: Find related Deployments
        deployments = (
            self.db.query(DeploymentInfo.id)
            .filter(DeploymentInfo.point_id == point_id)
            .all()
        )
        deployment_ids = [d.id for d in deployments]

        if deployment_ids:
            # 3. Cascade to Audios
            self.db.query(AudioInfo).filter(
                AudioInfo.deployment_id.in_(deployment_ids)
            ).update(
                {
                    AudioInfo.is_deleted: True,
                    AudioInfo.deleted_at: now,
                    AudioInfo.deleted_by: user_id,
                },
                synchronize_session=False,
            )
            # Update Deployments
            self.db.query(DeploymentInfo).filter(
                DeploymentInfo.point_id == point_id
            ).update(
                {
                    DeploymentInfo.is_deleted: True,
                    DeploymentInfo.deleted_at: now,
                    DeploymentInfo.deleted_by: user_id,
                },
                synchronize_session=False,
            )

        self.db.add(point)
        self.db.commit()
        self.db.refresh(point)
        return point

    def restore_point(self, point_id: int) -> PointInfo:
        point = self.db.query(PointInfo).filter(PointInfo.id == point_id).first()
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Point not found",
            )

        # Check for name collision before restore
        if (
            self.db.query(PointInfo)
            .filter(
                PointInfo.project_id == point.project_id,
                PointInfo.name == point.name,
                PointInfo.is_deleted.is_(False),
                PointInfo.id != point_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active point with this name already exists in the project. Cannot restore.",
            )

        # Cascade Restore Logic
        # Only restore child records deleted at the same time as parent
        update_values = {
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by": None,
        }

        # Time threshold: only restore records deleted within 5 seconds of parent
        deleted_at = point.deleted_at
        time_min = deleted_at - timedelta(seconds=5)
        time_max = deleted_at + timedelta(seconds=5)

        # 1. Cascade to Audios (Grandchildren)
        # Subquery: Find all Deployment IDs in this point
        deployment_ids_sub = self.db.query(DeploymentInfo.id).filter(
            DeploymentInfo.point_id == point_id
        )
        self.db.query(AudioInfo).filter(
            AudioInfo.deployment_id.in_(deployment_ids_sub),
            AudioInfo.deleted_at >= time_min,
            AudioInfo.deleted_at <= time_max,
        ).update(update_values, synchronize_session=False)

        # 2. Cascade to Deployments (Children)
        self.db.query(DeploymentInfo).filter(
            DeploymentInfo.point_id == point_id,
            DeploymentInfo.deleted_at >= time_min,
            DeploymentInfo.deleted_at <= time_max,
        ).update(update_values, synchronize_session=False)

        point.is_deleted = False
        point.deleted_at = None
        point.deleted_by = None
        self.db.add(point)
        self.db.commit()
        self.db.refresh(point)
        return point
