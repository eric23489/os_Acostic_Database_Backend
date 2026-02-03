from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.schemas.audio import AudioCreate, AudioUpdate


class AudioService:
    def __init__(self, db: Session):
        self.db = db

    def get_audio(self, audio_id: int) -> AudioInfo:
        audio = self.db.query(AudioInfo).filter(AudioInfo.id == audio_id).first()
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
            .filter(AudioInfo.id == audio_id)
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
        query = self.db.query(AudioInfo)
        if deployment_id:
            query = query.filter(AudioInfo.deployment_id == deployment_id)
        return query.offset(skip).limit(limit).all()

    def create_audio(self, audio_in: AudioCreate) -> AudioInfo:
        # Check if object_key exists (unique constraint)
        if (
            self.db.query(AudioInfo)
            .filter(AudioInfo.object_key == audio_in.object_key)
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio with this object_key already exists",
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
