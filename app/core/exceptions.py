# ruff: noqa: N801, N818
from dataclasses import FrozenInstanceError, dataclass

from fastapi import status

_EXCEPTION_INTERNAL_ATTRS = frozenset(
    {"__traceback__", "__cause__", "__context__", "__suppress_context__"}
)


@dataclass(frozen=True)
class AppException(Exception):
    """應用程式自定義例外，包含機器可讀的 error_code。"""

    error_code: str
    message: str
    http_status: int
    headers: dict | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)


def _app_exception_setattr(self: AppException, name: str, value: object) -> None:
    """允許 Python 例外機制設定 __traceback__ 等內部屬性，其餘欄位維持 frozen。"""
    if name in _EXCEPTION_INTERNAL_ATTRS:
        object.__setattr__(self, name, value)
        return
    raise FrozenInstanceError(f"cannot assign to field {name!r}")


def _app_exception_delattr(self: AppException, name: str) -> None:
    if name in _EXCEPTION_INTERNAL_ATTRS:
        object.__delattr__(self, name)
        return
    raise FrozenInstanceError(f"cannot delete field {name!r}")


AppException.__setattr__ = _app_exception_setattr  # type: ignore[method-assign]
AppException.__delattr__ = _app_exception_delattr  # type: ignore[method-assign]


# ── 認證與授權 ──────────────────────────────────────────
class AUTH_TOKEN_INVALID(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUTH_TOKEN_INVALID",
            message="Could not validate credentials",
            http_status=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AUTH_USER_INACTIVE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUTH_USER_INACTIVE",
            message="Inactive user",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class AUTH_INCORRECT_CREDENTIALS(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUTH_INCORRECT_CREDENTIALS",
            message="Incorrect email or password",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class PERMISSION_DENIED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PERMISSION_DENIED",
            message="The user doesn't have enough privileges",
            http_status=status.HTTP_403_FORBIDDEN,
        )


class PERMISSION_ADMIN_REQUIRED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PERMISSION_ADMIN_REQUIRED",
            message="Admin permission required",
            http_status=status.HTTP_403_FORBIDDEN,
        )


class PERMISSION_RESTORE_DENIED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PERMISSION_RESTORE_DENIED",
            message="Only the deleter or admin can restore this resource",
            http_status=status.HTTP_403_FORBIDDEN,
        )


# ── Project ─────────────────────────────────────────────
class PROJECT_NAME_REQUIRED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PROJECT_NAME_REQUIRED",
            message="Either 'name' or 'name_zh' must be provided.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class PROJECT_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PROJECT_NOT_FOUND",
            message="Project not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class PROJECT_NAME_DUPLICATE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PROJECT_NAME_DUPLICATE",
            message="Project with this name already exists",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class PROJECT_NAME_RESERVED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PROJECT_NAME_RESERVED",
            message="Name reserved by deleted project. Hard delete to release.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class PROJECT_NAME_COLLISION(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PROJECT_NAME_COLLISION",
            message="Active project with this name already exists. Cannot restore.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── Point ────────────────────────────────────────────────
class POINT_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="POINT_NOT_FOUND",
            message="Point not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class POINT_NAME_DUPLICATE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="POINT_NAME_DUPLICATE",
            message="Point name already exists in this project",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class POINT_NAME_RESERVED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="POINT_NAME_RESERVED",
            message="Name reserved by deleted point. Hard delete to release.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class POINT_NAME_COLLISION(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="POINT_NAME_COLLISION",
            message="Active point with this name already exists in the project. Cannot restore.",  # noqa: E501
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── Deployment ───────────────────────────────────────────
class DEPLOYMENT_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="DEPLOYMENT_NOT_FOUND",
            message="Deployment not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class DEPLOYMENT_PHASE_COLLISION(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="DEPLOYMENT_PHASE_COLLISION",
            message="Active deployment with this phase already exists for the point. Cannot restore.",  # noqa: E501
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── Audio ────────────────────────────────────────────────
class AUDIO_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_NOT_FOUND",
            message="Audio not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class AUDIO_OBJECT_KEY_DUPLICATE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_OBJECT_KEY_DUPLICATE",
            message="Audio with this object_key already exists",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class AUDIO_OBJECT_KEY_RESERVED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_OBJECT_KEY_RESERVED",
            message="object_key reserved by deleted audio. Hard delete to release.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class AUDIO_OBJECT_KEY_COLLISION(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_OBJECT_KEY_COLLISION",
            message="Active audio with this object_key already exists. Cannot restore.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class AUDIO_UPLOAD_NOT_COMPLETED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_UPLOAD_NOT_COMPLETED",
            message="Audio upload not completed",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class AUDIO_CONCURRENT_CONFLICT(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_CONCURRENT_CONFLICT",
            message="Concurrent write conflict on object_key. Please retry.",
            http_status=status.HTTP_409_CONFLICT,
        )


