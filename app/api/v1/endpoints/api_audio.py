from typing import List, Optional
from fastapi import APIRouter, Depends
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.core.minio import get_s3_client
from app.utils.path_utils import parse_filename_and_generate_key
from app.schemas.audio import (
    AudioCreate,
    AudioResponse,
    AudioUpdate,
    AudioWithDetailsResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    PresignedUrlBatchRequest,
    PresignedUrlBatchResponse,
)
from app.services.audio_service import AudioService
from app.services.project_service import ProjectService
from app.services.point_service import PointService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/", response_model=List[AudioResponse])
def get_audios(
    deployment_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).get_audios(
        deployment_id=deployment_id, skip=skip, limit=limit
    )


@router.get("/{audio_id}", response_model=AudioResponse)
def get_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).get_audio(audio_id)


@router.get("/{audio_id}/details", response_model=AudioWithDetailsResponse)
def get_audio_details(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).get_audio_details(audio_id)


@router.post("/", response_model=AudioResponse)
def create_audio(
    audio: AudioCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).create_audio(audio)


@router.put("/{audio_id}", response_model=AudioResponse)
def update_audio(
    audio_id: int,
    audio: AudioUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AudioService(db).update_audio(audio_id, audio)


@router.post("/upload/presigned-url", response_model=PresignedUrlResponse)
def generate_presigned_url(
    request: PresignedUrlRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate a presigned URL for uploading audio files to MinIO.
    """
    s3_client = get_s3_client()
    bucket_name = request.project_name
    object_name = parse_filename_and_generate_key(request.point_name, request.filename)

    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=3600,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate presigned URL: {str(e)}"
        )

    return PresignedUrlResponse(presigned_url=url, bucket=bucket_name, key=object_name)


@router.post("/upload/presigned-urls", response_model=List[PresignedUrlBatchResponse])
def generate_presigned_urls(
    request: PresignedUrlBatchRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate multiple presigned URLs for uploading audio files to MinIO.
    """
    s3_client = get_s3_client()
    bucket_name = request.project_name
    responses = []

    for filename in request.filenames:
        object_name = parse_filename_and_generate_key(request.point_name, filename)
        try:
            url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=3600,
            )
            responses.append(
                PresignedUrlBatchResponse(
                    filename=filename,
                    presigned_url=url,
                    bucket=bucket_name,
                    key=object_name,
                )
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate presigned URL for {filename}: {str(e)}",
            )

    return responses
