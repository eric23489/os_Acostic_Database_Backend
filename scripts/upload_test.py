"""
完整音檔上傳整合測試腳本。

使用方式:
    python scripts/upload_test.py            # 上傳 1 個檔案（預設）
    python scripts/upload_test.py --count 3  # 上傳前 3 個檔案
    python scripts/upload_test.py --all      # 上傳全部檔案

前提條件:
  - API server 運行於 localhost:8000
  - .env 中 MINIO_IP_ADDRESS=192.168.1.21（與 MINIO_EXTERNAL_URL 同一實例）
  - admin 帳號 aaa@example.com / aaa
  - scripts/ 目錄下有 7505.*.wav 檔案

流程:
  1. setup: 建立 recorder / project / point / deployment
  2. 一次建立 upload job（含所有檔案）
  3. 每個 task 依序執行 multipart upload
  4. 驗證每個 audio 的 upload_status == completed
  5. 將資源 IDs 寫入 .upload_test_state.json（清理由 upload_test_cleanup.py 執行）
"""

import argparse
import base64
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import httpx

# ── 設定 ──────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "aaa@example.com"
PASSWORD = "aaa"
SCRIPTS_DIR = Path(__file__).parent
STATE_FILE = SCRIPTS_DIR / ".upload_test_state.json"


# ── 工具函式 ──────────────────────────────────────────────────────────────────
def sha256_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def find_test_wavs(count: int | None) -> list[Path]:
    candidates = sorted(SCRIPTS_DIR.glob("7505.*.wav"))
    if not candidates:
        print("[error] scripts/ 目錄下找不到 7505.*.wav")
        sys.exit(1)
    return candidates if count is None else candidates[:count]


def parse_sn(wav_path: Path) -> str:
    return wav_path.name.split(".")[0]


def save_state(
    project_id: int | None,
    point_id: int | None,
    deployment_id: int | None,
    audio_ids: list[int],
    recorder_id: int | None,
    should_cleanup_recorder: bool,
) -> None:
    state = {
        "project_id": project_id,
        "point_id": point_id,
        "deployment_id": deployment_id,
        "audio_ids": audio_ids,
        "recorder_id": recorder_id,
        "should_cleanup_recorder": should_cleanup_recorder,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"\n[state] 資源 IDs 已寫入 {STATE_FILE.name}")
    print("  清理請執行: python scripts/upload_test_cleanup.py")


