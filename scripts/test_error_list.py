#!/usr/bin/env python3
"""
對運行中的 FastAPI 服務發出 HTTP 請求，驗證 error-list.md 的 error_code + http_status。

用法: python scripts/test_error_list.py
前提: docker-compose up -d 且 admin 帳號 aaa@example.com / aaa 存在
"""
import sys
import time

import httpx

API_BASE = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "aaa@example.com"
ADMIN_PASSWORD = "aaa"

SKIP_LIST = [
    ("POINT_NAME_RESERVED", "與 PROJECT_NAME_RESERVED 同模式，已由後者示範"),
    ("AUDIO_UPLOAD_NOT_COMPLETED", "需 upload job 流程，建立 UPLOADING 狀態的 AudioInfo"),
    ("AUDIO_CONCURRENT_CONFLICT", "Race condition，無法確定性觸發"),
    ("AUDIO_DB_COMMIT_FAILED", "需 DB IntegrityError 故障注入"),
    ("MINIO_DELETE_FAILED", "需 MinIO container 故障注入"),
    ("MINIO_UPLOAD_FAILED", "需 MinIO container 故障注入"),
    ("UPLOAD_TASK_NOT_FOUND", "需先建立有效 job（create_job 需 MinIO bucket）"),
    ("UPLOAD_MULTIPART_NOT_INIT", "需有效 job + task，未 init multipart"),
    ("PASSWORD_RESET_TOKEN_EXPIRED", "需等待 token 過期（時間相關）"),
    ("OAUTH_NOT_CONFIGURED", "需 Google OAuth env vars"),
    ("OAUTH_CODE_EXCHANGE_FAILED", "需 Google authorization code"),
    ("OAUTH_ALREADY_LINKED", "需已連結 Google 帳號的使用者"),
    ("OAUTH_ACCOUNT_IN_USE", "需 Google 帳號已被其他使用者連結"),
    ("OAUTH_PASSWORD_REQUIRED", "需 OAuth-only user（無密碼）"),
    ("OAUTH_USERINFO_FETCH_FAILED", "需 Google API 回傳失敗"),
]


