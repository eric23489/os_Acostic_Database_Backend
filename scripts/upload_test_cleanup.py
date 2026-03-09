"""
上傳測試資源清理腳本。

讀取 upload_test.py 產生的 .upload_test_state.json，
依反序永久刪除所有測試建立的資源。

使用方式:
    python scripts/upload_test_cleanup.py
"""

import json
import sys
from pathlib import Path

import httpx

# ── 設定 ──────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "aaa@example.com"
PASSWORD = "aaa"
SCRIPTS_DIR = Path(__file__).parent
STATE_FILE = SCRIPTS_DIR / ".upload_test_state.json"


def login(client: httpx.Client) -> str:
    resp = client.post(
        f"{API_BASE}/users/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    resp.raise_for_status()
    print("[login] OK")
    return resp.json()["access_token"]


def hard_delete(client: httpx.Client, resource: str, resource_id: int) -> bool:
    resp = client.delete(f"{API_BASE}/{resource}/{resource_id}/permanent")
    if resp.is_success:
        print(f"  {resource.rstrip('s')} {resource_id} 刪除")
        return True
    print(
        f"  {resource.rstrip('s')} {resource_id} 刪除失敗:"
        f" {resp.status_code} {resp.text[:80]}"
    )
    return False


def cleanup(
    client: httpx.Client,
    audio_ids: list[int],
    deployment_id: int | None,
    point_id: int | None,
    project_id: int | None,
    recorder_id: int | None,
    should_cleanup_recorder: bool,
) -> int:
    """刪除資源，回傳失敗數。"""
    fails = 0
    print("\n[cleanup]")

    for audio_id in audio_ids:
        if not hard_delete(client, "audio", audio_id):
            fails += 1

    if deployment_id:
        if not hard_delete(client, "deployments", deployment_id):
            fails += 1

    if point_id:
        if not hard_delete(client, "points", point_id):
            fails += 1

    if project_id:
        if not hard_delete(client, "projects", project_id):
            fails += 1

    if recorder_id and should_cleanup_recorder:
        if not hard_delete(client, "recorders", recorder_id):
            fails += 1

    print("[cleanup] 完成")
    return fails


def main() -> None:
    if not STATE_FILE.exists():
        print(f"[error] 找不到 {STATE_FILE.name}，請先執行 upload_test.py")
        sys.exit(1)

    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    print(f"[state] 讀取 {STATE_FILE.name}:")
    for key, value in state.items():
        print(f"  {key}: {value}")

    with httpx.Client(timeout=60) as client:
        token = login(client)
        client.headers["Authorization"] = f"Bearer {token}"

        # 相容舊格式（audio_id 單值）與新格式（audio_ids 清單）
        raw = state.get("audio_ids") or (
            [state["audio_id"]] if state.get("audio_id") else []
        )

        fails = cleanup(
            client,
            audio_ids=raw,
            deployment_id=state.get("deployment_id"),
            point_id=state.get("point_id"),
            project_id=state.get("project_id"),
            recorder_id=state.get("recorder_id"),
            should_cleanup_recorder=state.get("should_cleanup_recorder", False),
        )

    if fails == 0:
        STATE_FILE.unlink()
        print(f"\n{STATE_FILE.name} 已刪除")
        sys.exit(0)
    else:
        print(f"\n{fails} 個資源刪除失敗，{STATE_FILE.name} 保留供重試")
        sys.exit(1)


if __name__ == "__main__":
    main()
