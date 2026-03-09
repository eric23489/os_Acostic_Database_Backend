import logging
from datetime import UTC, datetime

from botocore.exceptions import ClientError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    AUDIO_CONCURRENT_CONFLICT,
    AUDIO_DB_COMMIT_FAILED,
    AUDIO_NOT_FOUND,
    AUDIO_OBJECT_KEY_COLLISION,
    AUDIO_OBJECT_KEY_DUPLICATE,
    AUDIO_OBJECT_KEY_RESERVED,
    AUDIO_UPLOAD_NOT_COMPLETED,
    DEPLOYMENT_NOT_FOUND,
    MINIO_DELETE_FAILED,
    PERMISSION_RESTORE_DENIED,
    POINT_NOT_FOUND,
    PROJECT_NOT_FOUND,
)
from app.enums.enums import UploadStatus, UserRole
from app.models.audio import AudioInfo
from app.models.deployment import DeploymentInfo
from app.models.point import PointInfo
from app.models.project import ProjectInfo
from app.models.upload_job import UploadTask
from app.models.user import UserInfo
from app.schemas.audio import (
    AudioBatchCreateRequest,
    AudioBatchCreateResponse,
    AudioBatchResultItem,
    AudioCreate,
    AudioDownloadUrlResponse,
    AudioUpdate,
)
from app.schemas.pagination import SortOrder
from app.services.minio_service import MinioService
from app.utils.query import apply_filter, apply_search, apply_sorting, paginate

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
            raise AUDIO_NOT_FOUND
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
            raise AUDIO_NOT_FOUND
        return audio

    def get_audios(
        self,
        skip: int = 0,
        limit: int = 100,
        deployment_id: int | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        order: SortOrder = SortOrder.DESC,
    ) -> tuple[list[AudioInfo], int]:
        """
        取得音檔列表，支援搜尋、篩選、排序和分頁。

        Args:
            skip: 跳過的筆數
            limit: 每頁筆數上限
            deployment_id: 篩選佈放 ID (選填)
            search: 搜尋關鍵字 (搜尋 file_name, target)
            sort_by: 排序欄位 (file_name, record_time, file_size, created_at)
            order: 排序方向

        Returns:
            tuple: (items, total)
        """
        query = self.db.query(AudioInfo).filter(AudioInfo.is_deleted.is_(False))

        # 篩選
        query = apply_filter(query, AudioInfo, "deployment_id", deployment_id)

        # 搜尋
        search_fields = ["file_name", "target"]
        query = apply_search(query, AudioInfo, search_fields, search)

        # 排序
        allowed_sort_fields = ["file_name", "record_time", "file_size", "created_at"]
        query = apply_sorting(query, AudioInfo, sort_by, order, allowed_sort_fields)

        # 分頁
        return paginate(query, skip, limit)

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
            raise AUDIO_OBJECT_KEY_DUPLICATE

        # Check if object_key is reserved by a soft-deleted audio
        if (
            self.db.query(AudioInfo)
            .filter(
                AudioInfo.object_key == audio_in.object_key,
                AudioInfo.is_deleted.is_(True),
            )
            .first()
        ):
            raise AUDIO_OBJECT_KEY_RESERVED

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

    def restore_audio(self, audio_id: int, current_user: UserInfo) -> AudioInfo:
        """
        還原軟刪除的 Audio。僅允許原刪除者或 Admin 執行。

        Args:
            audio_id: Audio ID
            current_user: 執行還原的使用者
        """
        audio = self.db.query(AudioInfo).filter(AudioInfo.id == audio_id).first()
        if not audio:
            raise AUDIO_NOT_FOUND

        is_admin = current_user.role == UserRole.ADMIN.value
        if not is_admin and current_user.id != audio.deleted_by:
            raise PERMISSION_RESTORE_DENIED

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
            raise AUDIO_OBJECT_KEY_COLLISION

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
            raise AUDIO_NOT_FOUND

        # 取得 bucket 名稱
        deployment = (
            self.db.query(DeploymentInfo)
            .filter(DeploymentInfo.id == audio.deployment_id)
            .first()
        )
        if not deployment:
            raise DEPLOYMENT_NOT_FOUND

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

        # 刪除 MinIO 物件（bucket 或 object 不存在視為已清理）
        minio_service = MinioService()
        try:
            minio_service.delete_object(bucket_name, audio.object_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchBucket", "NoSuchKey"):
                logger.warning(
                    "MinIO object/bucket not found during hard delete, skipping. "
                    "object_key=%s bucket=%s",
                    audio.object_key,
                    bucket_name,
                )
            else:
                logger.error(
                    "Failed to delete MinIO object during hard delete. "
                    "object_key=%s bucket=%s error=%s",
                    audio.object_key,
                    bucket_name,
                    e,
                )
                raise MINIO_DELETE_FAILED from None

        # 刪除關聯的 upload_tasks（FK 無 CASCADE，需先刪）
        self.db.query(UploadTask).filter(UploadTask.audio_id == audio_id).delete()

        # 刪除 DB 記錄
        self.db.query(AudioInfo).filter(AudioInfo.id == audio_id).delete()
        self.db.commit()

        return {"message": "Audio permanently deleted"}

    def create_audios_batch(
        self,
        request: AudioBatchCreateRequest,
    ) -> AudioBatchCreateResponse:
        """
        批量建立 AudioInfo。

        使用冪等設計：
        - 活躍的 object_key 已存在 → skipped，回傳既有 audio_id
        - 軟刪除的 object_key 已佔用 → skipped，需 hard delete 釋放
        - 批次內重複的 object_key → 第一筆通過，後續 skipped
        - 全部成功回傳 201，部分跳過由 router 回傳 207

        Args:
            request: 批量建立請求

        Returns:
            AudioBatchCreateResponse
        """
        deployment_id = request.deployment_id

        deployment = (
            self.db.query(DeploymentInfo)
            .filter(
                DeploymentInfo.id == deployment_id,
                DeploymentInfo.is_deleted.is_(False),
            )
            .first()
        )
        if not deployment:
            raise DEPLOYMENT_NOT_FOUND

        object_keys = [item.object_key for item in request.audios]
        active_keys = self._get_existing_active_keys(set(object_keys))
        deleted_keys = self._get_existing_deleted_keys(set(object_keys))

        indexed_results: dict[int, AudioBatchResultItem] = {}
        to_create: list[tuple[int, AudioInfo]] = []  # (index, AudioInfo)
        seen_keys: set[str] = set()

        for idx, item in enumerate(request.audios):
            if item.object_key in seen_keys:
                indexed_results[idx] = AudioBatchResultItem(
                    file_name=item.file_name,
                    object_key=item.object_key,
                    status="skipped",
                    reason="Duplicate object_key within batch",
                )
                continue

            seen_keys.add(item.object_key)

            if item.object_key in active_keys:
                existing = (
                    self.db.query(AudioInfo.id)
                    .filter(
                        AudioInfo.object_key == item.object_key,
                        AudioInfo.is_deleted.is_(False),
                    )
                    .scalar()
                )
                indexed_results[idx] = AudioBatchResultItem(
                    file_name=item.file_name,
                    object_key=item.object_key,
                    status="skipped",
                    audio_id=existing,
                    reason="Already exists",
                )
                continue

            if item.object_key in deleted_keys:
                indexed_results[idx] = AudioBatchResultItem(
                    file_name=item.file_name,
                    object_key=item.object_key,
                    status="skipped",
                    reason="Reserved by deleted record. Hard delete to release.",
                )
                continue

            audio = AudioInfo(
                deployment_id=deployment_id,
                file_name=item.file_name,
                object_key=item.object_key,
                file_format=item.file_format,
                file_size=item.file_size,
                checksum=item.checksum,
                record_time=item.record_time,
                record_duration=item.record_duration,
                fs=item.fs,
                recorder_channel=item.recorder_channel,
                audio_channels=item.audio_channels,
                target=item.target,
                target_type=item.target_type,
                meta_json=item.meta_json,
                is_cold_storage=item.is_cold_storage,
            )
            self.db.add(audio)
            to_create.append((idx, audio))

        # C4：flush 可能因並發競爭拋出 IntegrityError
        try:
            self.db.flush()
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(
                "create_audios_batch flush IntegrityError"
                " (concurrent write conflict): %s",
                e,
            )
            raise AUDIO_CONCURRENT_CONFLICT from None

        # 補充 created 結果（flush 後才有 ID）
        for idx, audio in to_create:
            item = request.audios[idx]
            indexed_results[idx] = AudioBatchResultItem(
                file_name=item.file_name,
                object_key=item.object_key,
                status="created",
                audio_id=audio.id,
            )

        # C8：commit 失敗代表 DB 問題，已 flush 的 ID 無法使用
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(
                "create_audios_batch commit failed. deployment_id=%s error=%s",
                deployment_id,
                e,
            )
            raise AUDIO_DB_COMMIT_FAILED from None

        # 依照原始順序重建結果列表，正確處理 batch 內重複 key 的排序
        results = [indexed_results[i] for i in range(len(request.audios))]
        success_count = sum(1 for r in results if r.status == "created")
        skipped_count = sum(1 for r in results if r.status == "skipped")
        failed_count = sum(1 for r in results if r.status == "failed")

        return AudioBatchCreateResponse(
            deployment_id=deployment_id,
            total_count=len(results),
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            results=results,
        )

    def _get_existing_active_keys(self, object_keys: set[str]) -> set[str]:
        """批量查詢已存在的活躍 object_keys。"""
        if not object_keys:
            return set()
        return {
            r[0]
            for r in self.db.query(AudioInfo.object_key)
            .filter(
                AudioInfo.object_key.in_(object_keys),
                AudioInfo.is_deleted.is_(False),
            )
            .all()
        }

    def _get_existing_deleted_keys(self, object_keys: set[str]) -> set[str]:
        """批量查詢已軟刪除的 object_keys。"""
        if not object_keys:
            return set()
        return {
            r[0]
            for r in self.db.query(AudioInfo.object_key)
            .filter(
                AudioInfo.object_key.in_(object_keys),
                AudioInfo.is_deleted.is_(True),
            )
            .all()
        }

    def get_download_url(
        self, audio_id: int, expires_in: int = 3600
    ) -> AudioDownloadUrlResponse:
        """
        取得 Audio 下載 URL。

        Args:
            audio_id: Audio ID
            expires_in: URL 有效期 (秒)，預設 3600

        Returns:
            AudioDownloadUrlResponse: 包含 presigned URL 和檔案資訊
        """
        # 查詢 Audio (含關聯到 Project)
        audio = (
            self.db.query(AudioInfo)
            .options(
                joinedload(AudioInfo.deployment)
                .joinedload(DeploymentInfo.point)
                .joinedload(PointInfo.project)
            )
            .filter(AudioInfo.id == audio_id, AudioInfo.is_deleted.is_(False))
            .first()
        )
        if not audio:
            raise AUDIO_NOT_FOUND

        # 驗證上傳狀態
        if audio.upload_status != UploadStatus.COMPLETED:
            raise AUDIO_UPLOAD_NOT_COMPLETED

        # 取得 bucket 名稱 (project.name)
        bucket_name = audio.deployment.point.project.name

        # 產生 presigned URL
        minio_service = MinioService()
        presigned_url = minio_service.generate_presigned_url(
            bucket=bucket_name,
            key=audio.object_key,
            expires_in=expires_in,
            method="get_object",
        )

        return AudioDownloadUrlResponse(
            presigned_url=presigned_url,
            expires_in=expires_in,
            file_name=audio.file_name,
            file_size=audio.file_size,
        )
