import logging
import time
import uuid
from typing import Callable

from fastapi import Request
from fastapi.responses import Response
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_user_identity(request: Request) -> str:
    """Best-effort 從 JWT 提取 user email，失敗時回傳 'anonymous'。"""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return "anonymous"
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload.get("sub") or "anonymous"
    except JWTError:
        return "anonymous"


def resolve_log_level(status_code: int) -> int:
    """根據 HTTP status code 決定 log level。"""
    if 500 <= status_code <= 599:
        return logging.ERROR
    if 400 <= status_code <= 499:
        return logging.WARNING
    return logging.INFO


async def log_requests(request: Request, call_next: Callable) -> Response:
    """記錄每個 API 請求，含 request_id、user identity、耗時與 log level 分級。"""
    request_id = str(uuid.uuid4())
    user_identity = extract_user_identity(request)

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    log_level = resolve_log_level(response.status_code)
    logger.log(
        log_level,
        "%s %s %s %.1fms req_id=%s user=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
        user_identity,
    )

    response.headers["X-Request-ID"] = request_id
    return response
