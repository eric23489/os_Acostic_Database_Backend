"""
Enum 資料一致性測試 - P2 (建議)

測試 Enum 定義與資料庫的一致性:
1. Schema 預設值與 Model 預設值一致
2. Enum 值長度不超過 DB 欄位限制
3. 所有 Enum 值都是有效的 DB 字串
"""

from app.enums.enums import DeploymentStatus, RecorderStatus, UserRole
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.schemas.recorder import RecorderCreate, RecorderResponse
from app.schemas.user import UserCreate, UserResponse

# =============================================================================
# Schema 與 Model 預設值一致性測試
# =============================================================================


class TestEnumDefaultValueConsistency:
    """測試 Schema 與 Enum 預設值一致性。"""

    def test_deployment_status_default_matches_enum(self):
        """DeploymentCreate 預設值為 DeploymentStatus.UNDEPLOYED。"""
        deployment = DeploymentCreate(point_id=1, recorder_id=1)
        assert deployment.status == DeploymentStatus.UNDEPLOYED
        assert deployment.status.value == "un-deployed"

    def test_recorder_status_default_matches_enum(self):
        """RecorderCreate 預設值為 RecorderStatus.IN_SERVICE。"""
        recorder = RecorderCreate(
            brand="Test",
            model="Model",
            sn="SN123",
            sensitivity=-160.0,
        )
        assert recorder.status == RecorderStatus.IN_SERVICE
        assert recorder.status.value == "in-service"

    def test_user_role_default_matches_enum(self):
        """UserCreate 預設值為 UserRole.USER。"""
        user = UserCreate(
            email="test@example.com",
            password="password123",
        )
        assert user.role == UserRole.USER
        assert user.role.value == "user"

    def test_deployment_status_enum_values_match_schema_options(self):
        """DeploymentStatus Enum 所有值都能被 Schema 接受。"""
        for status in DeploymentStatus:
            deployment = DeploymentCreate(
                point_id=1,
                recorder_id=1,
                status=status.value,  # 使用字串值
            )
            assert deployment.status == status

    def test_recorder_status_enum_values_match_schema_options(self):
        """RecorderStatus Enum 所有值都能被 Schema 接受。"""
        for status in RecorderStatus:
            recorder = RecorderCreate(
                brand="Test",
                model="Model",
                sn="SN123",
                sensitivity=-160.0,
                status=status.value,
            )
            assert recorder.status == status

    def test_user_role_enum_values_match_schema_options(self):
        """UserRole Enum 所有值都能被 Schema 接受。"""
        for role in UserRole:
            user = UserCreate(
                email="test@example.com",
                password="password123",
                role=role.value,
            )
            assert user.role == role


# =============================================================================
# DB 欄位長度限制測試
# =============================================================================


class TestEnumDbFieldLengthConstraints:
    """測試 Enum 值長度不超過 DB 欄位限制。"""

    def test_deployment_status_values_fit_db_column(self):
        """所有 DeploymentStatus 值都不超過 DB String(50) 限制。"""
        # DeploymentInfo.status 是 Column(String(50))
        max_length = 50
        for status in DeploymentStatus:
            assert len(status.value) <= max_length, (
                f"DeploymentStatus.{status.name} value '{status.value}' "
                f"exceeds {max_length} chars"
            )

    def test_recorder_status_values_fit_db_column(self):
        """所有 RecorderStatus 值都不超過 DB String(50) 限制。"""
        # RecorderInfo.status 是 Column(String(50))
        max_length = 50
        for status in RecorderStatus:
            assert len(status.value) <= max_length, (
                f"RecorderStatus.{status.name} value '{status.value}' "
                f"exceeds {max_length} chars"
            )

    def test_user_role_values_fit_db_column(self):
        """所有 UserRole 值都不超過 DB String(100) 限制。"""
        # User.role 是 Column(String(100))
        max_length = 100
        for role in UserRole:
            assert len(role.value) <= max_length, (
                f"UserRole.{role.name} value '{role.value}' "
                f"exceeds {max_length} chars"
            )

    def test_all_enum_values_are_non_empty(self):
        """所有 Enum 值都是非空字串。"""
        for status in DeploymentStatus:
            assert len(status.value) > 0
            assert status.value.strip() == status.value

        for status in RecorderStatus:
            assert len(status.value) > 0
            assert status.value.strip() == status.value

        for role in UserRole:
            assert len(role.value) > 0
            assert role.value.strip() == role.value


# =============================================================================
# Enum 值格式測試
# =============================================================================