# ── API 呼叫 ──────────────────────────────────────────────────────────────────
def login(client: httpx.Client) -> str:
    resp = client.post(
        f"{API_BASE}/users/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    resp.raise_for_status()
    print("[admin login] OK")
    return resp.json()["access_token"]


def setup_recorder(client: httpx.Client, sn: str) -> tuple[int, bool]:
    """
    嘗試建立 recorder。

    Returns:
        (recorder_id, should_cleanup)
        should_cleanup=True 表示本次新建，cleanup 需清理。
    """
    resp = client.post(
        f"{API_BASE}/recorders/",
        json={
            "brand": "OceanSound",
            "model": "SoundTrap",
            "sn": sn,
            "sensitivity": -180.0,
        },
    )
    if resp.is_success:
        recorder_id = resp.json()["id"]
        print(f"[setup] recorder 建立 id={recorder_id} sn={sn}")
        return recorder_id, True

    error_code = resp.json().get("error_code", "")
    if error_code in ("RECORDER_IDENTIFIER_RESERVED", "RECORDER_IDENTIFIER_DUPLICATE"):
        search_resp = client.get(f"{API_BASE}/recorders/", params={"search": sn})
        search_resp.raise_for_status()
        items = search_resp.json()["items"]
        matched = [r for r in items if r["sn"] == sn]
        if not matched:
            print(f"[error] 找不到既有 recorder sn={sn}")
            sys.exit(1)
        recorder_id = matched[0]["id"]
        print(f"[setup] recorder 既有 id={recorder_id} sn={sn}（cleanup 不清理）")
        return recorder_id, False

    resp.raise_for_status()
    raise RuntimeError(f"setup_recorder unexpected: {resp.text}")


def setup_project(client: httpx.Client, timestamp: str) -> int:
    suffix = format(random.randint(0, 0xFFFF), "04x")
    resp = client.post(
        f"{API_BASE}/projects/",
        json={"name": f"test-{timestamp}-{suffix}", "name_zh": "上傳測試專案"},
    )
    if not resp.is_success:
        print(f"[error] setup_project {resp.status_code}: {resp.text[:500]}")
    resp.raise_for_status()
    project_id = resp.json()["id"]
    print(f"[setup] project id={project_id}")
    return project_id


def setup_point(client: httpx.Client, project_id: int) -> int:
    resp = client.post(
        f"{API_BASE}/points/",
        json={"project_id": project_id, "name": "測試測點"},
    )
    resp.raise_for_status()
    point_id = resp.json()["id"]
    print(f"[setup] point id={point_id}")
    return point_id


def setup_deployment(client: httpx.Client, point_id: int, recorder_id: int) -> int:
    resp = client.post(
        f"{API_BASE}/deployments/",
        json={"point_id": point_id, "recorder_id": recorder_id},
    )
    resp.raise_for_status()
    deployment_id = resp.json()["id"]
    print(f"[setup] deployment id={deployment_id}")
    return deployment_id


def create_upload_job(
    client: httpx.Client,
    deployment_id: int,
    wav_paths: list[Path],
) -> tuple[str, list[dict]]:
    """
    建立上傳 job（含所有檔案）。

    Returns:
        (job_id, tasks)
        tasks: [{"task_id", "audio_id", "object_key", "file_name"}, ...]
    """
    files_payload = [{"name": p.name, "size": p.stat().st_size} for p in wav_paths]
    resp = client.post(
        f"{API_BASE}/audio-upload-jobs/",
        json={"deployment_id": deployment_id, "files": files_payload},
    )
    if not resp.is_success:
        print(f"[FAIL] create upload job {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()

    data = resp.json()
    job_id: str = data["job_id"]
    tasks: list[dict] = data.get("tasks", [])
    skipped: list[dict] = data.get("skipped_files", [])

    if skipped:
        print(f"[job] 跳過 {len(skipped)} 個檔案:")
        for s in skipped:
            print(f"  - {s['name']}: {s['reason']}")

    print(f"[job] job_id={job_id}  有效任務 {len(tasks)} 個")
    return job_id, tasks


def run_multipart_upload(
    client: httpx.Client,
    job_id: str,
    task_id: str,
    wav_path: Path,
) -> bool:
    """執行單一檔案的完整 multipart upload 流程。"""
    base_url = f"{API_BASE}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart"

    resp = client.post(f"{base_url}/init")
    resp.raise_for_status()
    init_data = resp.json()
    upload_id: str = init_data["upload_id"]
    total_parts: int = init_data["total_parts"]
    part_size: int = init_data["part_size"]
    print(f"    [PASS] multipart init  upload_id={upload_id[:16]}...")

    completed_parts: list[dict] = []

    with wav_path.open("rb") as f:
        for part_number in range(1, total_parts + 1):
            urls_resp = client.post(
                f"{base_url}/urls",
                json={"part_numbers": [part_number]},
            )
            urls_resp.raise_for_status()
            presigned_url: str = urls_resp.json()["parts"][0]["presigned_url"]

            f.seek((part_number - 1) * part_size)
            chunk = f.read(part_size)
            checksum = sha256_b64(chunk)

            t0 = time.time()
            put_resp = httpx.put(
                presigned_url,
                content=chunk,
                headers={
                    "x-amz-sdk-checksum-algorithm": "SHA256",
                    "x-amz-checksum-sha256": checksum,
                },
                timeout=300,
            )
            elapsed = time.time() - t0
            speed = len(chunk) / elapsed / 1024 / 1024

            if put_resp.status_code != 200:
                print(
                    f"    [FAIL] part {part_number} upload "
                    f"{put_resp.status_code}: {put_resp.text[:200]}"
                )
                return False

            etag = put_resp.headers.get("ETag", "")
            print(
                f"    [PASS] part {part_number}/{total_parts} "
                f"{len(chunk) / 1024 / 1024:.1f}MB  {speed:.1f} MB/s"
            )

            part_resp = client.post(
                f"{base_url}/part-complete",
                json={
                    "part_number": part_number,
                    "etag": etag,
                    "checksum_sha256": checksum,
                },
            )
            part_resp.raise_for_status()
            completed_parts.append(
                {
                    "part_number": part_number,
                    "etag": etag,
                    "checksum_sha256": checksum,
                }
            )

    complete_resp = client.post(
        f"{base_url}/complete",
        json={"parts": completed_parts},
    )
    if complete_resp.status_code != 200:
        print(
            f"    [FAIL] complete {complete_resp.status_code}: {complete_resp.json()}"
        )
        return False

    print("    [PASS] complete")
    return True


def verify_audio(client: httpx.Client, audio_id: int) -> bool:
    resp = client.get(f"{API_BASE}/audio/{audio_id}")
    resp.raise_for_status()
    audio = resp.json()
    upload_status = audio.get("upload_status")
    if upload_status != "completed":
        print(f"    [FAIL] upload_status={upload_status}")
        return False
    fs = audio.get("fs")
    channels = audio.get("audio_channels")
    duration = audio.get("record_duration")
    print(f"    [PASS] completed  fs={fs}  ch={channels}  dur={duration}s")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--count", type=int, default=1, help="上傳檔案數量（預設 1）")
    group.add_argument("--all", action="store_true", help="上傳全部檔案")
    args = parser.parse_args()

    if STATE_FILE.exists():
        print(f"[warn] 偵測到殘留的 {STATE_FILE.name}，請先執行 cleanup 再重跑：")
        print("  python scripts/upload_test_cleanup.py")
        sys.exit(1)

    count = None if args.all else args.count
    wav_paths = find_test_wavs(count)
    sn = parse_sn(wav_paths[0])
    timestamp = str(int(time.time()))

    recorder_id: int | None = None
    project_id: int | None = None
    point_id: int | None = None
    deployment_id: int | None = None
    audio_ids: list[int] = []
    should_cleanup_recorder = False

    passes = 0
    fails = 0

    with httpx.Client(timeout=60) as client:
        token = login(client)
        client.headers.update({"Authorization": f"Bearer {token}"})

        # ── setup ────────────────────────────────────────────────────────────
        try:
            recorder_id, should_cleanup_recorder = setup_recorder(client, sn)
            project_id = setup_project(client, timestamp)
            point_id = setup_point(client, project_id)
            deployment_id = setup_deployment(client, point_id, recorder_id)
        except Exception as exc:
            print(f"[error] setup 失敗: {exc}")
            save_state(
                project_id,
                point_id,
                deployment_id,
                audio_ids,
                recorder_id,
                should_cleanup_recorder,
            )
            sys.exit(1)

        # ── 測試 ─────────────────────────────────────────────────────────────
        try:
            total_size_mb = sum(p.stat().st_size for p in wav_paths) / 1024 / 1024
            print(
                f"\n=== Upload Test {len(wav_paths)} 個檔案 {total_size_mb:.1f} MB ==="
            )

            job_id, tasks = create_upload_job(client, deployment_id, wav_paths)

            if not tasks:
                fails += 1
                print("  [FAIL] 無有效任務")
            else:
                task_map = {t["file_name"]: t for t in tasks}

                for wav_path in wav_paths:
                    task = task_map.get(wav_path.name)
                    file_size_mb = wav_path.stat().st_size / 1024 / 1024

                    if task is None:
                        print(f"\n  [SKIP] {wav_path.name}（被跳過，無對應任務）")
                        continue

                    audio_id: int = task["audio_id"]
                    audio_ids.append(audio_id)

                    print(
                        f"\n  [{wav_path.name}]  {file_size_mb:.1f} MB"
                        f"  audio_id={audio_id}"
                    )

                    upload_ok = run_multipart_upload(
                        client, job_id, task["task_id"], wav_path
                    )
                    if upload_ok:
                        verify_ok = verify_audio(client, audio_id)
                        if verify_ok:
                            passes += 1
                        else:
                            fails += 1
                    else:
                        fails += 1

        except Exception as exc:
            print(f"  [FAIL] 未預期錯誤: {exc}")
            fails += 1

        finally:
            save_state(
                project_id,
                point_id,
                deployment_id,
                audio_ids,
                recorder_id,
                should_cleanup_recorder,
            )

    total = passes + fails
    print(f"\n結果: {passes}/{total} PASS")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
