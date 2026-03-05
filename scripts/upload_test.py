"""
實際 API 上傳測試腳本。

使用方式:
    python scripts/upload_test.py [--count N]

預設上傳 1 個檔案，--count all 上傳全部。
"""

import argparse
import base64
import glob
import hashlib
import os
import socket
import sys
import time

import httpx

# ── 設定 ──────────────────────────────────────────────
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "aaa@example.com"
PASSWORD = "aaa"
DEPLOYMENT_ID = 351
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PART_SIZE = 100 * 1024 * 1024  # 100MB

# presigned URL 的 hostname 是 Docker 內部 minio:9000
# 透過 monkeypatching getaddrinfo 讓 minio 解析至 localhost
_original_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, *args, **kwargs):
    if host == "minio":
        host = "127.0.0.1"
    return _original_getaddrinfo(host, port, *args, **kwargs)


socket.getaddrinfo = _patched_getaddrinfo


# ── 工具函式 ──────────────────────────────────────────
def compute_sha256(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def login(client: httpx.Client) -> str:
    resp = client.post(
        f"{API_BASE}/users/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[login] OK")
    return token


def create_job(client: httpx.Client, files: list[dict]) -> tuple[str, list[dict]]:
    resp = client.post(
        f"{API_BASE}/audio-upload-jobs/",
        json={"deployment_id": DEPLOYMENT_ID, "files": files},
    )
    if not resp.is_success:
        print(f"[create_job] {resp.status_code}: {resp.text[:300]}")
    resp.raise_for_status()
    data = resp.json()
    job_id = data["job_id"]
    skipped = data.get("skipped_files", [])
    if skipped:
        print(f"[job] 跳過 {len(skipped)} 個檔案:")
        for s in skipped:
            print(f"  - {s['name']}: {s['reason']}")
    tasks = data["tasks"]
    print(f"[job] 建立 job={job_id}，有效任務 {len(tasks)} 個")
    return job_id, tasks


def upload_file(client: httpx.Client, job_id: str, task: dict, file_path: str) -> bool:
    task_id = task["task_id"]
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    print(f"\n  [{file_name}] 大小={file_size / 1024 / 1024:.1f} MB")

    # 1. Init multipart
    resp = client.post(
        f"{API_BASE}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init"
    )
    resp.raise_for_status()
    init_data = resp.json()
    upload_id = init_data["upload_id"]
    total_parts = init_data["total_parts"]
    part_size = init_data["part_size"]
    print(f"  [init] upload_id={upload_id[:16]}..., total_parts={total_parts}")

    # 2. 取得所有 part URLs
    part_numbers = list(range(1, total_parts + 1))
    resp = client.post(
        f"{API_BASE}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls",
        json={"part_numbers": part_numbers},
    )
    resp.raise_for_status()
    url_map = {p["part_number"]: p["presigned_url"] for p in resp.json()["parts"]}

    # 3. 逐 part 上傳
    completed_parts = []
    with open(file_path, "rb") as f:
        for part_number in part_numbers:
            start = (part_number - 1) * part_size
            f.seek(start)
            chunk = f.read(part_size)

            sha256 = compute_sha256(chunk)
            t0 = time.time()
            upload_resp = httpx.put(
                url_map[part_number],
                content=chunk,
                headers={
                    "x-amz-sdk-checksum-algorithm": "SHA256",
                    "x-amz-checksum-sha256": sha256,
                },
                timeout=300,
            )
            elapsed = time.time() - t0
            speed = len(chunk) / elapsed / 1024 / 1024

            if upload_resp.status_code != 200:
                print(f"  [part {part_number}] FAIL {upload_resp.status_code}: {upload_resp.text[:200]}")
                return False

            etag = upload_resp.headers.get("ETag", "")
            print(f"  [part {part_number}/{total_parts}] {len(chunk)/1024/1024:.1f}MB  {speed:.1f} MB/s")

            # 4. 回報 part 完成
            resp = client.post(
                f"{API_BASE}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete",
                json={"part_number": part_number, "etag": etag, "checksum_sha256": sha256},
            )
            resp.raise_for_status()
            completed_parts.append({"part_number": part_number, "etag": etag, "checksum_sha256": sha256})

    # 5. 完成上傳
    resp = client.post(
        f"{API_BASE}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete",
        json={"parts": completed_parts},
    )
    if resp.status_code != 200:
        print(f"  [complete] FAIL {resp.status_code}: {resp.json()}")
        return False

    print(f"  [complete] OK")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", default="1", help="上傳檔案數量，或 'all'")
    args = parser.parse_args()

    wav_files = sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.wav")))
    if not wav_files:
        print("scripts/ 目錄下找不到 .wav 檔案")
        sys.exit(1)

    count = len(wav_files) if args.count == "all" else int(args.count)
    wav_files = wav_files[:count]
    print(f"準備上傳 {len(wav_files)} 個檔案到 deployment_id={DEPLOYMENT_ID}")

    with httpx.Client(timeout=60) as client:
        token = login(client)
        client.headers.update({"Authorization": f"Bearer {token}"})

        # 建立 job（帶檔案大小）
        files_payload = [
            {"name": os.path.basename(p), "size": os.path.getsize(p)}
            for p in wav_files
        ]
        job_id, tasks = create_job(client, files_payload)

        if not tasks:
            print("沒有可上傳的任務，結束。")
            return

        # 建立 task_id 對應表
        task_map = {t["file_name"]: t for t in tasks}

        success = 0
        for wav_path in wav_files:
            file_name = os.path.basename(wav_path)
            task = task_map.get(file_name)
            if not task:
                print(f"\n[skip] {file_name} 被跳過（無對應任務）")
                continue

            ok = upload_file(client, job_id, task, wav_path)
            if ok:
                success += 1

        print(f"\n完成: {success}/{len(wav_files)} 個檔案上傳成功")


if __name__ == "__main__":
    main()
