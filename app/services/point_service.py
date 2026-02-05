import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.minio import get_s3_client
from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.schemas.point import PointCreate, PointUpdate

logger = logging.getLogger(__name__)


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

        # Check if name is reserved by a soft-deleted point
        if (
            self.db.query(PointInfo)
            .filter(
                PointInfo.project_id == point_in.project_id,
                PointInfo.name == point_in.name,
                PointInfo.is_deleted.is_(True),
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name reserved by deleted point. Hard delete to release.",
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

        now = datetime.now(UTC)

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

    def hard_delete_point(self, point_id: int) -> dict:
        """
        永久刪除 Point 及所有相關資料。

        包含：
        - 刪除 MinIO 中該 Point 下的所有物件
        - 刪除資料庫中的所有相關記錄 (Audios, Deployments, Point)
        - 釋放名稱，可重新使用
        """
        # 查詢 Point (包含已軟刪除)
        point = self.db.query(PointInfo).filter(PointInfo.id == point_id).first()
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Point not found",
            )

        # 取得 Project 名稱 (用於 MinIO bucket)
        project = (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.id == point.project_id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent project not found",
            )
        bucket_name = project.name

        # 取得相關 Audio
        deployment_ids_sub = self.db.query(DeploymentInfo.id).filter(
            DeploymentInfo.point_id == point_id
        )
        audios = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.deployment_id.in_(deployment_ids_sub))
            .all()
        )

        # 刪除 MinIO 物件
        s3_client = get_s3_client()
        if audios:
            objects_to_delete = [{"Key": a.object_key} for a in audios]
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i : i + 1000]
                try:
                    s3_client.delete_objects(
                        Bucket=bucket_name, Delete={"Objects": batch}
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete objects in bucket {bucket_name}: {e}"
                    )

        # 刪除 DB 記錄 (先子後父)
        deleted_audios = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.deployment_id.in_(deployment_ids_sub))
            .delete(synchronize_session=False)
        )

        self.db.query(DeploymentInfo).filter(
            DeploymentInfo.point_id == point_id
        ).delete(synchronize_session=False)

        self.db.query(PointInfo).filter(PointInfo.id == point_id).delete(
            synchronize_session=False
        )

        self.db.commit()

        return {
            "message": "Point permanently deleted",
            "deleted_audios": deleted_audios,
        }
