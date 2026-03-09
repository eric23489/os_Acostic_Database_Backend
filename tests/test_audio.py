"""
tests/test_audio.py

POST /audio/batch 端點與 AudioBatchResultItem 型別不變量測試。
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import DEPLOYMENT_NOT_FOUND, AppException
from app.schemas.audio import (
    AudioBatchCreateRequest,
    AudioBatchCreateResponse,
    AudioBatchResultItem,
)
from app.services.upload_job_service import UploadJobService

# =============================================================================
# AudioBatchResultItem 型別不變量測試 (C5)
# =============================================================================


class TestAudioBatchResultItem:
    """驗證 AudioBatchResultItem 的跨欄位不變量。"""

    def test_created_with_audio_id_is_valid(self):
        item = AudioBatchResultItem(
            file_name="a.wav",
            object_key="key/a.wav",
            status="created",
            audio_id=42,
        )
        assert item.audio_id == 42
        assert item.reason is None

    def test_created_without_audio_id_raises(self):
        with pytest.raises(ValidationError, match="audio_id is required"):
            AudioBatchResultItem(
                file_name="a.wav",
                object_key="key/a.wav",
                status="created",
                audio_id=None,
            )

    def test_skipped_with_reason_is_valid(self):
        item = AudioBatchResultItem(
            file_name="a.wav",
            object_key="key/a.wav",
            status="skipped",
            reason="Already exists",
        )
        assert item.audio_id is None
        assert item.reason == "Already exists"

    def test_skipped_without_reason_raises(self):
        with pytest.raises(ValidationError, match="reason is required"):
            AudioBatchResultItem(
                file_name="a.wav",
                object_key="key/a.wav",
                status="skipped",
            )

    def test_failed_with_reason_is_valid(self):
        item = AudioBatchResultItem(
            file_name="a.wav",
            object_key="key/a.wav",
            status="failed",
            reason="DB error",
        )
        assert item.reason == "DB error"

    def test_failed_without_reason_raises(self):
        with pytest.raises(ValidationError, match="reason is required"):
            AudioBatchResultItem(
                file_name="a.wav",
                object_key="key/a.wav",
                status="failed",
            )

    def test_skipped_with_audio_id_for_collision_is_valid(self):
        """active key 碰撞時，skipped 可同時帶 audio_id 和 reason。"""
        item = AudioBatchResultItem(
            file_name="a.wav",
            object_key="key/a.wav",
            status="skipped",
            audio_id=99,
            reason="Already exists",
        )
        assert item.audio_id == 99


# =============================================================================
# AudioBatchCreateRequest 驗證測試
# =============================================================================


class TestAudioBatchCreateRequest:
    """驗證批次大小邊界。"""

    def _make_item(self, key: str = "key/a.wav") -> dict:
        return {"file_name": "a.wav", "object_key": key}

    def test_empty_list_raises(self):
        with pytest.raises(ValidationError, match="At least 1 audio required"):
            AudioBatchCreateRequest(deployment_id=1, audios=[])

    def test_one_item_is_valid(self):
        req = AudioBatchCreateRequest(deployment_id=1, audios=[self._make_item()])
        assert len(req.audios) == 1

    def test_100_items_is_valid(self):
        items = [self._make_item(f"key/{i}.wav") for i in range(100)]
        req = AudioBatchCreateRequest(deployment_id=1, audios=items)
        assert len(req.audios) == 100

    def test_101_items_raises(self):
        items = [self._make_item(f"key/{i}.wav") for i in range(101)]
        with pytest.raises(ValidationError, match="Maximum 100 audios per batch"):
            AudioBatchCreateRequest(deployment_id=1, audios=items)


# =============================================================================
# POST /audio/batch 端點測試 (C7)
# =============================================================================


class TestCreateAudiosBatchEndpoint:
    """POST /audio/batch 路由層整合測試（mock service）。"""

    BASE_URL = f"{settings.api_prefix}/audio/batch"

    def _make_response(self, **overrides) -> AudioBatchCreateResponse:
        defaults = dict(
            deployment_id=1,
            total_count=2,
            success_count=2,
            skipped_count=0,
            failed_count=0,
            results=[
                AudioBatchResultItem(
                    file_name="a.wav",
                    object_key="key/a.wav",
                    status="created",
                    audio_id=1,
                ),
                AudioBatchResultItem(
                    file_name="b.wav",
                    object_key="key/b.wav",
                    status="created",
                    audio_id=2,
                ),
            ],
        )
        defaults.update(overrides)
        return AudioBatchCreateResponse(**defaults)

    def test_all_created_returns_201(self, client):
        response = self._make_response()
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            MockService.return_value.create_audios_batch.return_value = response
            res = client.post(
                self.BASE_URL,
                json={
                    "deployment_id": 1,
                    "audios": [
                        {"file_name": "a.wav", "object_key": "key/a.wav"},
                        {"file_name": "b.wav", "object_key": "key/b.wav"},
                    ],
                },
            )
        assert res.status_code == 201
        data = res.json()
        assert data["success_count"] == 2
        assert data["skipped_count"] == 0
        assert all(r["status"] == "created" for r in data["results"])

    def test_partial_skip_returns_207(self, client):
        response = AudioBatchCreateResponse(
            deployment_id=1,
            total_count=2,
            success_count=1,
            skipped_count=1,
            failed_count=0,
            results=[
                AudioBatchResultItem(
                    file_name="a.wav",
                    object_key="key/a.wav",
                    status="created",
                    audio_id=1,
                ),
                AudioBatchResultItem(
                    file_name="b.wav",
                    object_key="key/b.wav",
                    status="skipped",
                    audio_id=99,
                    reason="Already exists",
                ),
            ],
        )
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            MockService.return_value.create_audios_batch.return_value = response
            res = client.post(
                self.BASE_URL,
                json={
                    "deployment_id": 1,
                    "audios": [
                        {"file_name": "a.wav", "object_key": "key/a.wav"},
                        {"file_name": "b.wav", "object_key": "key/b.wav"},
                    ],
                },
            )
        assert res.status_code == 207
        data = res.json()
        assert data["skipped_count"] == 1
        skipped = next(r for r in data["results"] if r["status"] == "skipped")
        assert skipped["audio_id"] == 99
        assert skipped["reason"] == "Already exists"

    def test_deployment_not_found_returns_404(self, client):
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            MockService.return_value.create_audios_batch.side_effect = (
                DEPLOYMENT_NOT_FOUND
            )
            res = client.post(
                self.BASE_URL,
                json={
                    "deployment_id": 999,
                    "audios": [
                        {"file_name": "a.wav", "object_key": "key/a.wav"},
                    ],
                },
            )
        assert res.status_code == 404
        assert res.json()["message"] == "Deployment not found"

    def test_empty_audios_returns_422(self, client):
        res = client.post(
            self.BASE_URL,
            json={"deployment_id": 1, "audios": []},
        )
        assert res.status_code == 422

    def test_over_100_audios_returns_422(self, client):
        audios = [
            {"file_name": f"{i}.wav", "object_key": f"key/{i}.wav"} for i in range(101)
        ]
        res = client.post(
            self.BASE_URL,
            json={"deployment_id": 1, "audios": audios},
        )
        assert res.status_code == 422

    def test_all_skipped_with_soft_deleted_keys_returns_207(self, client):
        response = AudioBatchCreateResponse(
            deployment_id=1,
            total_count=1,
            success_count=0,
            skipped_count=1,
            failed_count=0,
            results=[
                AudioBatchResultItem(
                    file_name="a.wav",
                    object_key="key/a.wav",
                    status="skipped",
                    reason="Reserved by deleted record. Hard delete to release.",
                ),
            ],
        )
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            MockService.return_value.create_audios_batch.return_value = response
            res = client.post(
                self.BASE_URL,
                json={
                    "deployment_id": 1,
                    "audios": [
                        {"file_name": "a.wav", "object_key": "key/a.wav"},
                    ],
                },
            )
        assert res.status_code == 207
        result = res.json()["results"][0]
        assert result["status"] == "skipped"
        assert "Hard delete" in result["reason"]

    def test_concurrent_conflict_returns_409(self, client):
        with patch("app.api.v1.endpoints.api_audio.AudioService") as MockService:
            MockService.return_value.create_audios_batch.side_effect = HTTPException(
                status_code=409,
                detail="Concurrent write conflict on object_key. Please retry.",
            )
            res = client.post(
                self.BASE_URL,
                json={
                    "deployment_id": 1,
                    "audios": [
                        {"file_name": "a.wav", "object_key": "key/a.wav"},
                    ],
                },
            )
        assert res.status_code == 409


# =============================================================================
# _get_task IDOR 保護測試 (C9)
# =============================================================================


class TestGetTaskIDOR:
    """_get_task 的 IDOR 保護：非擁有者取得 404，不洩漏資源是否存在。"""

    def _make_db(self, result) -> MagicMock:
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.first.return_value = result
        return db

    def test_wrong_user_raises_404_not_403(self):
        """其他使用者的 task → 404，避免洩漏資源存在。"""
        db = self._make_db(result=None)
        service = UploadJobService(db)

        with pytest.raises(AppException) as exc_info:
            service._get_task("job-1", "task-1", user_id=99)

        assert exc_info.value.http_status == 404
        assert exc_info.value.message == "Task not found"

    def test_correct_user_returns_task(self):
        """擁有者查詢自己的 task → 成功回傳。"""
        task = MagicMock()
        db = self._make_db(result=task)
        service = UploadJobService(db)

        result = service._get_task("job-1", "task-1", user_id=1)

        assert result is task
