import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.minio import get_s3_client
from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.schemas.audio import AudioCreate, AudioUpdate

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self, db: Session):
        self.db = db

    def get_audio(self, audio_id: int) -> AudioInfo:
        audio = (
            self.db.query(AudioInfo)
            .filter(AudioInfo.id == audio_id, AudioInfo.is_deleted.is_(False))
            .first()
        )
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio not found",
            )
        return audio

    def get_audio_details(self, audio_id: int) -> AudioInfo:
        audio = (
            self.db.query(AudioInfo)
            .options(
                joinedload(AudioInfo.deployment)
                .joinedload(DeploymentInfo.point)
                .joinedload(PointInfo.project),
                joinedload(AudioInfo.deployment).joinedload(DeploymentInfo.recorder),
            )
            .filter(AudioInfo.id == audio_id, AudioInfo.is_deleted.is_(False))
            .first()
        )
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found"
            )
        return audio

    def get_audios(
        self, deployment_id: int | None = None, skip: int = 0, limit: int = 100
    ) -> list[AudioInfo]:
        query = self.db.query(AudioInfo).filter(AudioInfo.is_deleted.is_(False))
        if deployment_id:
            query = query.filter(AudioInfo.deployment_id == deployment_id)
        return query.offset(skip).limit(limit).all()

    def create_audio(self, audio_in: AudioCreate) -> AudioInfo:
        # Check if object_key exists (unique constraint)
        if (
            self.db.query(AudioInfo)
            .filter(
                AudioInfo.object_key == audio_in.object_key,
                AudioInfo.is_deleted.is_(False),
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio with this object_key already exists",
            )

        # Check if object_key is reserved by a soft-deleted audio
        if (
            self.db.query(AudioInfo)
            .filter(
                AudioInfo.object_key == audio_in.object_key,
                AudioInfo.is_deleted.is_(True),
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="object_key reserved by deleted audio. Hard delete to release.",
            )

        audio_data = audio_in.model_dump()
        db_obj = AudioInfo(**audio_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update_audio(self, audio_id: int, audio_in: AudioUpdate) -> AudioInfo:
        audio = self.get_audio(audio_id)
        update_data = audio_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(audio, field, value)

        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def delete_audio(self, audio_id: int, user_id: int) -> AudioInfo:
        audio = self.get_audio(audio_id)
        audio.is_deleted = True
        audio.deleted_at = datetime.now(UTC)
        audio.deleted_by = user_id
        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def restore_audio(self, audio_id: int) -> AudioInfo:
        audio = self.db.query(AudioInfo).filter(AudioInfo.id == audio_id).first()
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio not found",
            )

        # Check for object_key collision
        if (
            self.db.query(AudioInfo)
            .filter(
                AudioInfo.object_key == audio.object_key,
                AudioInfo.is_deleted.is_(False),
                AudioInfo.id != audio_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active audio with this object_key already exists. Cannot restore.",
            )

        audio.is_deleted = False
        audio.deleted_at = None
        audio.deleted_by = None
        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def hard_delete_audio(self, audio_id: int) -> dict:
        """
        永久刪除單一 Audio。

        包含：
        - 刪除 MinIO 物件
        - 刪除資料庫記錄
        - 釋放 object_key，可重新使用
        """
        # 查詢 Audio (包含已軟刪除)
        audio = self.db.query(AudioInfo).filter(AudioInfo.id == audio_id).first()
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio not found",
            )

        # 取得 bucket 名稱
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.id == audio.deployment_id)
            .first()
        )
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent deployment not found",
            )

        point = (
            self.db.query(PointInfo).filter(PointInfo.id == deployment.point_id).first()
        )
        if not point:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent point not found",
            )

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

        # 刪除 MinIO 物件
        s3_client = get_s3_client()
        try:
            s3_client.delete_object(Bucket=bucket_name, Key=audio.object_key)
        except Exception as e:
            logger.warning(f"Failed to delete object {audio.object_key}: {e}")

        # 刪除 DB 記錄
        self.db.query(AudioInfo).filter(AudioInfo.id == audio_id).delete()
        self.db.commit()

        return {"message": "Audio permanently deleted"}
