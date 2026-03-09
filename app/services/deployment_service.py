import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    DEPLOYMENT_NOT_FOUND,
    DEPLOYMENT_PHASE_COLLISION,
    POINT_NOT_FOUND,
    PROJECT_NOT_FOUND,
)
from app.core.minio import get_s3_client
from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.models.upload_job import UploadJob, UploadTask
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate
from app.schemas.pagination import SortOrder
from app.utils.query import apply_filter, apply_sorting, paginate

logger = logging.getLogger(__name__)


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
            raise DEPLOYMENT_NOT_FOUND
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
            raise DEPLOYMENT_NOT_FOUND
        return deployment

    def get_deployments(
        self,
        skip: int = 0,
        limit: int = 100,
        point_id: int | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[DeploymentInfo], int]:
        """
        取得佈放列表，支援篩選、排序和分頁。

        Args:
            skip: 跳過的筆數
            limit: 每頁筆數上限
            point_id: 篩選測點 ID (選填)
            status: 篩選狀態
            sort_by: 排序欄位 (phase, created_at, deploy_time, return_time)
            order: 排序方向

        Returns:
            tuple: (items, total)
        """
        query = self.db.query(DeploymentInfo).filter(
            DeploymentInfo.is_deleted.is_(False)
        )

        # 篩選
        query = apply_filter(query, DeploymentInfo, "point_id", point_id)
        query = apply_filter(query, DeploymentInfo, "status", status)

        # 排序
        allowed_sort_fields = ["phase", "created_at", "deploy_time", "return_time"]
        query = apply_sorting(
            query, DeploymentInfo, sort_by, order, allowed_sort_fields
        )

        # 分頁
        return paginate(query, skip, limit)

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

        now = datetime.now(UTC)

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
            raise DEPLOYMENT_NOT_FOUND

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
            raise DEPLOYMENT_PHASE_COLLISION

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

    def hard_delete_deployment(self, deployment_id: int) -> dict:
        """
        永久刪除 Deployment 及所有相關資料。

        包含：
        - 刪除 MinIO 中該 Deployment 下的所有物件
        - 刪除資料庫中的所有相關記錄 (Audios, Deployment)
        """
        # 查詢 Deployment (包含已軟刪除)
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.id == deployment_id)
            .first()
        )
        if not deployment:
            raise DEPLOYMENT_NOT_FOUND

        # 取得 bucket 名稱
        point = (
            self.db.query(PointInfo).filter(PointInfo.id == deployment.point_id).first()
        )
        if not point:
            raise POINT_NOT_FOUND

        project = (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.id == point.project_id)
            .first()
        )
        if not project:
            raise PROJECT_NOT_FOUND
        bucket_name = project.name

        # 取得相關 Audio
        audios = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.deployment_id == deployment_id)
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

        # 刪除 DB 記錄（FK 順序：tasks → audios → jobs → deployment）
        audio_ids = [a.id for a in audios]
        if audio_ids:
            self.db.query(UploadTask).filter(UploadTask.audio_id.in_(audio_ids)).delete(
                synchronize_session=False
            )

        self.db.query(UploadJob).filter(
            UploadJob.deployment_id == deployment_id
        ).delete(synchronize_session=False)

        deleted_audios = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.deployment_id == deployment_id)
            .delete(synchronize_session=False)
        )

        self.db.query(DeploymentInfo).filter(DeploymentInfo.id == deployment_id).delete(
            synchronize_session=False
        )

        self.db.commit()

        return {
            "message": "Deployment permanently deleted",
            "deleted_audios": deleted_audios,
        }
