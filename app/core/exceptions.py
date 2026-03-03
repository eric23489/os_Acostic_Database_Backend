from dataclasses import dataclass

from fastapi import status


@dataclass
class AppException(Exception):  # noqa: N818
    """應用程式自定義例外，包含機器可讀的 error_code。"""

    error_code: str
    message: str
    http_status: int

    def __post_init__(self) -> None:
        super().__init__(self.message)


# ── 認證與授權 ──────────────────────────────────────────
AUTH_TOKEN_INVALID = AppException(
    error_code="AUTH_TOKEN_INVALID",
    message="Could not validate credentials",
    http_status=status.HTTP_401_UNAUTHORIZED,
)
AUTH_USER_INACTIVE = AppException(
    error_code="AUTH_USER_INACTIVE",
    message="Inactive user",
    http_status=status.HTTP_400_BAD_REQUEST,
)
AUTH_INCORRECT_CREDENTIALS = AppException(
    error_code="AUTH_INCORRECT_CREDENTIALS",
    message="Incorrect email or password",
    http_status=status.HTTP_401_UNAUTHORIZED,
)
PERMISSION_DENIED = AppException(
    error_code="PERMISSION_DENIED",
    message="The user doesn't have enough privileges",
    http_status=status.HTTP_403_FORBIDDEN,
)
PERMISSION_ADMIN_REQUIRED = AppException(
    error_code="PERMISSION_ADMIN_REQUIRED",
    message="Admin permission required",
    http_status=status.HTTP_403_FORBIDDEN,
)
PERMISSION_RESTORE_DENIED = AppException(
    error_code="PERMISSION_RESTORE_DENIED",
    message="Only the deleter or admin can restore this resource",
    http_status=status.HTTP_403_FORBIDDEN,
)

