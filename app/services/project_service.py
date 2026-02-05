import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.minio import get_s3_client
from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.naming import generate_slug_from_zh

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def get_project(self, project_id: int) -> ProjectInfo:
        project = (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.id == project_id)
            .filter(ProjectInfo.is_deleted.is_(False))
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    def get_projects(self, skip: int = 0, limit: int = 100) -> list[ProjectInfo]:
        return (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_projects_hierarchy(self) -> list[ProjectInfo]:
        return (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.is_deleted.is_(False))
            .options(
                selectinload(ProjectInfo.points).selectinload(PointInfo.deployments)
            )
            .all()
        )

    def create_project(self, project_in: ProjectCreate) -> ProjectInfo:
        # Auto-generate name from name_zh if name is not provided
        if not project_in.name:
            if not project_in.name_zh:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either 'name' or 'name_zh' must be provided.",
                )

            base_slug = generate_slug_from_zh(project_in.name_zh)
            candidate_name = base_slug

            # Update the input model
            project_in.name = candidate_name

        # Check if project name exists
        if (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.name == project_in.name)
            .filter(ProjectInfo.is_deleted.is_(False))
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this name already exists",
            )

        # Check if Chinese name (name_zh) exists, if provided
        if project_in.name_zh and (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.name_zh == project_in.name_zh)
            .filter(ProjectInfo.is_deleted.is_(False))
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project with this Chinese name (name_zh) already exists",
            )

        # Check if name is reserved by a soft-deleted project
        if (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.name == project_in.name)
            .filter(ProjectInfo.is_deleted.is_(True))
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name reserved by deleted project. Hard delete to release.",
            )

        # Check if name_zh is reserved by a soft-deleted project
        if project_in.name_zh and (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.name_zh == project_in.name_zh)
            .filter(ProjectInfo.is_deleted.is_(True))
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name_zh reserved by deleted project. Hard delete to release.",
            )

        db_obj = ProjectInfo(**project_in.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)

        # Create MinIO bucket
        try:
            s3_client = get_s3_client()
            s3_client.create_bucket(Bucket=db_obj.name)
        except Exception as e:
            # Log error or handle it. For now, we might not want to fail the whole request
            # if bucket creation fails, but it's good practice to ensure consistency.
            logger.error(f"Failed to create MinIO bucket '{db_obj.name}': {e}")

        return db_obj

    def update_project(self, project_id: int, project_in: ProjectUpdate) -> ProjectInfo:
        project = self.get_project(project_id)
        update_data = project_in.model_dump(exclude_unset=True)

        # Check for name_zh uniqueness if it's being updated
        if "name_zh" in update_data and update_data["name_zh"]:
            if (
                self.db.query(ProjectInfo)
                .filter(
                    ProjectInfo.name_zh == update_data["name_zh"],
                    ProjectInfo.id != project_id,
                    ProjectInfo.is_deleted.is_(False),
                )
                .first()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project with this Chinese name (name_zh) already exists",
                )

        for field, value in update_data.items():
            setattr(project, field, value)

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: int, user_id: int) -> ProjectInfo:
        project = self.get_project(project_id)

        now = datetime.now(UTC)
        update_values = {
            "is_deleted": True,
            "deleted_at": now,
            "deleted_by": user_id,
        }

        # This synchronous part handles the faster updates for Project, Point, and Deployment.
        # The slow Audio update is handled by a background task.

        # Subquery: Find all Point IDs in this project
        point_ids_sub = self.db.query(PointInfo.id).filter(
            PointInfo.project_id == project_id
        )

        # 1. Cascade to Deployments
        self.db.query(DeploymentInfo).filter(
            DeploymentInfo.point_id.in_(point_ids_sub)
        ).update(update_values, synchronize_session=False)

        # 2. Cascade to Points
        self.db.query(PointInfo).filter(PointInfo.project_id == project_id).update(
            update_values, synchronize_session=False
        )

        # 3. Mark the Project itself as deleted
        project.is_deleted = True
        project.deleted_at = now
        project.deleted_by = user_id

        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project_audios(
        self, project_id: int, user_id: int, deleted_at: datetime
    ):
        """
        Background task to delete audios associated with a project.
        Uses the same deleted_at timestamp as the parent project for consistency.
        """
        update_values = {
            "is_deleted": True,
            "deleted_at": deleted_at,
            "deleted_by": user_id,
        }

        point_ids_sub = self.db.query(PointInfo.id).filter(
            PointInfo.project_id == project_id
        )
        deployment_ids_sub = self.db.query(DeploymentInfo.id).filter(
            DeploymentInfo.point_id.in_(point_ids_sub)
        )
        self.db.query(AudioInfo).filter(
            AudioInfo.deployment_id.in_(deployment_ids_sub)
        ).update(update_values, synchronize_session=False)
        self.db.commit()

    def restore_project(self, project_id: int) -> ProjectInfo:
        # We need to query even if is_deleted is True
        project = (
            self.db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Check for name collision before restore
        if (
            self.db.query(ProjectInfo)
            .filter(
                ProjectInfo.name == project.name,
                ProjectInfo.is_deleted.is_(False),
                ProjectInfo.id != project_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active project with this name already exists. Cannot restore.",
            )

        # Check for name_zh collision before restore
        if project.name_zh and (
            self.db.query(ProjectInfo)
            .filter(
                ProjectInfo.name_zh == project.name_zh,
                ProjectInfo.is_deleted.is_(False),
                ProjectInfo.id != project_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active project with this name_zh already exists. Cannot restore.",
            )

        # Cascade Restore Logic
        # Only restore child records deleted at the same time as parent
        update_values = {
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by": None,
        }

        # Time threshold: only restore records deleted within 5 seconds of parent
        deleted_at = project.deleted_at
        time_min = deleted_at - timedelta(seconds=5)
        time_max = deleted_at + timedelta(seconds=5)

        # 1. Cascade to Audios (Grandchildren)
        # Subquery: Find all Point IDs in this project (even deleted ones)
        point_ids_sub = self.db.query(PointInfo.id).filter(
            PointInfo.project_id == project_id
        )
        # Subquery: Find all Deployment IDs in these points
        deployment_ids_sub = self.db.query(DeploymentInfo.id).filter(
            DeploymentInfo.point_id.in_(point_ids_sub)
        )
        # Update Audios (only those deleted with the project)
        self.db.query(AudioInfo).filter(
            AudioInfo.deployment_id.in_(deployment_ids_sub),
            AudioInfo.deleted_at >= time_min,
            AudioInfo.deleted_at <= time_max,
        ).update(update_values, synchronize_session=False)

        # 2. Cascade to Deployments (Children)
        self.db.query(DeploymentInfo).filter(
            DeploymentInfo.point_id.in_(point_ids_sub),
            DeploymentInfo.deleted_at >= time_min,
            DeploymentInfo.deleted_at <= time_max,
        ).update(update_values, synchronize_session=False)

        # 3. Cascade to Points (Direct Children)
        self.db.query(PointInfo).filter(
            PointInfo.project_id == project_id,
            PointInfo.deleted_at >= time_min,
            PointInfo.deleted_at <= time_max,
        ).update(update_values, synchronize_session=False)

        project.is_deleted = False
        project.deleted_at = None
        project.deleted_by = None
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def hard_delete_project(self, project_id: int) -> dict:
        """
        永久刪除 Project 及所有相關資料。

        包含：
        - 刪除 MinIO Bucket 和所有物件
        - 刪除資料庫中的所有相關記錄 (Audios, Deployments, Points, Project)
        - 釋放名稱，可重新使用
        """
        # 查詢 Project (包含已軟刪除)
        project = (
            self.db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        project_name = project.name

        # 取得所有相關 Audio 的 object_key
        point_ids_sub = self.db.query(PointInfo.id).filter(
            PointInfo.project_id == project_id
        )
        deployment_ids_sub = self.db.query(DeploymentInfo.id).filter(
            DeploymentInfo.point_id.in_(point_ids_sub)
        )
        audios = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.deployment_id.in_(deployment_ids_sub))
            .all()
        )

        # 刪除 MinIO 物件
        s3_client = get_s3_client()
        bucket_name = project_name

        if audios:
            objects_to_delete = [{"Key": a.object_key} for a in audios]
            # S3 每次最多刪除 1000 個物件
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i : i + 1000]
                try:
                    s3_client.delete_objects(
                        Bucket=bucket_name, Delete={"Objects": batch}
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete objects in {bucket_name}: {e}")

        # 刪除 MinIO Bucket
        try:
            s3_client.delete_bucket(Bucket=bucket_name)
        except Exception as e:
            logger.warning(f"Failed to delete bucket {bucket_name}: {e}")

        # 刪除 DB 記錄 (順序重要：先子後父)
        deleted_audios = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.deployment_id.in_(deployment_ids_sub))
            .delete(synchronize_session=False)
        )

        self.db.query(DeploymentInfo).filter(
            DeploymentInfo.point_id.in_(point_ids_sub)
        ).delete(synchronize_session=False)

        self.db.query(PointInfo).filter(PointInfo.project_id == project_id).delete(
            synchronize_session=False
        )

        self.db.query(ProjectInfo).filter(ProjectInfo.id == project_id).delete(
            synchronize_session=False
        )

        self.db.commit()

        return {
            "message": f"Project '{project_name}' permanently deleted",
            "deleted_audios": deleted_audios,
        }
