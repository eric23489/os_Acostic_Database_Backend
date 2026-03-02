from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.minio import get_s3_client
from app.db.session import get_db
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check(
    response: Response,
    db: Session = Depends(get_db),
) -> HealthResponse:
    """Check PostgreSQL and MinIO connectivity."""
    db_status = _check_db(db)
    minio_status = _check_minio()
    overall: Literal["ok", "degraded"] = (
        "ok" if db_status == "ok" and minio_status == "ok" else "degraded"
    )
    if overall == "degraded":
        response.status_code = 503
    return HealthResponse(status=overall, db=db_status, minio=minio_status)


def _check_db(db: Session) -> Literal["ok", "error"]:
    """Execute a trivial query to verify database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


def _check_minio() -> Literal["ok", "error"]:
    """Call list_buckets to verify MinIO connectivity."""
    try:
        get_s3_client().list_buckets()
        return "ok"
    except Exception:
        return "error"
