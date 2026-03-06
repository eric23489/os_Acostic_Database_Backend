"""
實際 API 下載測試腳本。

使用方式:
    python scripts/download_test.py [--deployment-id N] [--audio-id N]
                                    [--count N] [--expires-in N]
                                    [--output-dir PATH] [--dry-run]

預設從 deployment_id=351 下載 1 個 COMPLETED 音檔。
"""

import argparse
import os
import socket
import sys
import time

import httpx

# ── 設定 ──────────────────────────────────────────────
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "aaa@example.com"
PASSWORD = "aaa"
DEFAULT_DEPLOYMENT_ID = 351
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# presigned URL 的 hostname 是 Docker 內部 minio:9000
# 透過 monkeypatching getaddrinfo 讓 minio 解析至 localhost
_original_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, port, *args, **kwargs):
    if host == "minio":
        host = "127.0.0.1"
    return _original_getaddrinfo(host, port, *args, **kwargs)


socket.getaddrinfo = _patched_getaddrinfo


# ── 工具函式 ──────────────────────────────────────────
def login(client: httpx.Client) -> str:
    """POST /users/login，回傳 access_token。"""
    resp = client.post(
        f"{API_BASE}/users/login",
        data={"username": EMAIL, "password": PASSWORD},
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print("[login] OK")
    return token


def list_completed_audios(
    client: httpx.Client,
    deployment_id: int,
    count: int | None,
) -> list[dict]:
    """GET /audio/?deployment_id=&limit= 並篩選 upload_status=completed。"""
    limit = count if count is not None else 1000
    resp = client.get(
        f"{API_BASE}/audio/",
        params={"deployment_id": deployment_id, "limit": limit},
    )
    resp.raise_for_status()
    data = resp.json()
    audios = data.get("items", [])

    # 過濾 upload_status == "completed"（server 端 download-url 也會驗證）
    completed = [a for a in audios if a.get("upload_status") == "completed"]

    if not completed:
        # 若回應不含 upload_status 欄位，則回傳全部（server 端自行驗證）
        completed = audios

    if count is not None:
        completed = completed[:count]

    print(f"[list] 找到 {len(completed)} 個音檔（deployment_id={deployment_id}）")
    return completed


def get_audio_by_id(client: httpx.Client, audio_id: int) -> dict:
    """GET /audio/{audio_id}。"""
    resp = client.get(f"{API_BASE}/audio/{audio_id}")
    resp.raise_for_status()
    return resp.json()


def download_audio(
    client: httpx.Client,
    audio: dict,
    output_dir: str,
    expires_in: int,
    dry_run: bool,
) -> bool:
    """
    取得 presigned URL 並下載音檔。

    回傳 True 表示成功，False 表示失敗。
    """
    audio_id = audio["id"]
    file_name = audio.get("file_name", f"audio_{audio_id}")

    # 1. 取得 presigned URL
    resp = client.get(
        f"{API_BASE}/audio/{audio_id}/download-url",
        params={"expires_in": expires_in},
    )
    if not resp.is_success:
        print(f"[download] {file_name}  SKIP ({resp.status_code}: {resp.json().get('detail', '')})")
        return False

    url_data = resp.json()
    presigned_url: str = url_data["presigned_url"]
    expected_size: int | None = url_data.get("file_size")
    file_name = url_data.get("file_name", file_name)

    # 2. dry-run 模式：只印 URL
    if dry_run:
        print(f"[dry-run] {file_name}  URL={presigned_url[:80]}...")
        return True

    # 3. 串流下載
    output_path = os.path.join(output_dir, file_name)
    downloaded_bytes = 0
    t0 = time.time()

    try:
        with httpx.stream("GET", presigned_url, timeout=300) as stream_resp:
            stream_resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in stream_resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
    except Exception as exc:
        print(f"[download] {file_name}  FAIL ({exc})")
        return False

    elapsed = time.time() - t0
    speed_mbps = downloaded_bytes / elapsed / 1024 / 1024 if elapsed > 0 else 0
    size_mb = downloaded_bytes / 1024 / 1024

    # 4. 驗證大小
    if expected_size is not None and downloaded_bytes != expected_size:
        print(
            f"[download] {file_name}  {size_mb:.1f} MB  {speed_mbps:.1f} MB/s"
            f"  FAIL (size mismatch: got {downloaded_bytes}, expected {expected_size})"
        )
        return False

    print(f"[download] {file_name}  {size_mb:.1f} MB  {speed_mbps:.1f} MB/s  OK")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="透過 API presigned URL 下載音檔")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--deployment-id", type=int, default=DEFAULT_DEPLOYMENT_ID, help="從此 deployment 列出音檔")
    group.add_argument("--audio-id", type=int, help="指定單一 audio ID")
    parser.add_argument("--count", default="1", help="下載數量，或 'all'（與 --audio-id 互斥）")
    parser.add_argument("--expires-in", type=int, default=300, help="presigned URL 有效秒數")
    parser.add_argument("--output-dir", default=os.path.join(SCRIPTS_DIR, "tmp_download"), help="儲存目錄")
    parser.add_argument("--dry-run", action="store_true", help="僅取得 URL，不實際下載")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    with httpx.Client(timeout=60) as client:
        token = login(client)
        client.headers.update({"Authorization": f"Bearer {token}"})

        # 取得音檔清單
        if args.audio_id is not None:
            audio = get_audio_by_id(client, args.audio_id)
            audios = [audio]
            print(f"[list] 指定 audio_id={args.audio_id}（{audio.get('file_name', '')}）")
        else:
            count = None if args.count == "all" else int(args.count)
            audios = list_completed_audios(client, args.deployment_id, count)

        if not audios:
            print("沒有可下載的音檔，結束。")
            sys.exit(0)

        # 下載
        success = 0
        for audio in audios:
            ok = download_audio(
                client,
                audio,
                output_dir=args.output_dir,
                expires_in=args.expires_in,
                dry_run=args.dry_run,
            )
            if ok:
                success += 1

        action = "URL 取得" if args.dry_run else "下載"
        print(f"\n完成: {success}/{len(audios)} 個檔案{action}成功")

        if success < len(audios):
            sys.exit(1)


if __name__ == "__main__":
    main()
