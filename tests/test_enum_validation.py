"""
Enum 輸入驗證測試 - P0 (必須)

測試 Schema 層的 Enum 驗證行為:
1. 無效值觸發 ValidationError
2. 所有有效值通過驗證
3. Response 序列化為字串
"""

import pytest
from pydantic import ValidationError

from app.enums.enums import DeploymentStatus, ProjectType, RecorderStatus, UserRole
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
)
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.recorder import RecorderCreate, RecorderResponse, RecorderUpdate
from app.schemas.user import UserCreate, UserResponse, UserUpdate

# =============================================================================
# DeploymentStatus 驗證測試
# =============================================================================


class TestDeploymentStatusValidation:
    """測試 DeploymentStatus Enum 驗證。"""

    def test_deployment_status_all_valid_values(self):
        """驗證所有有效 DeploymentStatus 值都能通過。"""
        for status in DeploymentStatus:
            deployment = DeploymentCreate(
                point_id=1,
                recorder_id=1,
                status=status,
            )
            assert deployment.status == status

    def test_deployment_status_valid_string_values(self):
        """驗證有效字串值都能通過。"""
        valid_values = [
            "un-deployed",
            "under-monitoring",
            "success",
            "water-intrusion",
            "lost",
            "found",
        ]
        for value in valid_values:
            deployment = DeploymentCreate(
                point_id=1,
                recorder_id=1,
                status=value,
            )
            assert deployment.status.value == value

    def test_deployment_status_invalid_string(self):
        """無效字串觸發 ValidationError。"""
        with pytest.raises(ValidationError) as exc_info:
            DeploymentCreate(
                point_id=1,
                recorder_id=1,
                status="invalid-status",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("status",)
        assert "Input should be" in errors[0]["msg"]

    def test_deployment_status_invalid_similar_string(self):
        """類似但錯誤的字串觸發 ValidationError。"""
        invalid_values = [
            "undeployed",  # 缺少連字號
            "under_monitoring",  # 底線而非連字號
            "SUCCESS",  # 大寫
            "deployed",  # 不存在的值
        ]
        for value in invalid_values:
            with pytest.raises(ValidationError):
                DeploymentCreate(
                    point_id=1,
                    recorder_id=1,
                    status=value,
                )

    def test_deployment_status_default_value(self):
        """status 預設值為 UNDEPLOYED。"""
        deployment = DeploymentCreate(
            point_id=1,
            recorder_id=1,
        )
        assert deployment.status == DeploymentStatus.UNDEPLOYED

    def test_deployment_update_status_none_allowed(self):
        """DeploymentUpdate 允許 status 為 None。"""
        update = DeploymentUpdate(status=None)
        assert update.status is None

    def test_deployment_update_invalid_status(self):
        """DeploymentUpdate 無效 status 觸發 ValidationError。"""
        with pytest.raises(ValidationError):
            DeploymentUpdate(status="invalid")


# =============================================================================
# RecorderStatus 驗證測試
# =============================================================================


class TestRecorderStatusValidation:
    """測試 RecorderStatus Enum 驗證。"""

    def test_recorder_status_all_valid_values(self):
        """驗證所有有效 RecorderStatus 值都能通過。"""
        for status in RecorderStatus:
            recorder = RecorderCreate(
                brand="Test",
                model="Model",
                sn="SN123",
                sensitivity=-160.0,
                status=status,
            )
            assert recorder.status == status

    def test_recorder_status_valid_string_values(self):
        """驗證有效字串值都能通過。"""
        valid_values = [
            "in-service",
            "out-of-service",
            "under-repair",
            "under-calibration",
            "broken",
            "retired",
            "lost",
            "checked-out",
        ]
        for value in valid_values:
            recorder = RecorderCreate(
                brand="Test",
                model="Model",
                sn="SN123",
                sensitivity=-160.0,
                status=value,
            )
            assert recorder.status.value == value

    def test_recorder_status_invalid_string(self):
        """無效字串觸發 ValidationError。"""
        with pytest.raises(ValidationError) as exc_info:
            RecorderCreate(
                brand="Test",
                model="Model",
                sn="SN123",
                sensitivity=-160.0,
                status="invalid-status",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("status",)
        assert "Input should be" in errors[0]["msg"]

    def test_recorder_status_case_sensitive(self):
        """大小寫錯誤觸發 ValidationError。"""
        invalid_values = [
            "IN-SERVICE",
            "In-Service",
            "OUT-OF-SERVICE",
        ]
        for value in invalid_values:
            with pytest.raises(ValidationError):
                RecorderCreate(
                    brand="Test",
                    model="Model",
                    sn="SN123",
                    sensitivity=-160.0,
                    status=value,
                )

    def test_recorder_status_default_value(self):
        """status 預設值為 IN_SERVICE。"""
        recorder = RecorderCreate(
            brand="Test",
            model="Model",
            sn="SN123",
            sensitivity=-160.0,
        )
        assert recorder.status == RecorderStatus.IN_SERVICE

    def test_recorder_update_status_none_allowed(self):
        """RecorderUpdate 允許 status 為 None。"""
        update = RecorderUpdate(status=None)
        assert update.status is None

    def test_recorder_update_invalid_status(self):
        """RecorderUpdate 無效 status 觸發 ValidationError。"""
        with pytest.raises(ValidationError):
            RecorderUpdate(status="invalid")


# =============================================================================
# UserRole 驗證測試
# =============================================================================


class TestUserRoleValidation:
    """測試 UserRole Enum 驗證。"""

    def test_user_role_all_valid_values(self):
        """驗證所有有效 UserRole 值都能通過。"""
        for role in UserRole:
            user = UserCreate(
                email="test@example.com",
                password="password123",
                role=role,
            )
            assert user.role == role

    def test_user_role_valid_string_values(self):
        """驗證有效字串值都能通過。"""
        valid_values = ["admin", "user", "guest"]
        for value in valid_values:
            user = UserCreate(
                email="test@example.com",
                password="password123",
                role=value,
            )
            assert user.role.value == value

    def test_user_role_invalid_string(self):
        """無效字串觸發 ValidationError。"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="password123",
                role="superuser",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role",)
        assert "Input should be" in errors[0]["msg"]

    def test_user_role_case_sensitive(self):
        """大小寫錯誤觸發 ValidationError。"""
        invalid_values = ["ADMIN", "Admin", "USER", "User"]
        for value in invalid_values:
            with pytest.raises(ValidationError):
                UserCreate(
                    email="test@example.com",
                    password="password123",
                    role=value,
                )

    def test_user_role_default_value(self):
        """role 預設值為 USER。"""
        user = UserCreate(
            email="test@example.com",
            password="password123",
        )
        assert user.role == UserRole.USER

    def test_user_update_role_none_allowed(self):
        """UserUpdate 允許 role 為 None。"""
        update = UserUpdate(role=None)
        assert update.role is None

    def test_user_update_invalid_role(self):
        """UserUpdate 無效 role 觸發 ValidationError。"""
        with pytest.raises(ValidationError):
            UserUpdate(role="superadmin")


# =============================================================================
# Response 序列化測試
# =============================================================================


class TestEnumResponseSerialization:
    """測試 Response Schema 的 Enum 序列化行為。"""

    def test_deployment_response_serializes_enum_to_string(self):
        """DeploymentResponse 序列化 Enum 為字串。"""
        response = DeploymentResponse(
            id=1,
            point_id=1,
            recorder_id=1,
            phase=1,
            status=DeploymentStatus.SUCCESS,
        )
        data = response.model_dump(mode="json")
        assert data["status"] == "success"
        assert isinstance(data["status"], str)

    def test_deployment_response_all_status_values(self):
        """DeploymentResponse 所有 status 值都序列化為字串。"""
        for status in DeploymentStatus:
            response = DeploymentResponse(
                id=1,
                point_id=1,
                recorder_id=1,
                phase=1,
                status=status,
            )
            data = response.model_dump(mode="json")
            assert data["status"] == status.value
            assert isinstance(data["status"], str)

    def test_recorder_response_serializes_enum_to_string(self):
        """RecorderResponse 序列化 Enum 為字串。"""
        response = RecorderResponse(
            id=1,
            brand="Test",
            model="Model",
            sn="SN123",
            sensitivity=-160.0,
            status=RecorderStatus.IN_SERVICE,
        )
        data = response.model_dump(mode="json")
        assert data["status"] == "in-service"
        assert isinstance(data["status"], str)

    def test_recorder_response_all_status_values(self):
        """RecorderResponse 所有 status 值都序列化為字串。"""
        for status in RecorderStatus:
            response = RecorderResponse(
                id=1,
                brand="Test",
                model="Model",
                sn="SN123",
                sensitivity=-160.0,
                status=status,
            )
            data = response.model_dump(mode="json")
            assert data["status"] == status.value
            assert isinstance(data["status"], str)

    def test_user_response_serializes_enum_to_string(self):
        """UserResponse 序列化 Enum 為字串。"""
        response = UserResponse(
            id=1,
            email="test@example.com",
            role=UserRole.ADMIN,
        )
        data = response.model_dump(mode="json")
        assert data["role"] == "admin"
        assert isinstance(data["role"], str)

    def test_user_response_all_role_values(self):
        """UserResponse 所有 role 值都序列化為字串。"""
        for role in UserRole:
            response = UserResponse(
                id=1,
                email="test@example.com",
                role=role,
            )
            data = response.model_dump(mode="json")
            assert data["role"] == role.value
            assert isinstance(data["role"], str)


# =============================================================================
# ProjectType 驗證測試
# =============================================================================


class TestProjectTypeValidation:
    """測試 ProjectType Enum 驗證。"""

    def test_project_type_all_valid_values(self):
        """驗證所有有效 ProjectType 值都能通過。"""
        for project_type in ProjectType:
            project = ProjectCreate(name="test-project", project_type=project_type)
            assert project.project_type == project_type

    def test_project_type_invalid_string(self):
        """無效字串觸發 ValidationError。"""
        with pytest.raises(ValidationError):
            ProjectCreate(name="test-project", project_type="invalid-type")

    def test_project_type_none_allowed(self):
        """ProjectCreate 允許 project_type 為 None。"""
        project = ProjectCreate(name="test-project")
        assert project.project_type is None

    def test_project_response_serializes_enum_to_string(self):
        """ProjectResponse 序列化 Enum 為字串。"""
        response = ProjectResponse(
            id=1, name="test-project", project_type=ProjectType.WIND_FARM
        )
        data = response.model_dump(mode="json")
        assert data["project_type"] == "wind-farm"
