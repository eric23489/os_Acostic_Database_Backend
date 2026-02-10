from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exists

from app.models.deployment import DeploymentInfo
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
                RecorderInfo.is_deleted.is_(False),
            )
        ).scalar()

    def get_recorder(self, recorder_id: int) -> RecorderInfo:
        recorder = (
            self.db.query(RecorderInfo)
            .filter(RecorderInfo.id == recorder_id, RecorderInfo.is_deleted.is_(False))
            .first()
        )
        if not recorder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recorder with ID {recorder_id} not found.",
            )
        return recorder

    def get_recorders(self, skip: int = 0, limit: int = 100) -> list[RecorderInfo]:
        return (
            self.db.query(RecorderInfo)
            .filter(RecorderInfo.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def check_soft_deleted_recorder_exists(self, brand: str, model: str, sn: str) -> bool:
        """檢查是否有軟刪除的 Recorder 佔用此識別碼。"""
        return self.db.query(
            exists().where(
                RecorderInfo.brand == brand,
                RecorderInfo.model == model,
                RecorderInfo.sn == sn,
                RecorderInfo.is_deleted.is_(True),
            )
        ).scalar()

    def create_recorder(self, recorder: RecorderCreate) -> RecorderInfo:
        if self.check_recorder_exists(recorder.brand, recorder.model, recorder.sn):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recorder with brand '{recorder.brand}', model '{recorder.model}', and SN '{recorder.sn}' already exists.",
            )

        # 檢查軟刪除名稱保留
        if self.check_soft_deleted_recorder_exists(
            recorder.brand, recorder.model, recorder.sn
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identifier reserved by deleted recorder. Hard delete to release.",
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

        self.db.add(db_recorder)
        self.db.commit()
        self.db.refresh(db_recorder)

        return db_recorder

    def delete_recorder(self, recorder_id: int, user_id: int) -> RecorderInfo:
        recorder = self.get_recorder(recorder_id)
        recorder.is_deleted = True
        recorder.deleted_at = datetime.now(timezone.utc)
        recorder.deleted_by = user_id
        self.db.add(recorder)
        self.db.commit()
        self.db.refresh(recorder)
        return recorder

    def restore_recorder(self, recorder_id: int) -> RecorderInfo:
        recorder = (
            self.db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).first()
        )
        if not recorder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recorder with ID {recorder_id} not found.",
            )

        # Check for unique constraint collision before restore
        if (
            self.db.query(RecorderInfo)
            .filter(
                RecorderInfo.brand == recorder.brand,
                RecorderInfo.model == recorder.model,
                RecorderInfo.sn == recorder.sn,
                RecorderInfo.is_deleted.is_(False),
                RecorderInfo.id != recorder_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active recorder with this brand/model/sn already exists. Cannot restore.",
            )

        recorder.is_deleted = False
        recorder.deleted_at = None
        recorder.deleted_by = None
        self.db.add(recorder)
        self.db.commit()
        self.db.refresh(recorder)
        return recorder

    def hard_delete_recorder(self, recorder_id: int) -> dict:
        """
        永久刪除 Recorder。

        包含：
        - 檢查是否有 Deployment 引用此 Recorder
        - 刪除資料庫記錄
        - 釋放 brand/model/sn 識別碼，可重新使用
        """
        # 查詢 Recorder (包含已軟刪除)
        recorder = (
            self.db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).first()
        )
        if not recorder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recorder not found",
            )

        # 檢查是否有 Deployment 引用此 Recorder
        deployment_count = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.recorder_id == recorder_id)
            .count()
        )
        if deployment_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete recorder: {deployment_count} deployment(s) reference this recorder. Delete deployments first.",
            )

        # 記錄識別資訊
        recorder_identifier = f"{recorder.brand}/{recorder.model}/{recorder.sn}"

        # 刪除 DB 記錄
        self.db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).delete()
        self.db.commit()

        return {"message": f"Recorder '{recorder_identifier}' permanently deleted"}