class TestEnumValueFormat:
    """測試 Enum 值格式。"""

    def test_deployment_status_values_are_lowercase(self):
        """DeploymentStatus 值都是小寫。"""
        for status in DeploymentStatus:
            assert status.value == status.value.lower(), (
                f"DeploymentStatus.{status.name} value '{status.value}' "
                f"is not lowercase"
            )

    def test_recorder_status_values_are_lowercase(self):
        """RecorderStatus 值都是小寫。"""
        for status in RecorderStatus:
            assert status.value == status.value.lower(), (
                f"RecorderStatus.{status.name} value '{status.value}' "
                f"is not lowercase"
            )

    def test_user_role_values_are_lowercase(self):
        """UserRole 值都是小寫。"""
        for role in UserRole:
            assert role.value == role.value.lower(), (
                f"UserRole.{role.name} value '{role.value}' "
                f"is not lowercase"
            )

    def test_deployment_status_uses_hyphen_separator(self):
        """DeploymentStatus 多字值使用連字號分隔。"""
        multi_word_statuses = [
            DeploymentStatus.UNDEPLOYED,
            DeploymentStatus.MONITORING,
            DeploymentStatus.WATER_INTRUSION,
        ]
        for status in multi_word_statuses:
            # 確認不使用底線
            assert "_" not in status.value, (
                f"DeploymentStatus.{status.name} uses underscore"
            )

    def test_recorder_status_uses_hyphen_separator(self):
        """RecorderStatus 多字值使用連字號分隔。"""
        multi_word_statuses = [
            RecorderStatus.IN_SERVICE,
            RecorderStatus.OUT_OF_SERVICE,
            RecorderStatus.UNDER_REPAIR,
            RecorderStatus.UNDER_CALIBRATION,
            RecorderStatus.CHECKED_OUT,
        ]
        for status in multi_word_statuses:
            assert "_" not in status.value, (
                f"RecorderStatus.{status.name} uses underscore"
            )


# =============================================================================
# Enum 完整性測試
# =============================================================================


class TestEnumCompleteness:
    """測試 Enum 定義完整性。"""

    def test_deployment_status_has_expected_values(self):
        """DeploymentStatus 包含所有預期的狀態。"""
        expected_values = {
            "un-deployed",
            "under-monitoring",
            "success",
            "water-intrusion",
            "lost",
        }
        actual_values = {status.value for status in DeploymentStatus}
        assert actual_values == expected_values

    def test_recorder_status_has_expected_values(self):
        """RecorderStatus 包含所有預期的狀態。"""
        expected_values = {
            "in-service",
            "out-of-service",
            "under-repair",
            "under-calibration",
            "broken",
            "retired",
            "lost",
            "checked-out",
        }
        actual_values = {status.value for status in RecorderStatus}
        assert actual_values == expected_values

    def test_user_role_has_expected_values(self):
        """UserRole 包含所有預期的角色。"""
        expected_values = {"admin", "user", "guest"}
        actual_values = {role.value for role in UserRole}
        assert actual_values == expected_values

    def test_deployment_status_count(self):
        """DeploymentStatus 有 5 個狀態。"""
        assert len(DeploymentStatus) == 5

    def test_recorder_status_count(self):
        """RecorderStatus 有 8 個狀態。"""
        assert len(RecorderStatus) == 8

    def test_user_role_count(self):
        """UserRole 有 3 個角色。"""
        assert len(UserRole) == 3


# =============================================================================
# Response 序列化一致性測試
# =============================================================================


class TestEnumSerializationConsistency:
    """測試 Enum 序列化一致性。"""

    def test_deployment_response_serializes_all_statuses_consistently(self):
        """DeploymentResponse 對所有 status 值序列化一致。"""
        for status in DeploymentStatus:
            response = DeploymentResponse(
                id=1,
                point_id=1,
                recorder_id=1,
                phase=1,
                status=status,
            )
            # model_dump (Python dict)
            data_dict = response.model_dump()
            assert data_dict["status"] == status.value

            # model_dump with mode="json" (JSON serializable)
            data_json = response.model_dump(mode="json")
            assert data_json["status"] == status.value
            assert isinstance(data_json["status"], str)

    def test_recorder_response_serializes_all_statuses_consistently(self):
        """RecorderResponse 對所有 status 值序列化一致。"""
        for status in RecorderStatus:
            response = RecorderResponse(
                id=1,
                brand="Test",
                model="Model",
                sn="SN123",
                sensitivity=-160.0,
                status=status,
            )
            data_dict = response.model_dump()
            assert data_dict["status"] == status.value

            data_json = response.model_dump(mode="json")
            assert data_json["status"] == status.value
            assert isinstance(data_json["status"], str)

    def test_user_response_serializes_all_roles_consistently(self):
        """UserResponse 對所有 role 值序列化一致。"""
        for role in UserRole:
            response = UserResponse(
                id=1,
                email="test@example.com",
                role=role,
            )
            data_dict = response.model_dump()
            assert data_dict["role"] == role.value

            data_json = response.model_dump(mode="json")
            assert data_json["role"] == role.value
            assert isinstance(data_json["role"], str)

    def test_serialization_roundtrip_preserves_value(self):
        """序列化後反序列化保持值不變。"""
        original = DeploymentResponse(
            id=1,
            point_id=1,
            recorder_id=1,
            phase=1,
            status=DeploymentStatus.SUCCESS,
        )
        # Serialize to JSON dict
        json_data = original.model_dump(mode="json")

        # Deserialize back
        restored = DeploymentResponse.model_validate(json_data)

        assert restored.status == original.status
        assert restored.status == DeploymentStatus.SUCCESS.value
