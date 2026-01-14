from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exists

from app.models.recorder import RecorderInfo
from app.schemas.recorder import RecorderCreate, RecorderUpdate


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
        self, recorder_id: int, recorder_in: RecorderUpdate
    ) -> RecorderInfo:
        db_recorder = self.get_recorder(recorder_id)

        update_data = recorder_in.model_dump(exclude_unset=True)

        # Check if unique constraint fields are being updated
        new_brand = update_data.get("brand", db_recorder.brand)
        new_model = update_data.get("model", db_recorder.model)
        new_sn = update_data.get("sn", db_recorder.sn)

        if (
            new_brand != db_recorder.brand
            or new_model != db_recorder.model
            or new_sn != db_recorder.sn
        ):
            if self.check_recorder_exists(new_brand, new_model, new_sn):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Recorder with brand '{new_brand}', model '{new_model}', and SN '{new_sn}' already exists.",
                )

        for field, value in update_data.items():
            setattr(db_recorder, field, value)

        self.db.commit()
        self.db.refresh(db_recorder)

        return db_recorder
