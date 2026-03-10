from enum import IntEnum, StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class DeploymentStatus(StrEnum):
    UNDEPLOYED = "un-deployed"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    WATER_INTRUSION = "water-intrusion"
    LOST = "lost"
    FOUND = "found"


class RecorderStatus(StrEnum):
    AVAILABLE = "available"
    OUT_OF_SERVICE = "out-of-service"
    UNDER_REPAIR = "under-repair"
    UNDER_CALIBRATION = "under-calibration"
    BROKEN = "broken"
    RETIRED = "retired"
    LOST = "lost"
    CHECKED_OUT = "checked-out"
    DEPLOYING = "deploying"


class DetectionMethod(StrEnum):
    MANUAL = "manually"
    NTU_PAM = "ntu-pam"
    MODEL = "model-detect"


class CetaceanSpecies(IntEnum):
    UNKNOWN = 0  # 未知


class CetaceanCallType(IntEnum):
    UNKNOWN = 0  # 未知
    UPSWEEP = 1  # 上升型
    DOWNSWEEP = 2  # 下降型
    CONCAVE = 3  # U型
    CONVEX = 4  # 倒U型
    CONSTANT = 5  # 平穩型
    SINE = 6  # sin型
    CLICK = 7
    BURST = 8


class ProjectType(StrEnum):
    WIND_FARM = "wind-farm"


class UploadStatus(StrEnum):
    """AudioInfo 上传状态。"""

    PENDING = "pending"  # 已建立，等待上传
    UPLOADING = "uploading"  # 上传中 (有 parts 进度)
    COMPLETED = "completed"  # 上传完成
    FAILED = "failed"  # 上传失败


class JobStatus(StrEnum):
    """上传任务状态。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    """上传子任务状态。"""

    PENDING = "pending"  # 等待上传
    MULTIPART_INIT = "multipart-init"  # 已初始化分段上传
    UPLOADING = "uploading"  # 上传中 (有 parts 进度)
    UPLOADED = "uploaded"  # 已上传到 MinIO
    COMPLETED = "completed"  # 完成 (AudioInfo 已更新)
    FAILED = "failed"  # 失败
