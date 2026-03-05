"""
MinIO 服务。

提供 S3 兼容的物件储存操作，包括分段上传支援。
"""

import logging

from botocore.exceptions import ClientError

from app.core.minio import get_s3_client

logger = logging.getLogger(__name__)


class MinioService:
    """MinIO/S3 服务类。"""

    def __init__(self):
        self.s3_client = get_s3_client()

    # =========================================================================
    # Bucket Operations
    # =========================================================================

    def create_bucket(self, bucket_name: str) -> None:
        """
        建立 bucket (如果不存在)。

        Args:
            bucket_name: Bucket 名称
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.debug(f"Bucket '{bucket_name}' already exists")
        except ClientError:
            self.s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created bucket '{bucket_name}'")

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        检查 bucket 是否存在。

        Args:
            bucket_name: Bucket 名称

        Returns:
            bool: 是否存在
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False

    # =========================================================================
    # Object Operations
    # =========================================================================

    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
        method: str = "put_object",
    ) -> str:
        """
        产生 presigned URL。

        Args:
            bucket: Bucket 名称
            key: Object key
            expires_in: 有效期 (秒)
            method: HTTP 方法 (put_object, get_object)

        Returns:
            presigned URL
        """
        return self.s3_client.generate_presigned_url(
            ClientMethod=method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def get_object_size(self, bucket: str, key: str) -> int | None:
        """
        取得物件大小。

        Args:
            bucket: Bucket 名称
            key: Object key

        Returns:
            档案大小 (bytes)，不存在则回传 None
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            return response["ContentLength"]
        except ClientError:
            return None

    def delete_object(self, bucket: str, key: str) -> None:
        """
        删除物件。

        Args:
            bucket: Bucket 名称
            key: Object key
        """
        self.s3_client.delete_object(Bucket=bucket, Key=key)

    # =========================================================================
    # Multipart Upload Operations
    # =========================================================================

    def create_multipart_upload(self, bucket: str, key: str) -> str:
        """
        初始化分段上传。

        Args:
            bucket: Bucket 名称
            key: Object key

        Returns:
            upload_id: 分段上传 ID
        """
        response = self.s3_client.create_multipart_upload(
            Bucket=bucket,
            Key=key,
            ChecksumAlgorithm="SHA256",
        )
        upload_id = response["UploadId"]
        logger.debug(f"Created multipart upload: {bucket}/{key} -> {upload_id}")
        return upload_id

    def generate_part_upload_url(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = 3600,
    ) -> str:
        """
        产生单一 part 的 presigned URL。

        Args:
            bucket: Bucket 名称
            key: Object key
            upload_id: 分段上传 ID
            part_number: Part 编号 (从 1 开始)
            expires_in: 有效期 (秒)

        Returns:
            presigned URL
        """
        return self.s3_client.generate_presigned_url(
            ClientMethod="upload_part",
            Params={
                "Bucket": bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
                "ChecksumAlgorithm": "SHA256",
            },
            ExpiresIn=expires_in,
        )

    def complete_multipart_upload(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict],
    ) -> str:
        """
        完成分段上传，合并所有 parts。

        Args:
            bucket: Bucket 名称
            key: Object key
            upload_id: 分段上传 ID
            parts: Part 列表 [{"PartNumber": 1, "ETag": "xxx"}, ...]

        Returns:
            ETag of the completed object (stripped of quotes)
        """
        response = self.s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )
        logger.info(f"Completed multipart upload: {bucket}/{key}")
        return response["ETag"].strip('"')

    def read_object_range(self, bucket: str, key: str, start: int, end: int) -> bytes:
        """
        讀取物件指定 byte range。

        Args:
            bucket: Bucket 名称
            key: Object key
            start: 起始 byte（含）
            end: 結束 byte（含）

        Returns:
            指定範圍的 bytes
        """
        response = self.s3_client.get_object(
            Bucket=bucket, Key=key, Range=f"bytes={start}-{end}"
        )
        return response["Body"].read()

    def abort_multipart_upload(
        self, bucket: str, key: str, upload_id: str
    ) -> None:
        """
        取消分段上传，清理已上传的 parts。

        Args:
            bucket: Bucket 名称
            key: Object key
            upload_id: 分段上传 ID
        """
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
            )
            logger.info(f"Aborted multipart upload: {bucket}/{key}")
        except ClientError as e:
            logger.warning(f"Failed to abort multipart upload: {e}")

    def list_multipart_uploads(self, bucket: str) -> list[dict]:
        """
        列出所有进行中的分段上传。

        Args:
            bucket: Bucket 名称

        Returns:
            分段上传列表
        """
        response = self.s3_client.list_multipart_uploads(Bucket=bucket)
        return response.get("Uploads", [])
