"""Tests for upload job schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.upload_job import (
    FileInfo,
    MultipartInitResponse,
    PartCompleteRequest,
    TaskProgressResponse,
    UploadJobCreateRequest,
    UploadJobProgress,
)


class TestFileInfoSchema:
    """Tests for FileInfo schema."""

    def test_valid_filename(self):
        """Test that valid filenames pass validation."""
        file_info = FileInfo(name="7505.240611130000.wav", size=1024)

        assert file_info.name == "7505.240611130000.wav"
        assert file_info.size == 1024

    def test_valid_filename_without_extension(self):
        """Test that valid filename without extension passes."""
        file_info = FileInfo(name="7505.240611130000")

        assert file_info.name == "7505.240611130000"

    def test_invalid_filename_raises_error(self):
        """Test that invalid filenames raise ValidationError."""
        with pytest.raises(ValidationError):
            FileInfo(name="invalid_file.wav")

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        file_info = FileInfo(name="7505.240611130000.wav")

        assert file_info.size is None
        assert file_info.checksum is None


class TestUploadJobCreateRequest:
    """Tests for UploadJobCreateRequest schema."""

    def test_valid_request(self):
        """Test a valid upload job create request."""
        request = UploadJobCreateRequest(
            deployment_id=1,
            files=[
                FileInfo(name="7505.240611130000.wav", size=1024),
                FileInfo(name="7505.240611130100.wav", size=1024),
            ],
        )

        assert request.deployment_id == 1
        assert len(request.files) == 2
        assert request.priority == 5  # default

    def test_custom_priority(self):
        """Test request with custom priority."""
        request = UploadJobCreateRequest(
            deployment_id=1,
            priority=0,
            files=[FileInfo(name="7505.240611130000.wav")],
        )

        assert request.priority == 0

    def test_empty_files_raises_error(self):
        """Test that empty files list raises ValidationError."""
        with pytest.raises(ValidationError):
            UploadJobCreateRequest(deployment_id=1, files=[])

    def test_too_many_files_raises_error(self):
        """Test that more than 1000 files raises ValidationError."""
        files = [
            FileInfo(name=f"7505.{240611130000 + i:012d}.wav") for i in range(1001)
        ]

        with pytest.raises(ValidationError):
            UploadJobCreateRequest(deployment_id=1, files=files)


class TestMultipartSchemas:
    """Tests for multipart upload schemas."""

    def test_multipart_init_response(self):
        """Test MultipartInitResponse schema."""
        response = MultipartInitResponse(
            upload_id="abc123",
            total_parts=13,
            part_size=104857600,
        )

        assert response.upload_id == "abc123"
        assert response.total_parts == 13
        assert response.part_size == 104857600

    def test_part_complete_request(self):
        """Test PartCompleteRequest schema."""
        request = PartCompleteRequest(
            part_number=1,
            etag="etag123",
        )

        assert request.part_number == 1
        assert request.etag == "etag123"


class TestTaskProgressResponse:
    """Tests for TaskProgressResponse schema."""

    def test_task_progress_response(self):
        """Test TaskProgressResponse schema."""
        response = TaskProgressResponse(
            task_id="task-123",
            file_name="7505.240611130000.wav",
            status="uploading",
            upload_id="upload-123",
            part_size=104857600,
            total_parts=13,
            completed_parts=[1, 2, 3, 4, 5],
            remaining_parts=[6, 7, 8, 9, 10, 11, 12, 13],
        )

        assert response.task_id == "task-123"
        assert len(response.completed_parts) == 5
        assert len(response.remaining_parts) == 8


class TestUploadJobProgress:
    """Tests for UploadJobProgress schema."""

    def test_upload_job_progress(self):
        """Test UploadJobProgress schema."""
        progress = UploadJobProgress(
            total=100,
            uploaded=50,
            completed=45,
            failed=2,
            percentage=45.0,
        )

        assert progress.total == 100
        assert progress.uploaded == 50
        assert progress.completed == 45
        assert progress.failed == 2
        assert progress.percentage == 45.0