class AUDIO_DB_COMMIT_FAILED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="AUDIO_DB_COMMIT_FAILED",
            message="Failed to save audio records. Please retry.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ── Upload Job ───────────────────────────────────────────
class UPLOAD_JOB_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="UPLOAD_JOB_NOT_FOUND",
            message="Job not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class UPLOAD_TASK_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="UPLOAD_TASK_NOT_FOUND",
            message="Task not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class UPLOAD_MULTIPART_NOT_INIT(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="UPLOAD_MULTIPART_NOT_INIT",
            message="Multipart upload not initialized",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class UPLOAD_ALL_FILES_SKIPPED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="UPLOAD_ALL_FILES_SKIPPED",
            message="All files skipped: no valid files to upload",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class MINIO_DELETE_FAILED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="MINIO_DELETE_FAILED",
            message="Failed to delete resource. Please try again or contact administrator.",  # noqa: E501
            http_status=status.HTTP_502_BAD_GATEWAY,
        )


class MINIO_UPLOAD_FAILED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="MINIO_UPLOAD_FAILED",
            message="Failed to complete file upload",
            http_status=status.HTTP_502_BAD_GATEWAY,
        )


# ── Recorder ─────────────────────────────────────────────
class RECORDER_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="RECORDER_NOT_FOUND",
            message="Recorder not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class RECORDER_IDENTIFIER_RESERVED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="RECORDER_IDENTIFIER_RESERVED",
            message="Identifier reserved by deleted recorder. Hard delete to release.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class RECORDER_IDENTIFIER_DUPLICATE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="RECORDER_IDENTIFIER_DUPLICATE",
            message="Active recorder with this brand/model/sn already exists.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class RECORDER_HAS_DEPLOYMENTS(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="RECORDER_HAS_DEPLOYMENTS",
            message="Cannot delete recorder: deployments reference this recorder. Delete deployments first.",  # noqa: E501
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── User ─────────────────────────────────────────────────
class USER_NOT_FOUND(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="USER_NOT_FOUND",
            message="User not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )


class USER_EMAIL_DUPLICATE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="USER_EMAIL_DUPLICATE",
            message="UserInfo with the same email already exists.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class USER_EMAIL_COLLISION(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="USER_EMAIL_COLLISION",
            message="Active user with this email already exists. Cannot restore.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class USER_PASSWORD_TOO_SHORT(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="USER_PASSWORD_TOO_SHORT",
            message="Password must be at least 8 characters",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── Password Reset ───────────────────────────────────────
class PASSWORD_RESET_TOKEN_INVALID(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PASSWORD_RESET_TOKEN_INVALID",
            message="Invalid or expired reset token",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class PASSWORD_RESET_TOKEN_EXPIRED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="PASSWORD_RESET_TOKEN_EXPIRED",
            message="Reset token has expired. Please request a new one.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── 查詢 ─────────────────────────────────────────────────
class QUERY_SORT_INVALID(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="QUERY_SORT_INVALID",
            message="Invalid sort field",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


# ── 系統 ─────────────────────────────────────────────────
class INTERNAL_ERROR(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ── OAuth ────────────────────────────────────────────────
class OAUTH_NOT_CONFIGURED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_NOT_CONFIGURED",
            message="Google OAuth is not configured",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class OAUTH_CODE_EXCHANGE_FAILED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_CODE_EXCHANGE_FAILED",
            message="Failed to exchange authorization code",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )


class OAUTH_ALREADY_LINKED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_ALREADY_LINKED",
            message="Account already linked to Google",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class OAUTH_ACCOUNT_IN_USE(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_ACCOUNT_IN_USE",
            message="This Google account is already linked to another user",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class OAUTH_NOT_LINKED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_NOT_LINKED",
            message="Account is not linked to Google",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class OAUTH_PASSWORD_REQUIRED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_PASSWORD_REQUIRED",
            message="Please set a password before unlinking Google account",
            http_status=status.HTTP_400_BAD_REQUEST,
        )


class OAUTH_USERINFO_FETCH_FAILED(AppException):
    def __init__(self) -> None:
        super().__init__(
            error_code="OAUTH_USERINFO_FETCH_FAILED",
            message="Failed to fetch user info from Google.",
            http_status=status.HTTP_502_BAD_GATEWAY,
        )
