import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from app.schemas.audio import AudioBase, AudioBatchItem, AudioUpdate
from app.schemas.deployment import DeploymentBase, DeploymentUpdate
from app.schemas.project import ProjectCreate, ProjectResponse


def test_datetime_timezone_validator():
    """
    Test that a naive datetime input (no timezone) is automatically
    converted to UTC+8 (Taiwan time).
    """
    # Input naive datetime: 2024-01-01 12:00:00
    naive_dt = datetime(2024, 1, 1, 12, 0, 0)
    project = ProjectCreate(name="test-project", start_time=naive_dt)

    # Should be converted to aware datetime with UTC+8
    assert project.start_time.tzinfo is not None
    assert project.start_time.utcoffset() == timedelta(hours=8)
    assert project.start_time.hour == 12  # Hour should remain 12


def test_datetime_serializer():
    """
    Test that datetime fields are serialized to ISO 8601 format with +08:00 timezone.
    """
    # Simulate a UTC datetime from database (e.g., 04:00 UTC = 12:00 UTC+8)
    utc_dt = datetime(2024, 1, 1, 4, 0, 0, tzinfo=timezone.utc)
    project = ProjectResponse(id=1, name="test-project", start_time=utc_dt)

    # Dump model to JSON-compatible dict
    data = project.model_dump(mode="json")

    # Check string format
    assert data["start_time"] == "2024-01-01T12:00:00+08:00"


# =============================================================================
# fs 欄位驗證測試
# =============================================================================

_DEPLOYMENT_BASE_REQUIRED = {"point_id": 1, "recorder_id": 1}
_AUDIO_BASE_REQUIRED = {
    "deployment_id": 1,
    "file_name": "test.wav",
    "object_key": "bucket/test.wav",
}
_AUDIO_BATCH_REQUIRED = {"file_name": "test.wav", "object_key": "bucket/test.wav"}


@pytest.mark.parametrize(
    "schema_cls,required_fields,fs_value",
    [
        (DeploymentBase, _DEPLOYMENT_BASE_REQUIRED, 0),
        (DeploymentBase, _DEPLOYMENT_BASE_REQUIRED, 100),
        (DeploymentBase, _DEPLOYMENT_BASE_REQUIRED, 384000),
        (DeploymentUpdate, {}, 0),
        (DeploymentUpdate, {}, 100),
        (DeploymentUpdate, {}, 384000),
        (AudioBase, _AUDIO_BASE_REQUIRED, 0),
        (AudioBase, _AUDIO_BASE_REQUIRED, 100),
        (AudioBase, _AUDIO_BASE_REQUIRED, 384000),
        (AudioUpdate, {}, 0),
        (AudioUpdate, {}, 100),
        (AudioUpdate, {}, 384000),
        (AudioBatchItem, _AUDIO_BATCH_REQUIRED, 0),
        (AudioBatchItem, _AUDIO_BATCH_REQUIRED, 100),
        (AudioBatchItem, _AUDIO_BATCH_REQUIRED, 384000),
    ],
)
def test_fs_valid_values(schema_cls, required_fields, fs_value):
    """fs 合法值（0、低採樣率、上限）應通過驗證。"""
    instance = schema_cls(**required_fields, fs=fs_value)
    assert instance.fs == fs_value


@pytest.mark.parametrize(
    "schema_cls,required_fields,fs_value",
    [
        (DeploymentBase, _DEPLOYMENT_BASE_REQUIRED, -1),
        (DeploymentBase, _DEPLOYMENT_BASE_REQUIRED, 384001),
        (DeploymentUpdate, {}, -1),
        (DeploymentUpdate, {}, 384001),
        (AudioBase, _AUDIO_BASE_REQUIRED, -1),
        (AudioBase, _AUDIO_BASE_REQUIRED, 384001),
        (AudioUpdate, {}, -1),
        (AudioUpdate, {}, 384001),
        (AudioBatchItem, _AUDIO_BATCH_REQUIRED, -1),
        (AudioBatchItem, _AUDIO_BATCH_REQUIRED, 384001),
    ],
)
def test_fs_invalid_values(schema_cls, required_fields, fs_value):
    """fs 非法值（負數、超出上限）應拋出 ValidationError。"""
    with pytest.raises(ValidationError):
        schema_cls(**required_fields, fs=fs_value)
