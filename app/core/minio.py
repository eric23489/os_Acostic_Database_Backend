import boto3
from botocore.client import Config
from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_ip_address}:{settings.minio_port}",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def get_s3_presigned_client():
    """產生 presigned URL 專用的 S3 client。

    若設定了 MINIO_EXTERNAL_URL，使用外部位址確保外部網路可存取；
    否則回退至內部位址，行為與 get_s3_client() 相同。
    """
    endpoint = (
        settings.minio_external_url
        or f"http://{settings.minio_ip_address}:{settings.minio_port}"
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
