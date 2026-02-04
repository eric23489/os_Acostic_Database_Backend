import sys
import os
import time
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal


def benchmark_audio_query(deployment_id: int):
    db = SessionLocal()
    try:
        print(f"--- Benchmarking Audio Query for Deployment ID: {deployment_id} ---")

        # 1. Measure Python execution time
        start_time = time.time()
        # We use text() to execute raw SQL for clarity in benchmark
        result = db.execute(
            text(
                "SELECT * FROM audio_info WHERE deployment_id = :did AND is_deleted = false"
            ),
            {"did": deployment_id},
        ).fetchall()
        end_time = time.time()
        print(f"Python Execution Time: {(end_time - start_time) * 1000:.2f} ms")
        print(f"Rows fetched: {len(result)}")

        # 2. Get Query Plan from Database
        print("\n--- Query Plan (EXPLAIN ANALYZE) ---")
        explain_result = db.execute(
            text(
                "EXPLAIN ANALYZE SELECT * FROM audio_info WHERE deployment_id = :did AND is_deleted = false"
            ),
            {"did": deployment_id},
        ).fetchall()

        for row in explain_result:
            print(row[0])

    finally:
        db.close()


if __name__ == "__main__":
    # Ensure you have some data in DB before running this
    # You can pass a deployment_id that exists
    benchmark_audio_query(5)
