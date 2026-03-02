"""
Enum 輸入驗證 API 測試 - P1 (重要)

測試 API 層的 Enum 驗證行為:
1. 無效 Enum 值回傳 422 錯誤
2. 422 錯誤包含詳細驗證訊息
3. 部分更新時 status 省略行為
4. Response JSON 包含字串值
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.core.config import settings

# =============================================================================
# Deployment API Enum 驗證測試
# =============================================================================


class TestDeploymentApiEnumValidation:
    """測試 Deployment API 的 Enum 驗證。"""

    def test_create_deployment_invalid_status_returns_422(self, client):
        """POST 無效 status 回傳 422。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid-status",
            },
        )
        assert response.status_code == 422

    def test_create_deployment_422_contains_status_error(self, client):
        """422 錯誤包含 status 欄位的驗證訊息。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "wrong-value",
            },
        )
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        # 確認錯誤指向 status 欄位
        status_errors = [e for e in error_detail if "status" in e.get("field", "")]
        assert len(status_errors) > 0
        # 確認錯誤訊息包含允許值
        assert "Input should be" in status_errors[0]["message"]

    def test_create_deployment_422_lists_valid_options(self, client):
        """422 錯誤訊息列出所有允許值。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        error_msg = str(response.json()["detail"])
        # 確認列出有效選項
        assert "un-deployed" in error_msg
        assert "under-monitoring" in error_msg
        assert "success" in error_msg

    def test_update_deployment_invalid_status_returns_422(self, client):
        """PUT 無效 status 回傳 422。"""
        response = client.put(
            f"{settings.api_prefix}/deployments/1",
            json={"status": "not-a-valid-status"},
        )
        assert response.status_code == 422

    def test_update_deployment_valid_status_accepted(self, client):
        """PUT 有效 status 被接受。"""
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_deployment = MagicMock()
            mock_deployment.id = 1
            mock_deployment.point_id = 1
            mock_deployment.recorder_id = 1
            mock_deployment.phase = 1
            mock_deployment.start_time = None
            mock_deployment.end_time = None
            mock_deployment.deploy_time = None
            mock_deployment.return_time = None
            mock_deployment.gps_lat_exe = None
            mock_deployment.gps_lon_exe = None
            mock_deployment.depth_exe = None
            mock_deployment.fs = None
            mock_deployment.sensitivity = None
            mock_deployment.gain = None
            mock_deployment.status = "success"
            mock_deployment.description = None
            mock_deployment.deploy_personnel = None
            mock_deployment.retrieve_personnel = None
            mock_deployment.created_at = datetime.now(UTC)
            mock_deployment.updated_at = datetime.now(UTC)
            mock_service.update_deployment.return_value = mock_deployment

            response = client.put(
                f"{settings.api_prefix}/deployments/1",
                json={"status": "success"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "success"

    def test_update_deployment_omit_status_allowed(self, client):
        """PUT 省略 status 不會觸發驗證錯誤。"""
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_deployment = MagicMock()
            mock_deployment.id = 1
            mock_deployment.point_id = 1
            mock_deployment.recorder_id = 1
            mock_deployment.phase = 1
            mock_deployment.start_time = None
            mock_deployment.end_time = None
            mock_deployment.deploy_time = None
            mock_deployment.return_time = None
            mock_deployment.gps_lat_exe = None
            mock_deployment.gps_lon_exe = None
            mock_deployment.depth_exe = None
            mock_deployment.fs = None
            mock_deployment.sensitivity = None
            mock_deployment.gain = None
            mock_deployment.status = "un-deployed"
            mock_deployment.description = "Updated description"
            mock_deployment.deploy_personnel = None
            mock_deployment.retrieve_personnel = None
            mock_deployment.created_at = datetime.now(UTC)
            mock_deployment.updated_at = datetime.now(UTC)
            mock_service.update_deployment.return_value = mock_deployment

            response = client.put(
                f"{settings.api_prefix}/deployments/1",
                json={"description": "Updated description"},
            )
            assert response.status_code == 200

    def test_get_deployment_response_contains_string_status(self, client):
        """GET 回應包含字串格式的 status。"""
        with patch(
            "app.api.v1.endpoints.api_deployments.DeploymentService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_deployment = MagicMock()
            mock_deployment.id = 1
            mock_deployment.point_id = 1
            mock_deployment.recorder_id = 1
            mock_deployment.phase = 1
            mock_deployment.start_time = None
            mock_deployment.end_time = None
            mock_deployment.deploy_time = None
            mock_deployment.return_time = None
            mock_deployment.gps_lat_exe = None
            mock_deployment.gps_lon_exe = None
            mock_deployment.depth_exe = None
            mock_deployment.fs = None
            mock_deployment.sensitivity = None
            mock_deployment.gain = None
            mock_deployment.status = "under-monitoring"
            mock_deployment.description = None
            mock_deployment.deploy_personnel = None
            mock_deployment.retrieve_personnel = None
            mock_deployment.created_at = datetime.now(UTC)
            mock_deployment.updated_at = datetime.now(UTC)
            mock_service.get_deployment.return_value = mock_deployment

            response = client.get(f"{settings.api_prefix}/deployments/1")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "under-monitoring"
            assert isinstance(data["status"], str)


# =============================================================================
# Recorder API Enum 驗證測試
# =============================================================================


class TestRecorderApiEnumValidation:
    """測試 Recorder API 的 Enum 驗證。"""

    def test_create_recorder_invalid_status_returns_422(self, client):
        """POST 無效 status 回傳 422。"""
        response = client.post(
            f"{settings.api_prefix}/recorders/",
            json={
                "brand": "Test",
                "model": "Model",
                "sn": "SN123",
                "sensitivity": -160.0,
                "status": "invalid-status",
            },
        )
        assert response.status_code == 422

    def test_create_recorder_422_contains_status_error(self, client):
        """422 錯誤包含 status 欄位的驗證訊息。"""
        response = client.post(
            f"{settings.api_prefix}/recorders/",
            json={
                "brand": "Test",
                "model": "Model",
                "sn": "SN123",
                "sensitivity": -160.0,
                "status": "wrong-value",
            },
        )
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        status_errors = [e for e in error_detail if "status" in e.get("field", "")]
        assert len(status_errors) > 0

    def test_create_recorder_422_lists_valid_options(self, client):
        """422 錯誤訊息列出所有允許值。"""
        response = client.post(
            f"{settings.api_prefix}/recorders/",
            json={
                "brand": "Test",
                "model": "Model",
                "sn": "SN123",
                "sensitivity": -160.0,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        error_msg = str(response.json()["detail"])
        assert "in-service" in error_msg
        assert "out-of-service" in error_msg

    def test_update_recorder_invalid_status_returns_422(self, client):
        """PUT 無效 status 回傳 422。"""
        response = client.put(
            f"{settings.api_prefix}/recorders/1",
            json={"status": "not-valid"},
        )
        assert response.status_code == 422

    def test_update_recorder_valid_status_accepted(self, client):
        """PUT 有效 status 被接受。"""
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_recorder = MagicMock()
            mock_recorder.id = 1
            mock_recorder.brand = "Test"
            mock_recorder.model = "Model"
            mock_recorder.sn = "SN123"
            mock_recorder.sensitivity = -160.0
            mock_recorder.high_gain = None
            mock_recorder.low_gain = None
            mock_recorder.status = "under-repair"
            mock_recorder.owner = "Ocean Sound"
            mock_recorder.recorder_channels = 1
            mock_recorder.description = None
            mock_recorder.created_at = datetime.now(UTC)
            mock_recorder.updated_at = datetime.now(UTC)
            mock_service.update_recorder.return_value = mock_recorder

            response = client.put(
                f"{settings.api_prefix}/recorders/1",
                json={"status": "under-repair"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "under-repair"

    def test_get_recorder_response_contains_string_status(self, client):
        """GET 回應包含字串格式的 status。"""
        with patch(
            "app.api.v1.endpoints.api_recorders.RecorderService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_recorder = MagicMock()
            mock_recorder.id = 1
            mock_recorder.brand = "Test"
            mock_recorder.model = "Model"
            mock_recorder.sn = "SN123"
            mock_recorder.sensitivity = -160.0
            mock_recorder.high_gain = None
            mock_recorder.low_gain = None
            mock_recorder.status = "checked-out"
            mock_recorder.owner = "Ocean Sound"
            mock_recorder.recorder_channels = 1
            mock_recorder.description = None
            mock_recorder.created_at = datetime.now(UTC)
            mock_recorder.updated_at = datetime.now(UTC)
            mock_service.get_recorder.return_value = mock_recorder

            response = client.get(f"{settings.api_prefix}/recorders/1")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "checked-out"
            assert isinstance(data["status"], str)


# =============================================================================
# User API Enum 驗證測試
# =============================================================================


class TestUserApiEnumValidation:
    """測試 User API 的 Enum 驗證。"""

    def test_create_user_invalid_role_returns_422(self, client):
        """POST 無效 role 回傳 422。"""
        response = client.post(
            f"{settings.api_prefix}/users/",
            json={
                "email": "test@example.com",
                "password": "password123",
                "role": "superadmin",
            },
        )
        assert response.status_code == 422

    def test_create_user_422_contains_role_error(self, client):
        """422 錯誤包含 role 欄位的驗證訊息。"""
        response = client.post(
            f"{settings.api_prefix}/users/",
            json={
                "email": "test@example.com",
                "password": "password123",
                "role": "invalid-role",
            },
        )
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        role_errors = [e for e in error_detail if "role" in e.get("field", "")]
        assert len(role_errors) > 0

    def test_create_user_422_lists_valid_options(self, client):
        """422 錯誤訊息列出所有允許值。"""
        response = client.post(
            f"{settings.api_prefix}/users/",
            json={
                "email": "test@example.com",
                "password": "password123",
                "role": "invalid",
            },
        )
        assert response.status_code == 422
        error_msg = str(response.json()["detail"])
        assert "admin" in error_msg
        assert "user" in error_msg
        assert "guest" in error_msg

    def test_create_user_valid_roles_accepted(self, client):
        """POST 所有有效 role 被接受。"""
        for role in ["admin", "user", "guest"]:
            with patch(
                "app.api.v1.endpoints.api_users.UserService"
            ) as mock_service_class:
                mock_service = mock_service_class.return_value
                mock_user = MagicMock()
                mock_user.id = 1
                mock_user.email = f"{role}@example.com"
                mock_user.full_name = None
                mock_user.role = role
                mock_user.is_active = True
                mock_user.is_verified = False
                mock_user.last_login_at = None
                mock_user.created_at = datetime.now(UTC)
                mock_user.updated_at = datetime.now(UTC)
                mock_user.oauth_provider = None
                mock_user.password_hash = "hashed"
                mock_service.create_user.return_value = mock_user

                response = client.post(
                    f"{settings.api_prefix}/users/",
                    json={
                        "email": f"{role}@example.com",
                        "password": "password123",
                        "role": role,
                    },
                )
                assert response.status_code == 200, f"Failed for role: {role}"


# =============================================================================
# 422 錯誤結構測試
# =============================================================================


class TestEnumValidation422Structure:
    """測試 422 錯誤回應結構（統一格式）。"""

    def test_422_response_has_error_code(self, client):
        """422 錯誤包含 error_code 欄位，值為 VALIDATION_ERROR。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"

    def test_422_detail_is_list(self, client):
        """422 detail 是錯誤列表。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert isinstance(body["detail"], list)

    def test_422_error_item_has_required_fields(self, client):
        """422 錯誤項目包含必要欄位 (field, message)。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        error_item = response.json()["detail"][0]
        assert "field" in error_item
        assert "message" in error_item

    def test_422_error_message_contains_valid_options(self, client):
        """422 錯誤訊息包含允許值提示。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        error_item = response.json()["detail"][0]
        assert "Input should be" in error_item["message"]

    def test_422_field_contains_field_path(self, client):
        """422 field 包含欄位路徑。"""
        response = client.post(
            f"{settings.api_prefix}/deployments/",
            json={
                "point_id": 1,
                "recorder_id": 1,
                "status": "invalid",
            },
        )
        assert response.status_code == 422
        error_item = response.json()["detail"][0]
        assert "status" in error_item["field"]


# =============================================================================
# Project API Enum 驗證測試
# =============================================================================


class TestProjectApiEnumValidation:
    """測試 Project API 的 ProjectType Enum 驗證。"""

    def test_create_project_invalid_project_type_returns_422(self, client):
        """POST 無效 project_type 回傳 422。"""
        response = client.post(
            f"{settings.api_prefix}/projects/",
            json={
                "name": "test-project",
                "project_type": "invalid-type",
            },
        )
        assert response.status_code == 422

    def test_create_project_422_contains_project_type_error(self, client):
        """422 錯誤包含 project_type 欄位的驗證訊息。"""
        response = client.post(
            f"{settings.api_prefix}/projects/",
            json={
                "name": "test-project",
                "project_type": "wrong-value",
            },
        )
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        project_type_errors = [
            e for e in error_detail if "project_type" in e.get("field", "")
        ]
        assert len(project_type_errors) > 0

    def test_create_project_422_lists_valid_options(self, client):
        """422 錯誤訊息列出所有允許值。"""
        response = client.post(
            f"{settings.api_prefix}/projects/",
            json={
                "name": "test-project",
                "project_type": "invalid",
            },
        )
        assert response.status_code == 422
        error_msg = str(response.json()["detail"])
        assert "wind-farm" in error_msg

    def test_create_project_valid_project_type_accepted(self, client):
        """POST 有效 project_type 被接受。"""
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"
            mock_project.name_zh = None
            mock_project.area = None
            mock_project.description = None
            mock_project.start_time = None
            mock_project.end_time = None
            mock_project.is_finished = False
            mock_project.owner = None
            mock_project.contractor = None
            mock_project.contact_name = None
            mock_project.contact_phone = None
            mock_project.contact_email = None
            mock_project.project_type = "wind-farm"
            mock_project.created_at = datetime.now(UTC)
            mock_project.updated_at = datetime.now(UTC)
            mock_service.create_project.return_value = mock_project

            response = client.post(
                f"{settings.api_prefix}/projects/",
                json={
                    "name": "test-project",
                    "project_type": "wind-farm",
                },
            )
            assert response.status_code == 200
            assert response.json()["project_type"] == "wind-farm"

    def test_create_project_null_project_type_accepted(self, client):
        """POST project_type 為 null 被接受。"""
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"
            mock_project.name_zh = None
            mock_project.area = None
            mock_project.description = None
            mock_project.start_time = None
            mock_project.end_time = None
            mock_project.is_finished = False
            mock_project.owner = None
            mock_project.contractor = None
            mock_project.contact_name = None
            mock_project.contact_phone = None
            mock_project.contact_email = None
            mock_project.project_type = None
            mock_project.created_at = datetime.now(UTC)
            mock_project.updated_at = datetime.now(UTC)
            mock_service.create_project.return_value = mock_project

            response = client.post(
                f"{settings.api_prefix}/projects/",
                json={"name": "test-project"},
            )
            assert response.status_code == 200
            assert response.json()["project_type"] is None

    def test_update_project_invalid_project_type_returns_422(self, client):
        """PUT 無效 project_type 回傳 422。"""
        response = client.put(
            f"{settings.api_prefix}/projects/1",
            json={"project_type": "not-valid"},
        )
        assert response.status_code == 422

    def test_get_project_response_contains_string_project_type(self, client):
        """GET 回應包含字串格式的 project_type。"""
        with patch(
            "app.api.v1.endpoints.api_projects.ProjectService"
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_project = MagicMock()
            mock_project.id = 1
            mock_project.name = "test-project"
            mock_project.name_zh = None
            mock_project.area = None
            mock_project.description = None
            mock_project.start_time = None
            mock_project.end_time = None
            mock_project.is_finished = False
            mock_project.owner = None
            mock_project.contractor = None
            mock_project.contact_name = None
            mock_project.contact_phone = None
            mock_project.contact_email = None
            mock_project.project_type = "wind-farm"
            mock_project.created_at = datetime.now(UTC)
            mock_project.updated_at = datetime.now(UTC)
            mock_service.get_project.return_value = mock_project

            response = client.get(f"{settings.api_prefix}/projects/1")
            assert response.status_code == 200
            data = response.json()
            assert data["project_type"] == "wind-farm"
            assert isinstance(data["project_type"], str)
