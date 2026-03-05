"""
上傳測試清理腳本。

刪除 upload_test.py 對 deployment_id=351 上傳的所有測試資料：
- 取消進行中的 upload jobs
- 刪除 MinIO 物件
- 刪除 DB 的 upload_tasks、audio_info 記錄

使用方式:
    python scripts/upload_test_cleanup.py [--dry-run]
"""

import argparse
import os
import sys

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from botocore.exceptions import ClientError

from sqlalchemy import text

from scripts.connections import get_db_session, get_minio_client

DEPLOYMENT_ID = 351
BUCKET = "taiwanpower2nd"


def cleanup(dry_run: bool = False) -> None:
    db = get_db_session()
    s3 = get_minio_client()

    prefix = "[DRY-RUN] " if dry_run else ""

    try:
        # 1. 查出所有相關 audio（含軟刪除）
        rows = db.execute(
            text("""
            SELECT a.id, a.object_key, a.upload_status, a.is_deleted
            FROM audio_info a
            WHERE a.deployment_id = :dep_id
            ORDER BY a.id
            """),
            {"dep_id": DEPLOYMENT_ID},
        ).fetchall()

        if not rows:
            print("找不到任何 audio 記錄，無需清理。")
            return

        print(f"找到 {len(rows)} 筆 audio 記錄:")
        for r in rows:
            print(f"  id={r[0]} object_key={r[1]} status={r[2]} deleted={r[3]}")

        audio_ids = [r[0] for r in rows]
        object_keys = [r[1] for r in rows]

        # 2. 取消進行中的 multipart uploads（查 upload_id）
        upload_rows = db.execute(
            text("""
            SELECT id, upload_id, object_key
            FROM upload_tasks
            WHERE audio_id = ANY(:ids) AND upload_id IS NOT NULL
            """),
            {"ids": audio_ids},
        ).fetchall()

        for task_id, upload_id, object_key in upload_rows:
            print(f"{prefix}Aborting multipart upload: {object_key} upload_id={upload_id[:16]}...")
            if not dry_run:
                try:
                    s3.abort_multipart_upload(
                        Bucket=BUCKET, Key=object_key, UploadId=upload_id
                    )
                except ClientError as e:
                    print(f"  警告: abort 失敗 ({e})")

        # 3. 刪除 MinIO 物件
        print(f"\n{prefix}刪除 MinIO 物件 ({len(object_keys)} 個):")
        for key in object_keys:
            print(f"  {prefix}DELETE {BUCKET}/{key}")
            if not dry_run:
                try:
                    s3.delete_object(Bucket=BUCKET, Key=key)
                except ClientError as e:
                    print(f"  警告: 刪除失敗 ({e})")

        # 4. 刪除 DB 記錄
        print(f"\n{prefix}刪除 DB 記錄:")

        task_count = db.execute(
            text("SELECT COUNT(*) FROM upload_tasks WHERE audio_id = ANY(:ids)"),
            {"ids": audio_ids},
        ).scalar()
        print(f"  {prefix}DELETE upload_tasks ({task_count} 筆)")

        job_rows = db.execute(
            text("SELECT DISTINCT job_id FROM upload_tasks WHERE audio_id = ANY(:ids)"),
            {"ids": audio_ids},
        ).fetchall()

        if not dry_run:
            db.execute(
                text("DELETE FROM upload_tasks WHERE audio_id = ANY(:ids)"),
                {"ids": audio_ids},
            )

        print(f"  {prefix}DELETE audio_info ({len(audio_ids)} 筆)")
        if not dry_run:
            db.execute(
                text("DELETE FROM audio_info WHERE id = ANY(:ids)"),
                {"ids": audio_ids},
            )

        # 刪除沒有任何子任務的 upload_jobs
        for (job_id,) in job_rows:
            remaining = db.execute(
                text("SELECT COUNT(*) FROM upload_tasks WHERE job_id = :jid"),
                {"jid": job_id},
            ).scalar()
            if remaining == 0:
                print(f"  {prefix}DELETE upload_jobs job_id={job_id}")
                if not dry_run:
                    db.execute(
                        text("DELETE FROM upload_jobs WHERE id = :jid"), {"jid": job_id}
                    )

        if not dry_run:
            db.commit()
            print("\n清理完成。")
        else:
            print("\n[DRY-RUN] 以上為預覽，未實際執行。加上 --no-dry-run 執行。")

    except Exception as e:
        db.rollback()
        print(f"錯誤: {e}")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="預覽模式（預設），不實際執行",
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="實際執行刪除",
    )
    args = parser.parse_args()
    cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
