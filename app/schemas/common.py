from typing import Literal

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: list[dict] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "error"]
    minio: Literal["ok", "error"]


class MessageResponse(BaseModel):
    message: str
