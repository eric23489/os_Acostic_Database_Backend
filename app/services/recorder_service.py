from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exists

from app.models.recorder import RecorderInfo
from app.schemas.recorder import RecorderCreate, RecorderBase


class RecorderService:
    def __init__(self, db: Session):
        self.db = db

    def check_recorder_exists(self, brand, model, sn) -> bool:
        return self.db.query(
            exists().where(
                RecorderInfo.brand == brand,
                RecorderInfo.model == model,
                RecorderInfo.sn == sn,
            )
        ).scalar()

    def get_recorder(self, recorder_id: int) -> RecorderInfo:
        recorder = (
            self.db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).first()
        )
        if not recorder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recorder with ID {recorder_id} not found.",
            )
        return recorder

    def get_recorders(self, skip: int = 0, limit: int = 100) -> list[RecorderInfo]:
        return self.db.query(RecorderInfo).offset(skip).limit(limit).all()

    def create_recorder(self, recorder: RecorderCreate) -> RecorderInfo:
        if self.check_recorder_exists(recorder.brand, recorder.model, recorder.sn):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recorder with brand '{recorder.brand}', model '{recorder.model}', and SN '{recorder.sn}' already exists.",
            )

        db_recorder = RecorderInfo(
            brand=recorder.brand,
            model=recorder.model,
            sn=recorder.sn,
            sensitivity=recorder.sensitivity,
            high_gain=recorder.high_gain,
            low_gain=recorder.low_gain,
            status=recorder.status,
            owner=recorder.owner,
            recorder_channels=recorder.recorder_channels,
            description=recorder.description,
        )

        self.db.add(db_recorder)
        self.db.commit()
        self.db.refresh(db_recorder)

        return db_recorder

    def update_recorder(
        self, recorder_id: int, recorder: RecorderCreate
    ) -> RecorderInfo:
        db_recorder = self.get_recorder(recorder_id)

        if (
            db_recorder.brand != recorder.brand
            or db_recorder.model != recorder.model
            or db_recorder.sn != recorder.sn
        ):
            if self.check_recorder_exists(recorder.brand, recorder.model, recorder.sn):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Recorder with brand '{recorder.brand}', model '{recorder.model}', and SN '{recorder.sn}' already exists.",
                )

        db_recorder.brand = recorder.brand
        db_recorder.model = recorder.model
        db_recorder.sn = recorder.sn
        db_recorder.sensitivity = recorder.sensitivity
        db_recorder.high_gain = recorder.high_gain
        db_recorder.low_gain = recorder.low_gain
        db_recorder.status = recorder.status
        db_recorder.owner = recorder.owner
        db_recorder.recorder_channels = recorder.recorder_channels
        db_recorder.description = recorder.description

        self.db.commit()
        self.db.refresh(db_recorder)

        return db_recorder