class ErrorTestSuite:
    def __init__(self) -> None:
        self.client = httpx.Client(timeout=30)
        self.ts = int(time.time())
        self.results: list[tuple[str, bool, str]] = []

        self.project_id: int | None = None
        self.project_name: str = f"test-err-{self.ts}"
        self.point_id: int | None = None
        self.point_name: str = f"pt-err-{self.ts}"
        self.recorder_id: int | None = None
        self.deployment_id: int | None = None
        self.user_id: int | None = None
        self.user_email: str = f"testuser-{self.ts}@test.com"
        self.admin_user_id: int | None = None

        self.res_project_id: int | None = None
        self.res_recorder_id: int | None = None

        # Collision 測試資源（User / Project / Recorder）
        self.inactive_user_id: int | None = None
        self.coll_user_id1: int | None = None
        self.coll_user_id2: int | None = None
        self.coll_p1_id: int | None = None
        self.coll_p2_id: int | None = None
        self.coll_r1_id: int | None = None
        self.coll_r2_id: int | None = None

        # Collision 測試資源（Point / Deployment / Audio）
        self.coll_pt1_id: int | None = None
        self.coll_pt2_id: int | None = None
        self.coll_dep1_id: int | None = None
        self.coll_dep2_id: int | None = None
        self.audio_id_1: int | None = None
        self.audio_id_2: int | None = None

        # Permission 測試用隔離 project（避免 cascade soft-delete 污染主要資源）
        self.perm_proj_id: int | None = None

    def check(
        self,
        label: str,
        resp: httpx.Response,
        expected_code: str,
        expected_status: int,
    ) -> None:
        body = resp.json()
        ok = resp.status_code == expected_status and body.get("error_code") == expected_code
        self.results.append((label, ok, f"{resp.status_code} {body.get('error_code')}"))
        if ok:
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label}")
            print(f"         expected : {expected_status} {expected_code}")
            print(f"         actual   : {resp.status_code} {body.get('error_code')}")
            print(f"         body     : {body}")

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _login(self, email: str, password: str, label: str = "login") -> str:
        resp = self.client.post(
            f"{API_BASE}/users/login",
            data={"username": email, "password": password},
        )
        if not resp.is_success:
            print(f"[FATAL] {label} failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        print(f"[{label}] OK")
        return resp.json()["access_token"]

    def setup(self, admin_token: str) -> None:
        headers = self._headers(admin_token)

        # 1. recorder
        resp = self.client.post(
            f"{API_BASE}/recorders/",
            json={
                "brand": "TESTERR",
                "model": "TEST",
                "sn": f"err-{self.ts}",
                "sensitivity": -170.0,
            },
            headers=headers,
        )
        if not resp.is_success:
            print(f"[FATAL] setup recorder failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        self.recorder_id = resp.json()["id"]

        # 2. project
        resp = self.client.post(
            f"{API_BASE}/projects/",
            json={"name": self.project_name},
            headers=headers,
        )
        if not resp.is_success:
            print(f"[FATAL] setup project failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        self.project_id = resp.json()["id"]

        # 3. point
        resp = self.client.post(
            f"{API_BASE}/points/",
            json={"name": self.point_name, "project_id": self.project_id},
            headers=headers,
        )
        if not resp.is_success:
            print(f"[FATAL] setup point failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        self.point_id = resp.json()["id"]

        # 4. deployment
        resp = self.client.post(
            f"{API_BASE}/deployments/",
            json={"point_id": self.point_id, "recorder_id": self.recorder_id},
            headers=headers,
        )
        if not resp.is_success:
            print(f"[FATAL] setup deployment failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        self.deployment_id = resp.json()["id"]

        # 5. user
        resp = self.client.post(
            f"{API_BASE}/users/",
            json={"email": self.user_email, "password": "testpass123"},
            headers=headers,
        )
        if not resp.is_success:
            print(f"[FATAL] setup user failed: {resp.status_code} {resp.text}")
            sys.exit(1)
        self.user_id = resp.json()["id"]

        # 6. 取得 admin user ID
        resp = self.client.get(f"{API_BASE}/users/me", headers=headers)
        self.admin_user_id = resp.json()["id"]

        print(
            f"[setup] recorder={self.recorder_id} project={self.project_id}"
            f" point={self.point_id} deployment={self.deployment_id}"
            f" user={self.user_id} admin={self.admin_user_id}"
        )

    def teardown(self, admin_token: str) -> None:
        headers = self._headers(admin_token)
        print("\n[teardown] 清理資源...")

        # coll_dep2/dep1 必須在 recorder 之前清理（兩者都 reference self.recorder_id）
        if self.coll_dep2_id:
            self.client.delete(
                f"{API_BASE}/deployments/{self.coll_dep2_id}", headers=headers
            )
            self.client.delete(
                f"{API_BASE}/deployments/{self.coll_dep2_id}/permanent", headers=headers
            )

        if self.coll_dep1_id:
            self.client.delete(
                f"{API_BASE}/deployments/{self.coll_dep1_id}/permanent", headers=headers
            )

        if self.deployment_id:
            self.client.delete(f"{API_BASE}/deployments/{self.deployment_id}", headers=headers)
            self.client.delete(
                f"{API_BASE}/deployments/{self.deployment_id}/permanent", headers=headers
            )

        if self.recorder_id:
            self.client.delete(
                f"{API_BASE}/recorders/{self.recorder_id}/permanent", headers=headers
            )

        if self.point_id:
            self.client.delete(f"{API_BASE}/points/{self.point_id}/permanent", headers=headers)

        if self.project_id:
            self.client.delete(
                f"{API_BASE}/projects/{self.project_id}/permanent", headers=headers
            )

        if self.user_id:
            self.client.delete(f"{API_BASE}/users/{self.user_id}", headers=headers)

        if self.res_project_id:
            self.client.delete(
                f"{API_BASE}/projects/{self.res_project_id}/permanent", headers=headers
            )

        if self.res_recorder_id:
            self.client.delete(
                f"{API_BASE}/recorders/{self.res_recorder_id}/permanent", headers=headers
            )

        # Collision 測試資源清理（User / Project / Recorder）
        if self.inactive_user_id:
            self.client.delete(f"{API_BASE}/users/{self.inactive_user_id}", headers=headers)

        if self.coll_user_id2:
            self.client.delete(f"{API_BASE}/users/{self.coll_user_id2}", headers=headers)

        if self.coll_p2_id:
            self.client.delete(
                f"{API_BASE}/projects/{self.coll_p2_id}/permanent", headers=headers
            )

        if self.coll_p1_id:
            self.client.delete(
                f"{API_BASE}/projects/{self.coll_p1_id}/permanent", headers=headers
            )

        if self.coll_r2_id:
            self.client.delete(
                f"{API_BASE}/recorders/{self.coll_r2_id}/permanent", headers=headers
            )

        if self.coll_r1_id:
            self.client.delete(
                f"{API_BASE}/recorders/{self.coll_r1_id}/permanent", headers=headers
            )

        # Point collision 清理（coll_dep 已在上方處理）
        for pt_id in [self.coll_pt2_id, self.coll_pt1_id]:
            if pt_id:
                self.client.delete(f"{API_BASE}/points/{pt_id}/permanent", headers=headers)

        # Audio 清理
        for aid in [self.audio_id_1, self.audio_id_2]:
            if aid:
                self.client.delete(f"{API_BASE}/audio/{aid}/permanent", headers=headers)

        # Permission 測試用隔離 project（soft-deleted，需 permanent delete）
        if self.perm_proj_id:
            self.client.delete(
                f"{API_BASE}/projects/{self.perm_proj_id}/permanent", headers=headers
            )

        print("[teardown] 完成")

    # ── 群組 1：Auth ─────────────────────────────────────────────────────────

    def run_auth_group(self, admin_token: str) -> None:
        print("\n=== Auth ===")
        headers = self._headers(admin_token)

        resp = self.client.post(
            f"{API_BASE}/users/login",
            data={"username": "wrong@x.com", "password": "wrong"},
        )
        self.check("AUTH_INCORRECT_CREDENTIALS", resp, "AUTH_INCORRECT_CREDENTIALS", 401)

        resp = self.client.get(
            f"{API_BASE}/projects/",
            headers={"Authorization": "Bearer invalid_token_xxx"},
        )
        self.check("AUTH_TOKEN_INVALID", resp, "AUTH_TOKEN_INVALID", 401)

        # AUTH_USER_INACTIVE：建立使用者 → admin 停用 → 嘗試登入 → admin 恢復
        inactive_email = f"inactive-{self.ts}@test.com"
        resp = self.client.post(
            f"{API_BASE}/users/",
            json={"email": inactive_email, "password": "testpass123"},
            headers=headers,
        )
        if resp.is_success:
            self.inactive_user_id = resp.json()["id"]
            self.client.put(
                f"{API_BASE}/users/{self.inactive_user_id}",
                json={"is_active": False},
                headers=headers,
            )
            resp2 = self.client.post(
                f"{API_BASE}/users/login",
                data={"username": inactive_email, "password": "testpass123"},
            )
            self.check("AUTH_USER_INACTIVE", resp2, "AUTH_USER_INACTIVE", 400)
            self.client.put(
                f"{API_BASE}/users/{self.inactive_user_id}",
                json={"is_active": True},
                headers=headers,
            )
        else:
            print(f"  [SKIP] AUTH_USER_INACTIVE: create user failed: {resp.text}")

    # ── 群組 2：Not Found ────────────────────────────────────────────────────

    def run_not_found_group(self, admin_token: str) -> None:
        print("\n=== Not Found ===")
        headers = self._headers(admin_token)
        not_found_id = 999999

        cases = [
            ("PROJECT_NOT_FOUND", f"/projects/{not_found_id}"),
            ("POINT_NOT_FOUND", f"/points/{not_found_id}"),
            ("DEPLOYMENT_NOT_FOUND", f"/deployments/{not_found_id}"),
            ("AUDIO_NOT_FOUND", f"/audio/{not_found_id}"),
            ("RECORDER_NOT_FOUND", f"/recorders/{not_found_id}"),
            ("UPLOAD_JOB_NOT_FOUND", f"/audio-upload-jobs/{not_found_id}"),
            ("USER_NOT_FOUND", f"/users/{not_found_id}"),
        ]
        for label, path in cases:
            resp = self.client.get(f"{API_BASE}{path}", headers=headers)
            self.check(label, resp, label, 404)

    # ── 群組 3：Permission ───────────────────────────────────────────────────

    def run_permission_group(self, admin_token: str, user_token: str) -> None:
        print("\n=== Permission ===")
        admin_headers = self._headers(admin_token)
        user_headers = self._headers(user_token)

        resp = self.client.delete(
            f"{API_BASE}/projects/{self.project_id}/permanent",
            headers=user_headers,
        )
        self.check("PERMISSION_ADMIN_REQUIRED", resp, "PERMISSION_ADMIN_REQUIRED", 403)

        resp = self.client.put(
            f"{API_BASE}/users/{self.admin_user_id}",
            json={"full_name": "hacked"},
            headers=user_headers,
        )
        self.check("PERMISSION_DENIED", resp, "PERMISSION_DENIED", 403)

        # PERMISSION_RESTORE_DENIED：使用隔離 project 避免 cascade soft-delete 污染主要資源
        # admin 建立臨時 project → soft-delete → user 嘗試 restore → 期望 403
        # 不 restore，留在 soft-deleted，teardown 用 permanent delete 清理
        resp_p = self.client.post(
            f"{API_BASE}/projects/",
            json={"name": f"perm-{self.ts}"},
            headers=admin_headers,
        )
        if resp_p.is_success:
            self.perm_proj_id = resp_p.json()["id"]
            self.client.delete(
                f"{API_BASE}/projects/{self.perm_proj_id}", headers=admin_headers
            )
            resp = self.client.post(
                f"{API_BASE}/projects/{self.perm_proj_id}/restore",
                headers=user_headers,
            )
            self.check("PERMISSION_RESTORE_DENIED", resp, "PERMISSION_RESTORE_DENIED", 403)
        else:
            print(f"  [SKIP] PERMISSION_RESTORE_DENIED: create temp project failed: {resp_p.text}")

    # ── 群組 4：Validation ───────────────────────────────────────────────────

    def run_validation_group(self, admin_token: str) -> None:
        print("\n=== Validation ===")
        headers = self._headers(admin_token)

        resp = self.client.post(f"{API_BASE}/projects/", json={}, headers=headers)
        self.check("PROJECT_NAME_REQUIRED", resp, "PROJECT_NAME_REQUIRED", 400)

        resp = self.client.post(
            f"{API_BASE}/users/",
            json={"email": "x@x.com", "password": "ab"},
            headers=headers,
        )
        self.check("USER_PASSWORD_TOO_SHORT", resp, "USER_PASSWORD_TOO_SHORT", 400)

    # ── 群組 5：Duplicate ────────────────────────────────────────────────────

    def run_duplicate_group(self, admin_token: str) -> None:
        print("\n=== Duplicate ===")
        headers = self._headers(admin_token)

        resp = self.client.post(
            f"{API_BASE}/projects/",
            json={"name": self.project_name},
            headers=headers,
        )
        self.check("PROJECT_NAME_DUPLICATE", resp, "PROJECT_NAME_DUPLICATE", 400)

        resp = self.client.post(
            f"{API_BASE}/users/",
            json={"email": self.user_email, "password": "testpass123"},
            headers=headers,
        )
        self.check("USER_EMAIL_DUPLICATE", resp, "USER_EMAIL_DUPLICATE", 400)

        resp = self.client.post(
            f"{API_BASE}/points/",
            json={"name": self.point_name, "project_id": self.project_id},
            headers=headers,
        )
        self.check("POINT_NAME_DUPLICATE", resp, "POINT_NAME_DUPLICATE", 400)

    # ── 群組 6：Reserved ─────────────────────────────────────────────────────

    def run_reserved_group(self, admin_token: str) -> None:
        print("\n=== Reserved ===")
        headers = self._headers(admin_token)

        # PROJECT_NAME_RESERVED
        res_project_name = f"test-res-{self.ts}"
        resp = self.client.post(
            f"{API_BASE}/projects/",
            json={"name": res_project_name},
            headers=headers,
        )
        if resp.is_success:
            self.res_project_id = resp.json()["id"]
            self.client.delete(
                f"{API_BASE}/projects/{self.res_project_id}", headers=headers
            )
            resp2 = self.client.post(
                f"{API_BASE}/projects/",
                json={"name": res_project_name},
                headers=headers,
            )
            self.check("PROJECT_NAME_RESERVED", resp2, "PROJECT_NAME_RESERVED", 400)
        else:
            print(f"  [SKIP] PROJECT_NAME_RESERVED setup failed: {resp.status_code} {resp.text}")

        # RECORDER_IDENTIFIER_RESERVED
        res_sn = f"res-{self.ts}"
        resp = self.client.post(
            f"{API_BASE}/recorders/",
            json={"brand": "TESTERR", "model": "RES", "sn": res_sn, "sensitivity": -170.0},
            headers=headers,
        )
        if resp.is_success:
            self.res_recorder_id = resp.json()["id"]
            self.client.delete(
                f"{API_BASE}/recorders/{self.res_recorder_id}", headers=headers
            )
            resp2 = self.client.post(
                f"{API_BASE}/recorders/",
                json={"brand": "TESTERR", "model": "RES", "sn": res_sn, "sensitivity": -170.0},
                headers=headers,
            )
            self.check(
                "RECORDER_IDENTIFIER_RESERVED", resp2, "RECORDER_IDENTIFIER_RESERVED", 400
            )
        else:
            print(
                f"  [SKIP] RECORDER_IDENTIFIER_RESERVED setup failed:"
                f" {resp.status_code} {resp.text}"
            )

    # ── 群組 6b：Collision ───────────────────────────────────────────────────

    def run_collision_group(self, admin_token: str) -> None:
        print("\n=== Collision ===")
        headers = self._headers(admin_token)

        # USER_EMAIL_COLLISION：create_user 不檢查 RESERVED，可重建同 email
        coll_email = f"coll-u-{self.ts}@test.com"
        resp = self.client.post(
            f"{API_BASE}/users/",
            json={"email": coll_email, "password": "testpass123"},
            headers=headers,
        )
        if resp.is_success:
            self.coll_user_id1 = resp.json()["id"]
            self.client.delete(f"{API_BASE}/users/{self.coll_user_id1}", headers=headers)
            resp2 = self.client.post(
                f"{API_BASE}/users/",
                json={"email": coll_email, "password": "testpass123"},
                headers=headers,
            )
            if resp2.is_success:
                self.coll_user_id2 = resp2.json()["id"]
                resp3 = self.client.post(
                    f"{API_BASE}/users/{self.coll_user_id1}/restore",
                    headers=headers,
                )
                self.check("USER_EMAIL_COLLISION", resp3, "USER_EMAIL_COLLISION", 400)
            else:
                print(f"  [SKIP] USER_EMAIL_COLLISION: create U2 failed: {resp2.text}")
        else:
            print(f"  [SKIP] USER_EMAIL_COLLISION: create U1 failed: {resp.text}")

        # PROJECT_NAME_COLLISION：update 不檢查 RESERVED，改名後 restore 舊項
        coll_p1_name = f"coll-p1-{self.ts}"
        coll_p2_name = f"coll-p2-{self.ts}"
        resp = self.client.post(
            f"{API_BASE}/projects/", json={"name": coll_p1_name}, headers=headers
        )
        if resp.is_success:
            self.coll_p1_id = resp.json()["id"]
            resp2 = self.client.post(
                f"{API_BASE}/projects/", json={"name": coll_p2_name}, headers=headers
            )
            if resp2.is_success:
                self.coll_p2_id = resp2.json()["id"]
                self.client.delete(
                    f"{API_BASE}/projects/{self.coll_p2_id}", headers=headers
                )
                self.client.put(
                    f"{API_BASE}/projects/{self.coll_p1_id}",
                    json={"name": coll_p2_name},
                    headers=headers,
                )
                resp3 = self.client.post(
                    f"{API_BASE}/projects/{self.coll_p2_id}/restore",
                    headers=headers,
                )
                self.check("PROJECT_NAME_COLLISION", resp3, "PROJECT_NAME_COLLISION", 400)
            else:
                print(f"  [SKIP] PROJECT_NAME_COLLISION: create P2 failed: {resp2.text}")
        else:
            print(f"  [SKIP] PROJECT_NAME_COLLISION: create P1 failed: {resp.text}")

        # RECORDER_IDENTIFIER_COLLISION：update 不檢查 RESERVED，改 sn 後 restore 舊項
        coll_r1_sn = f"coll1-{self.ts}"
        coll_r2_sn = f"coll2-{self.ts}"
        resp = self.client.post(
            f"{API_BASE}/recorders/",
            json={"brand": "TESTERR", "model": "COLL", "sn": coll_r1_sn, "sensitivity": -170.0},
            headers=headers,
        )
        if resp.is_success:
            self.coll_r1_id = resp.json()["id"]
            resp2 = self.client.post(
                f"{API_BASE}/recorders/",
                json={
                    "brand": "TESTERR",
                    "model": "COLL",
                    "sn": coll_r2_sn,
                    "sensitivity": -170.0,
                },
                headers=headers,
            )
            if resp2.is_success:
                self.coll_r2_id = resp2.json()["id"]
                self.client.delete(
                    f"{API_BASE}/recorders/{self.coll_r2_id}", headers=headers
                )
                self.client.put(
                    f"{API_BASE}/recorders/{self.coll_r1_id}",
                    json={"sn": coll_r2_sn},
                    headers=headers,
                )
                resp3 = self.client.post(
                    f"{API_BASE}/recorders/{self.coll_r2_id}/restore",
                    headers=headers,
                )
                self.check(
                    "RECORDER_IDENTIFIER_COLLISION",
                    resp3,
                    "RECORDER_IDENTIFIER_COLLISION",
                    400,
                )
            else:
                print(
                    f"  [SKIP] RECORDER_IDENTIFIER_COLLISION: create R2 failed: {resp2.text}"
                )
        else:
            print(f"  [SKIP] RECORDER_IDENTIFIER_COLLISION: create R1 failed: {resp.text}")

    # ── 群組 6c：Point/Deployment Collision ──────────────────────────────────

    def run_point_deployment_collision_group(self, admin_token: str) -> None:
        print("\n=== Point/Deployment Collision ===")
        headers = self._headers(admin_token)

        # POINT_NAME_COLLISION：update 不查 RESERVED，改名後 restore 舊 point
        coll_pt1_name = f"coll-pt1-{self.ts}"
        coll_pt2_name = f"coll-pt2-{self.ts}"
        resp = self.client.post(
            f"{API_BASE}/points/",
            json={"name": coll_pt1_name, "project_id": self.project_id},
            headers=headers,
        )
        if resp.is_success:
            self.coll_pt1_id = resp.json()["id"]
            resp2 = self.client.post(
                f"{API_BASE}/points/",
                json={"name": coll_pt2_name, "project_id": self.project_id},
                headers=headers,
            )
            if resp2.is_success:
                self.coll_pt2_id = resp2.json()["id"]
                self.client.delete(f"{API_BASE}/points/{self.coll_pt2_id}", headers=headers)
                self.client.put(
                    f"{API_BASE}/points/{self.coll_pt1_id}",
                    json={"name": coll_pt2_name},
                    headers=headers,
                )
                resp3 = self.client.post(
                    f"{API_BASE}/points/{self.coll_pt2_id}/restore",
                    headers=headers,
                )
                self.check("POINT_NAME_COLLISION", resp3, "POINT_NAME_COLLISION", 400)
            else:
                print(f"  [SKIP] POINT_NAME_COLLISION: create PT2 failed: {resp2.text}")
        else:
            print(f"  [SKIP] POINT_NAME_COLLISION: create PT1 failed: {resp.text}")

        # DEPLOYMENT_PHASE_COLLISION：create_deployment 自動分配 phase
        # setup_deployment 已有 phase=1 → 新建 D1 得 phase=2 → 刪除 D1
        # → 新建 D2 max_active=1，得 phase=2 → restore D1 = COLLISION
        resp = self.client.post(
            f"{API_BASE}/deployments/",
            json={"point_id": self.point_id, "recorder_id": self.recorder_id},
            headers=headers,
        )
        if resp.is_success:
            self.coll_dep1_id = resp.json()["id"]
            self.client.delete(
                f"{API_BASE}/deployments/{self.coll_dep1_id}", headers=headers
            )
            resp2 = self.client.post(
                f"{API_BASE}/deployments/",
                json={"point_id": self.point_id, "recorder_id": self.recorder_id},
                headers=headers,
            )
            if resp2.is_success:
                self.coll_dep2_id = resp2.json()["id"]
                resp3 = self.client.post(
                    f"{API_BASE}/deployments/{self.coll_dep1_id}/restore",
                    headers=headers,
                )
                self.check(
                    "DEPLOYMENT_PHASE_COLLISION", resp3, "DEPLOYMENT_PHASE_COLLISION", 400
                )
            else:
                print(
                    f"  [SKIP] DEPLOYMENT_PHASE_COLLISION: create D2 failed: {resp2.text}"
                )
        else:
            print(f"  [SKIP] DEPLOYMENT_PHASE_COLLISION: create D1 failed: {resp.text}")

    # ── 群組 6d：Audio (Duplicate / Reserved / Collision) ─────────────────────

    def run_audio_group(self, admin_token: str) -> None:
        print("\n=== Audio Object Key ===")
        headers = self._headers(admin_token)
        key_a = f"test-err-{self.ts}/a.wav"
        key_b = f"test-err-{self.ts}/b.wav"

        # AUDIO_OBJECT_KEY_DUPLICATE：POST /audio/ 直接建立（不需 MinIO）
        resp = self.client.post(
            f"{API_BASE}/audio/",
            json={
                "deployment_id": self.deployment_id,
                "file_name": f"err-a-{self.ts}.wav",
                "object_key": key_a,
            },
            headers=headers,
        )
        if not resp.is_success:
            print(f"  [SKIP] AUDIO tests: create audio failed: {resp.text}")
            return
        self.audio_id_1 = resp.json()["id"]

        resp2 = self.client.post(
            f"{API_BASE}/audio/",
            json={
                "deployment_id": self.deployment_id,
                "file_name": f"err-a2-{self.ts}.wav",
                "object_key": key_a,
            },
            headers=headers,
        )
        self.check("AUDIO_OBJECT_KEY_DUPLICATE", resp2, "AUDIO_OBJECT_KEY_DUPLICATE", 400)

        # AUDIO_OBJECT_KEY_RESERVED：soft-delete audio_id_1，再建立同 key
        self.client.delete(
            f"{API_BASE}/audio/{self.audio_id_1}",
            headers=headers,
        )
        resp3 = self.client.post(
            f"{API_BASE}/audio/",
            json={
                "deployment_id": self.deployment_id,
                "file_name": f"err-a3-{self.ts}.wav",
                "object_key": key_a,
            },
            headers=headers,
        )
        self.check("AUDIO_OBJECT_KEY_RESERVED", resp3, "AUDIO_OBJECT_KEY_RESERVED", 400)

        # AUDIO_OBJECT_KEY_COLLISION：
        # audio_id_1 soft-deleted (key=a)
        # 建立 audio_id_2 (key=b)，update audio_id_2 改 key=a（update 無 RESERVED 檢查）
        # restore audio_id_1 → COLLISION（audio_id_2 active with key=a）
        resp4 = self.client.post(
            f"{API_BASE}/audio/",
            json={
                "deployment_id": self.deployment_id,
                "file_name": f"err-b-{self.ts}.wav",
                "object_key": key_b,
            },
            headers=headers,
        )
        if resp4.is_success:
            self.audio_id_2 = resp4.json()["id"]
            self.client.put(
                f"{API_BASE}/audio/{self.audio_id_2}",
                json={"object_key": key_a},
                headers=headers,
            )
            resp5 = self.client.post(
                f"{API_BASE}/audio/{self.audio_id_1}/restore",
                headers=headers,
            )
            self.check("AUDIO_OBJECT_KEY_COLLISION", resp5, "AUDIO_OBJECT_KEY_COLLISION", 400)
        else:
            print(f"  [SKIP] AUDIO_OBJECT_KEY_COLLISION: create audio B failed: {resp4.text}")

    # ── 群組 6e：Upload ───────────────────────────────────────────────────────

    def run_upload_group(self, admin_token: str) -> None:
        print("\n=== Upload ===")
        headers = self._headers(admin_token)

        # UPLOAD_ALL_FILES_SKIPPED：所有 filename 格式無效，job 建立前的驗證即 skip 全部
        resp = self.client.post(
            f"{API_BASE}/audio-upload-jobs/",
            json={
                "deployment_id": self.deployment_id,
                "files": [{"name": "invalid-not-parseable.wav", "size": 1000}],
            },
            headers=headers,
        )
        self.check("UPLOAD_ALL_FILES_SKIPPED", resp, "UPLOAD_ALL_FILES_SKIPPED", 400)

    # ── 群組 7：Recorder ─────────────────────────────────────────────────────

    def run_recorder_group(self, admin_token: str) -> None:
        print("\n=== Recorder ===")
        headers = self._headers(admin_token)

        resp = self.client.delete(
            f"{API_BASE}/recorders/{self.recorder_id}", headers=headers
        )
        self.check("RECORDER_HAS_DEPLOYMENTS", resp, "RECORDER_HAS_DEPLOYMENTS", 400)

    # ── 群組 8：OAuth ────────────────────────────────────────────────────────

    def run_oauth_group(self, admin_token: str) -> None:
        print("\n=== OAuth ===")
        headers = self._headers(admin_token)

        resp = self.client.delete(f"{API_BASE}/users/me/oauth/unlink", headers=headers)
        self.check("OAUTH_NOT_LINKED", resp, "OAUTH_NOT_LINKED", 400)

    # ── 群組 9：Password Reset ───────────────────────────────────────────────

    def run_password_reset_group(self) -> None:
        print("\n=== Password Reset ===")

        resp = self.client.post(
            f"{API_BASE}/auth/reset-password",
            json={"token": "fake-xxx", "new_password": "newpassword123"},
        )
        self.check("PASSWORD_RESET_TOKEN_INVALID", resp, "PASSWORD_RESET_TOKEN_INVALID", 400)

    # ── 摘要 ─────────────────────────────────────────────────────────────────

    def print_summary(self) -> None:
        passed = sum(1 for _, ok, _ in self.results if ok)
        failed = sum(1 for _, ok, _ in self.results if not ok)
        total = len(self.results)

        print(f"\n{'=' * 50}")
        print(f"結果: {passed} PASS / {failed} FAIL / {total} 共")

        if failed:
            print("失敗項目:")
            for label, ok, actual in self.results:
                if not ok:
                    print(f"  - {label}: {actual}")

        print("\n跳過項目 (共 {count} 個):".format(count=len(SKIP_LIST)))
        for code, reason in SKIP_LIST:
            print(f"  - {code}: {reason}")

    def run(self) -> None:
        admin_token = self._login(ADMIN_EMAIL, ADMIN_PASSWORD, "admin login")
        self.setup(admin_token)
        user_token = self._login(self.user_email, "testpass123", "user login")
        try:
            self.run_auth_group(admin_token)
            self.run_not_found_group(admin_token)
            self.run_permission_group(admin_token, user_token)
            self.run_validation_group(admin_token)
            self.run_duplicate_group(admin_token)
            self.run_reserved_group(admin_token)
            self.run_collision_group(admin_token)
            self.run_point_deployment_collision_group(admin_token)
            self.run_audio_group(admin_token)
            self.run_upload_group(admin_token)
            self.run_recorder_group(admin_token)
            self.run_oauth_group(admin_token)
            self.run_password_reset_group()
        finally:
            self.teardown(admin_token)
        self.print_summary()


if __name__ == "__main__":
    ErrorTestSuite().run()
