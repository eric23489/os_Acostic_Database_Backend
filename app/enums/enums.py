from enum import Enum, IntEnum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class DeploymentStatus(str, Enum):
    UNDEPLOYED = "un-deployed"
    MONITORING = "under-monitoring"
    SUCCESS = "success"
    WATER_INTRUSION = "water-intrusion"
    LOST = "lost"

class RecorderStatus(str, Enum):
    IN_SERVICE = "in-service"
    OUT_OF_SERVICE = "out-of-service"
    UNDER_REPAIR = "under-repair"
    UNDER_CALIBRATION = "under-calibration"
    BROKEN = "broken"
    RETIRED = "retired"
    LOST = "lost"
    CHECKED_OUT = "checked-out"

class DetectionMethod(str, Enum):
    MANUAL = "manually"
    NTU_PAM = "ntu-pam"
    MODEL = "model-detect"
    
class CetaceanCallType(IntEnum):
    UNKNOWN = 0   # 未知
    UPSWEEP = 1   # 上升型
    DOWNSWEEP = 2 # 下降型
    CONCAVE = 3   # U型
    CONVEX = 4    # 倒U型
    CONSTANT = 5  # 平穩型
    SINE = 6      # sin型
    CLICK = 7
    BURST = 8
    