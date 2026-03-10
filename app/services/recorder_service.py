from datetime import UTC, datetime

from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from app.core.exceptions import (
    PERMISSION_RESTORE_DENIED,
    RECORDER_HAS_DEPLOYMENTS,
    RECORDER_IDENTIFIER_DUPLICATE,
    RECORDER_IDENTIFIER_RESERVED,
    RECORDER_NOT_FOUND,
)
from app.enums.enums import RecorderStatus, UserRole
from app.models.deployment import DeploymentInfo
from app.models.recorder import RecorderInfo
from app.schemas.common import MessageResponse
from app.schemas.pagination import SortOrder
from app.schemas.recorder import RecorderCreate, RecorderStatsResponse, RecorderUpdate
from app.utils.query import apply_filter, apply_search, apply_sorting, paginate


class RecorderService:
    def __init__(self, db: Session):
        self.db = db

    def get_recorder_stats(self) -> RecorderStatsResponse:
        """回傳可用與佈放中的儀器數量統計。"""
        rows = (
            self.db.query(RecorderInfo.status, func.count(RecorderInfo.id))
            .filter(
                RecorderInfo.status.in_(
                    [RecorderStatus.AVAILABLE, RecorderStatus.DEPLOYING]
                ),
                RecorderInfo.is_deleted.is_(False),
            )
            .group_by(RecorderInfo.status)
            .all()
        )
        count_map = {status: count for status, count in rows}
        return RecorderStatsResponse(
            available_count=count_map.get(RecorderStatus.AVAILABLE, 0),
            deploying_count=count_map.get(RecorderStatus.DEPLOYING, 0),
        )

    def check_recorder_exists(self, brand: str, model: str, sn: str) -> bool:
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
            raise RECORDER_NOT_FOUND
        return recorder

    def get_recorders(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: RecorderStatus | None = None,
        sort_by: str | None = None,
        order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[RecorderInfo], int]:
        """
        取得錄音器列表，支援搜尋、篩選、排序和分頁。

        Args:
            skip: 跳過的筆數
            limit: 每頁筆數上限
            search: 搜尋關鍵字 (搜尋 brand, model, sn, owner)
            status: 篩選狀態
            sort_by: 排序欄位 (brand, model, sn, created_at)
            order: 排序方向

        Returns:
            tuple: (items, total)
        """
        query = self.db.query(RecorderInfo).filter(RecorderInfo.is_deleted.is_(False))

        # 搜尋
        search_fields = ["brand", "model", "sn", "owner"]
        query = apply_search(query, RecorderInfo, search_fields, search)

        # 篩選
        query = apply_filter(query, RecorderInfo, "status", status)

        # 排序
        allowed_sort_fields = ["brand", "model", "sn", "created_at"]
        query = apply_sorting(query, RecorderInfo, sort_by, order, allowed_sort_fields)

        # 分頁
        return paginate(query, skip, limit)

    def check_soft_deleted_recorder_exists(
        self, brand: str, model: str, sn: str
    ) -> bool:
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
            raise RECORDER_IDENTIFIER_DUPLICATE

        # 檢查軟刪除名稱保留
        if self.check_soft_deleted_recorder_exists(
            recorder.brand, recorder.model, recorder.sn
        ):
            raise RECORDER_IDENTIFIER_RESERVED

        db_recorder = RecorderInfo(
            brand=recorder.brand,
            model=recorder.model,
            sn=recorder.sn,
            sensitivity=recorder.sensitivity,
            high_gain=recorder.high_gain,
            low_gain=recorder.low_gain,
            bits=recorder.bits,
            status=recorder.status,
            owner=recorder.owner,
            recorder_channels=recorder.recorder_channels,
            description=recorder.description,
            measured_sensitivity=recorder.measured_sensitivity,
            standard_sensitivity=recorder.standard_sensitivity,
            calibration_date=recorder.calibration_date,
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
                raise RECORDER_IDENTIFIER_DUPLICATE
            if self.check_soft_deleted_recorder_exists(new_brand, new_model, new_sn):
                raise RECORDER_IDENTIFIER_RESERVED

        for field, value in update_data.items():
            setattr(db_recorder, field, value)

        self.db.add(db_recorder)
        self.db.commit()
        self.db.refresh(db_recorder)

        return db_recorder

    def delete_recorder(self, recorder_id: int, user_id: int) -> RecorderInfo:
        recorder = self.get_recorder(recorder_id)
        recorder.is_deleted = True
        recorder.deleted_at = datetime.now(UTC)
        recorder.deleted_by = user_id
        self.db.add(recorder)
        self.db.commit()
        self.db.refresh(recorder)
        return recorder

    def restore_recorder(
        self, recorder_id: int, current_user_id: int, current_user_role: str
    ) -> RecorderInfo:
        recorder = (
            self.db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).first()
        )
        if not recorder:
            raise RECORDER_NOT_FOUND

        if (
            current_user_role != UserRole.ADMIN.value
            and current_user_id != recorder.deleted_by
        ):
            raise PERMISSION_RESTORE_DENIED

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
            raise RECORDER_IDENTIFIER_DUPLICATE

        recorder.is_deleted = False
        recorder.deleted_at = None
        recorder.deleted_by = None
        self.db.add(recorder)
        self.db.commit()
        self.db.refresh(recorder)
        return recorder

    def hard_delete_recorder(self, recorder_id: int) -> MessageResponse:
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
            raise RECORDER_NOT_FOUND

        # 檢查是否有 Deployment 引用此 Recorder（含軟刪除）
        deployment_count = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.recorder_id == recorder_id)
            .count()
        )
        if deployment_count > 0:
            raise RECORDER_HAS_DEPLOYMENTS

        # 記錄識別資訊
        recorder_identifier = f"{recorder.brand}/{recorder.model}/{recorder.sn}"

        # 刪除 DB 記錄
        self.db.query(RecorderInfo).filter(RecorderInfo.id == recorder_id).delete()
        self.db.commit()

        return MessageResponse(
            message=f"Recorder '{recorder_identifier}' permanently deleted"
        )