# ── Project ─────────────────────────────────────────────
PROJECT_NOT_FOUND = AppException(
    error_code="PROJECT_NOT_FOUND",
    message="Project not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
PROJECT_NAME_DUPLICATE = AppException(
    error_code="PROJECT_NAME_DUPLICATE",
    message="Project with this name already exists",
    http_status=status.HTTP_400_BAD_REQUEST,
)
PROJECT_NAME_RESERVED = AppException(
    error_code="PROJECT_NAME_RESERVED",
    message="Name reserved by deleted project. Hard delete to release.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
PROJECT_NAME_COLLISION = AppException(
    error_code="PROJECT_NAME_COLLISION",
    message="Active project with this name already exists. Cannot restore.",
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── Point ────────────────────────────────────────────────
POINT_NOT_FOUND = AppException(
    error_code="POINT_NOT_FOUND",
    message="Point not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
POINT_NAME_DUPLICATE = AppException(
    error_code="POINT_NAME_DUPLICATE",
    message="Point name already exists in this project",
    http_status=status.HTTP_400_BAD_REQUEST,
)
POINT_NAME_RESERVED = AppException(
    error_code="POINT_NAME_RESERVED",
    message="Name reserved by deleted point. Hard delete to release.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
POINT_NAME_COLLISION = AppException(
    error_code="POINT_NAME_COLLISION",
    message="Active point with this name already exists in the project. Cannot restore.",  # noqa: E501
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── Deployment ───────────────────────────────────────────
DEPLOYMENT_NOT_FOUND = AppException(
    error_code="DEPLOYMENT_NOT_FOUND",
    message="Deployment not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
DEPLOYMENT_PHASE_COLLISION = AppException(
    error_code="DEPLOYMENT_PHASE_COLLISION",
    message="Active deployment with this phase already exists for the point. Cannot restore.",  # noqa: E501
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── Audio ────────────────────────────────────────────────
AUDIO_NOT_FOUND = AppException(
    error_code="AUDIO_NOT_FOUND",
    message="Audio not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
AUDIO_OBJECT_KEY_DUPLICATE = AppException(
    error_code="AUDIO_OBJECT_KEY_DUPLICATE",
    message="Audio with this object_key already exists",
    http_status=status.HTTP_400_BAD_REQUEST,
)
AUDIO_OBJECT_KEY_RESERVED = AppException(
    error_code="AUDIO_OBJECT_KEY_RESERVED",
    message="object_key reserved by deleted audio. Hard delete to release.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
AUDIO_OBJECT_KEY_COLLISION = AppException(
    error_code="AUDIO_OBJECT_KEY_COLLISION",
    message="Active audio with this object_key already exists. Cannot restore.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
AUDIO_UPLOAD_NOT_COMPLETED = AppException(
    error_code="AUDIO_UPLOAD_NOT_COMPLETED",
    message="Audio upload not completed",
    http_status=status.HTTP_400_BAD_REQUEST,
)
AUDIO_CONCURRENT_CONFLICT = AppException(
    error_code="AUDIO_CONCURRENT_CONFLICT",
    message="Concurrent write conflict on object_key. Please retry.",
    http_status=status.HTTP_409_CONFLICT,
)
AUDIO_DB_COMMIT_FAILED = AppException(
    error_code="AUDIO_DB_COMMIT_FAILED",
    message="Failed to save audio records. Please retry.",
    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
)

# ── Upload Job ───────────────────────────────────────────
UPLOAD_JOB_NOT_FOUND = AppException(
    error_code="UPLOAD_JOB_NOT_FOUND",
    message="Job not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
UPLOAD_TASK_NOT_FOUND = AppException(
    error_code="UPLOAD_TASK_NOT_FOUND",
    message="Task not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
UPLOAD_MULTIPART_NOT_INIT = AppException(
    error_code="UPLOAD_MULTIPART_NOT_INIT",
    message="Multipart upload not initialized",
    http_status=status.HTTP_400_BAD_REQUEST,
)
UPLOAD_ALL_FILES_SKIPPED = AppException(
    error_code="UPLOAD_ALL_FILES_SKIPPED",
    message="All files skipped: no valid files to upload",
    http_status=status.HTTP_400_BAD_REQUEST,
)
MINIO_DELETE_FAILED = AppException(
    error_code="MINIO_DELETE_FAILED",
    message="Failed to delete resource. Please try again or contact administrator.",
    http_status=status.HTTP_502_BAD_GATEWAY,
)
MINIO_UPLOAD_FAILED = AppException(
    error_code="MINIO_UPLOAD_FAILED",
    message="Failed to complete file upload",
    http_status=status.HTTP_502_BAD_GATEWAY,
)

# ── Recorder ─────────────────────────────────────────────
RECORDER_NOT_FOUND = AppException(
    error_code="RECORDER_NOT_FOUND",
    message="Recorder not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
RECORDER_IDENTIFIER_RESERVED = AppException(
    error_code="RECORDER_IDENTIFIER_RESERVED",
    message="Identifier reserved by deleted recorder. Hard delete to release.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
RECORDER_IDENTIFIER_COLLISION = AppException(
    error_code="RECORDER_IDENTIFIER_COLLISION",
    message="Active recorder with this brand/model/sn already exists. Cannot restore.",
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── User ─────────────────────────────────────────────────
USER_NOT_FOUND = AppException(
    error_code="USER_NOT_FOUND",
    message="User not found",
    http_status=status.HTTP_404_NOT_FOUND,
)
USER_EMAIL_DUPLICATE = AppException(
    error_code="USER_EMAIL_DUPLICATE",
    message="UserInfo with the same email already exists.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
USER_EMAIL_COLLISION = AppException(
    error_code="USER_EMAIL_COLLISION",
    message="Active user with this email already exists. Cannot restore.",
    http_status=status.HTTP_400_BAD_REQUEST,
)
USER_PASSWORD_TOO_SHORT = AppException(
    error_code="USER_PASSWORD_TOO_SHORT",
    message="Password does not meet the security requirements",
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── Password Reset ───────────────────────────────────────
PASSWORD_RESET_TOKEN_INVALID = AppException(
    error_code="PASSWORD_RESET_TOKEN_INVALID",
    message="Invalid or expired reset token",
    http_status=status.HTTP_400_BAD_REQUEST,
)
PASSWORD_RESET_TOKEN_EXPIRED = AppException(
    error_code="PASSWORD_RESET_TOKEN_EXPIRED",
    message="Reset token has expired. Please request a new one.",
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── 查詢 ─────────────────────────────────────────────────
QUERY_SORT_INVALID = AppException(
    error_code="QUERY_SORT_INVALID",
    message="Invalid sort field",
    http_status=status.HTTP_400_BAD_REQUEST,
)

# ── 系統 ─────────────────────────────────────────────────
INTERNAL_ERROR = AppException(
    error_code="INTERNAL_ERROR",
    message="An unexpected error occurred",
    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
)

# ── OAuth ────────────────────────────────────────────────
OAUTH_NOT_CONFIGURED = AppException(
    error_code="OAUTH_NOT_CONFIGURED",
    message="Google OAuth is not configured",
    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
)
OAUTH_CODE_EXCHANGE_FAILED = AppException(
    error_code="OAUTH_CODE_EXCHANGE_FAILED",
    message="Failed to exchange authorization code",
    http_status=status.HTTP_401_UNAUTHORIZED,
)
OAUTH_ALREADY_LINKED = AppException(
    error_code="OAUTH_ALREADY_LINKED",
    message="Account already linked to Google",
    http_status=status.HTTP_400_BAD_REQUEST,
)
OAUTH_ACCOUNT_IN_USE = AppException(
    error_code="OAUTH_ACCOUNT_IN_USE",
    message="This Google account is already linked to another user",
    http_status=status.HTTP_400_BAD_REQUEST,
)
OAUTH_NOT_LINKED = AppException(
    error_code="OAUTH_NOT_LINKED",
    message="Account is not linked to Google",
    http_status=status.HTTP_400_BAD_REQUEST,
)
