from app.core.config import settings


def test_generate_presigned_url(client, mock_s3_client):
    """
    Test generating a single presigned URL.
    Mocks the S3 client to avoid actual network calls.
    """
    # Mock S3 client behavior
    mock_s3_client.generate_presigned_url.return_value = "http://minio/signed-url"

    payload = {
        "project_id": 1,
        "project_name": "ProjectA",
        "point_id": 1,
        "point_name": "PointA",
        "filename": "7505.240611130000.wav",
    }

    response = client.post(
        f"{settings.api_prefix}/audio/upload/presigned-url", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["presigned_url"] == "http://minio/signed-url"
    assert data["bucket"] == "ProjectA"
    # Verify path generation logic was applied
    assert data["key"] == "PointA/2024/06/Raw_Data/7505.240611130000.wav"


def test_generate_presigned_urls_batch(client, mock_s3_client):
    """
    Test generating multiple presigned URLs in a batch.
    """
    # Return different URLs for calls (though here we just return a static one for simplicity,
    # or we could use side_effect if we wanted distinct URLs)
    mock_s3_client.generate_presigned_url.return_value = "http://minio/signed-url"

    payload = {
        "project_id": 1,
        "project_name": "ProjectA",
        "point_id": 1,
        "point_name": "PointA",
        "filenames": ["file1.wav", "file2.wav"],
    }

    response = client.post(
        f"{settings.api_prefix}/audio/upload/presigned-urls", json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["filename"] == "file1.wav"
    assert data[1]["filename"] == "file2.wav"
    assert mock_s3_client.generate_presigned_url.call_count == 2
