"""Audio Upload Jobs API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.minio import get_s3_client
from app.db.session import get_db
from app.schemas.audio import (
    PresignedUrlBatchRequest,
    PresignedUrlBatchResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.schemas.upload_job import (
    MultipartCompleteRequest,
    MultipartInitResponse,
    MultipartUrlsRequest,
    MultipartUrlsResponse,
    PartCompleteRequest,
    TaskCompleteRequest,
    TaskProgressResponse,
    UploadJobCreateRequest,
    UploadJobCreateResponse,
    UploadJobStatusResponse,
)
from app.services.upload_job_service import UploadJobService
from app.utils.path_utils import parse_filename_and_generate_key

router = APIRouter(prefix="/audio-upload-jobs", tags=["audio-upload-jobs"])


# =============================================================================
# Simple Presigned URL (Single File Upload)
# =============================================================================


@router.post("/presigned-url", response_model=PresignedUrlResponse)
def generate_presigned_url(
    request: PresignedUrlRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate a presigned URL for uploading a single audio file to MinIO.

    For batch uploads, use POST /audio-upload-jobs/ instead.
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


@router.post("/presigned-urls", response_model=list[PresignedUrlBatchResponse])
def generate_presigned_urls(
    request: PresignedUrlBatchRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate multiple presigned URLs for uploading audio files to MinIO.

    For large files (>100MB), use POST /audio-upload-jobs/ with multipart upload instead.
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


# =============================================================================
# Job Management
# =============================================================================


@router.post(
    "/",
    response_model=UploadJobCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_upload_job(
    request: UploadJobCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    建立上传任务。

    - 验证 deployment 存在
    - 批量建立 AudioInfo (upload_status = pending)
    - 回传任务 ID 和档案资讯
    """
    return UploadJobService(db).create_job(request, current_user.id)


@router.get("/{job_id}", response_model=UploadJobStatusResponse)
def get_upload_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查询上传任务进度。"""
    return UploadJobService(db).get_job_status(job_id)


@router.get("/", response_model=list[UploadJobStatusResponse])
def list_upload_jobs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """列出使用者的上传任务。"""
    return UploadJobService(db).list_jobs(current_user.id, skip, limit)


@router.post("/{job_id}/cancel")
def cancel_upload_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取消上传任务。"""
    UploadJobService(db).cancel_job(job_id)
    return {"status": "cancelled"}


# =============================================================================
# Task Completion (Simple Upload)
# =============================================================================


@router.post("/{job_id}/tasks/{task_id}/complete")
def complete_upload_task(
    job_id: str,
    task_id: str,
    request: TaskCompleteRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    通知单档上传完成 (简单上传模式)。

    注意：对于大档案，请使用 multipart upload API。
    """
    # For simple uploads, we need to implement this differently
    # This is a placeholder for now
    return {"status": "ok"}


# =============================================================================
# Multipart Upload API
# =============================================================================


@router.post(
    "/{job_id}/tasks/{task_id}/multipart/init",
    response_model=MultipartInitResponse,
)
def init_multipart_upload(
    job_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    初始化分段上传。

    - 计算总段数 (file_size / 100MB)
    - 向 MinIO 发起 create_multipart_upload
    - 回传 upload_id 和分段资讯
    """
    return UploadJobService(db).init_multipart(job_id, task_id)


@router.post(
    "/{job_id}/tasks/{task_id}/multipart/urls",
    response_model=MultipartUrlsResponse,
)
def get_multipart_urls(
    job_id: str,
    task_id: str,
    request: MultipartUrlsRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得指定 parts 的 presigned URLs。

    - 前端可分批请求 (例如一次 5 个)
    - 支援重试失败的 parts
    """
    return UploadJobService(db).get_multipart_urls(job_id, task_id, request.part_numbers)


@router.post("/{job_id}/tasks/{task_id}/multipart/part-complete")
def complete_part(
    job_id: str,
    task_id: str,
    request: PartCompleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    通知单一 part 上传完成。

    - 记录 etag
    - 更新进度 (completed_parts)
    """
    UploadJobService(db).mark_part_complete(
        job_id, task_id, request.part_number, request.etag
    )
    return {"status": "ok"}


@router.post("/{job_id}/tasks/{task_id}/multipart/complete")
def complete_multipart_upload(
    job_id: str,
    task_id: str,
    request: MultipartCompleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    完成分段上传。

    - 向 MinIO 发起 complete_multipart_upload
    - 更新 AudioInfo 状态为 completed
    """
    UploadJobService(db).complete_multipart(job_id, task_id, request.parts)
    return {"status": "ok"}


@router.post("/{job_id}/tasks/{task_id}/multipart/abort")
def abort_multipart_upload(
    job_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取消分段上传。

    - 向 MinIO 发起 abort_multipart_upload
    - 清理已上传的 parts
    """
    UploadJobService(db).abort_multipart(job_id, task_id)
    return {"status": "aborted"}


@router.get(
    "/{job_id}/tasks/{task_id}/progress",
    response_model=TaskProgressResponse,
)
def get_task_progress(
    job_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    取得单一档案的上传进度。

    - 用于断点续传：查询已完成的 parts
    """
    return UploadJobService(db).get_task_progress(job_id, task_id)
