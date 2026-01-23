from datetime import datetime, timezone, timedelta
from app.schemas.project import ProjectCreate, ProjectResponse


def test_datetime_timezone_validator():
    """
    Test that a naive datetime input (no timezone) is automatically
    converted to UTC+8 (Taiwan time).
    """
    # Input naive datetime: 2024-01-01 12:00:00
    naive_dt = datetime(2024, 1, 1, 12, 0, 0)
    project = ProjectCreate(name="Test Project", start_time=naive_dt)

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
    project = ProjectResponse(id=1, name="Test Project", start_time=utc_dt)

    # Dump model to JSON-compatible dict
    data = project.model_dump(mode="json")

    # Check string format
    assert data["start_time"] == "2024-01-01T12:00:00+08:00"
