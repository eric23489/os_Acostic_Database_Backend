import os
import sys
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 確保可以匯入 app 模組
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from app.core.config import settings


def get_db_session():
    """
    取得資料庫連線 Session (腳本專用)
    強制連線至 localhost
    """
    database_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@localhost:{settings.postgres_port}/{settings.postgres_db}"
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_minio_client():
    """
    取得 MinIO Client (腳本專用)
    強制連線至 localhost
    """
    # 假設 MinIO 在本機的 Port 是 settings.minio_port (通常是 9000)
    endpoint_url = f"http://localhost:{settings.minio_port}"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
