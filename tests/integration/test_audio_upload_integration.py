import uuid
from datetime import datetime

import httpx
import pytest

from app.core.config import settings
from app.enums.enums import UploadStatus
from app.models.audio import AudioInfo


@pytest.mark.integration
class TestAudioUploadIntegration:
    """批量上傳 API 整合測試 - 實際上傳檔案"""

    @pytest.fixture
    def test_file_content(self):
        """產生測試檔案內容 (1MB)"""
        return b"x" * (1024 * 1024)

    @pytest.fixture(autouse=True)
    def cleanup(self, s3_client):
        """測試後清理 MinIO 物件"""
        uploaded_objects: list[tuple[str, str]] = []  # (bucket, key)
        yield uploaded_objects

        # Cleanup logic runs after the test
        for bucket, key in uploaded_objects:
            try:
                s3_client.delete_object(Bucket=bucket, Key=key)
            except Exception as e:
                print(f"Error cleaning up MinIO object {bucket}/{key}: {e}")

    def generate_valid_filename(self, sn: str) -> str:
        """根據 SN 和時間產生有效的檔案名稱"""
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        return f"{sn}.{timestamp}.wav"

    def test_single_part_upload(
        self,
        api_client,
        auth_headers,
        test_deployment,
        test_file_content,
        s3_client,
        cleanup,
        db_session,
    ):
        """測試單 Part 小檔案上傳"""
        recorder_sn = test_deployment["recorder"].sn
        file_name = self.generate_valid_filename(recorder_sn)
        file_size = len(test_file_content)
        api_prefix = settings.api_prefix
        bucket = test_deployment["project"].name

        # 1. 建立上傳任務
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/",
            headers=auth_headers,
            json={
                "deployment_id": test_deployment["deployment"].id,
                "files": [{"name": file_name, "size": file_size}],
            },
        )
        assert response.status_code == 201, response.json()
        job = response.json()
        job_id = job["job_id"]
        task_id = job["tasks"][0]["task_id"]
        object_key = job["tasks"][0]["object_key"]
        cleanup.append((bucket, object_key))

        # 2. 初始化 Multipart
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init",
            headers=auth_headers,
        )
        assert response.status_code == 200, response.json()

        # 3. 取得 Part URL
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls",
            headers=auth_headers,
            json={"part_numbers": [1]},
        )
        assert response.status_code == 200, response.json()
        presigned_url = response.json()["parts"][0]["presigned_url"]

        # 4. 實際上傳檔案到 MinIO
        upload_response = httpx.put(presigned_url, content=test_file_content)
        assert upload_response.status_code == 200
        etag = upload_response.headers["ETag"]

        # 5. 回報 Part 完成
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete",
            headers=auth_headers,
            json={"part_number": 1, "etag": etag},
        )
        assert response.status_code == 200, response.json()

        # 6. 完成上傳
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete",
            headers=auth_headers,
            json={"parts": [{"part_number": 1, "etag": etag}]},
        )
        assert response.status_code == 200, response.json()

        # 7. 驗證 MinIO 檔案存在
        s3_response = s3_client.head_object(Bucket=bucket, Key=object_key)
        assert s3_response["ContentLength"] == file_size

        # 8. 驗證 DB 記錄 (新增)
        # 方式 A: 透過 object_key 查詢
        audio = (
            db_session.query(AudioInfo)
            .filter(
                AudioInfo.object_key == object_key,
                AudioInfo.is_deleted.is_(False),
            )
            .first()
        )

        assert audio is not None, "AudioInfo 記錄應存在"
        assert audio.upload_status == UploadStatus.COMPLETED
        assert audio.file_size == file_size
        assert audio.deployment_id == test_deployment["deployment"].id

        # 方式 B: 透過 deployment_id 查詢所有音檔
        audios = (
            db_session.query(AudioInfo)
            .filter(
                AudioInfo.deployment_id == test_deployment["deployment"].id,
                AudioInfo.is_deleted.is_(False),
            )
            .all()
        )

        assert len(audios) >= 1
        assert any(a.object_key == object_key for a in audios)

    @pytest.fixture
    def large_file_content(self):
        """產生測試檔案內容 (12MB)"""
        return b"y" * (12 * 1024 * 1024)

    def test_multi_part_upload(
        self,
        api_client,
        auth_headers,
        test_deployment,
        large_file_content,
        s3_client,
        cleanup,
    ):
        """測試多 Part 大檔案上傳"""
        recorder_sn = test_deployment["recorder"].sn
        file_name = self.generate_valid_filename(recorder_sn)
        file_size = len(large_file_content)
        api_prefix = settings.api_prefix
        bucket = test_deployment["project"].name
        part_size = 5 * 1024 * 1024  # 5MB

        # 1. 建立上傳任務
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/",
            headers=auth_headers,
            json={
                "deployment_id": test_deployment["deployment"].id,
                "files": [{"name": file_name, "size": file_size}],
            },
        )
        assert response.status_code == 201, response.json()
        job = response.json()
        job_id = job["job_id"]
        task_id = job["tasks"][0]["task_id"]
        object_key = job["tasks"][0]["object_key"]
        cleanup.append((bucket, object_key))

        # 2. 初始化
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init",
            headers=auth_headers,
        )
        assert response.status_code == 200, response.json()

        # 3. 取得 URLs & 4. 上傳 Parts
        completed_parts = []
        part_numbers = [1, 2, 3]
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls",
            headers=auth_headers,
            json={"part_numbers": part_numbers},
        )
        assert response.status_code == 200, response.json()
        urls_data = response.json()["parts"]

        for url_info in urls_data:
            part_number = url_info["part_number"]
            start = (part_number - 1) * part_size
            end = start + part_size
            chunk = large_file_content[start:end]

            upload_response = httpx.put(url_info["presigned_url"], content=chunk)
            assert upload_response.status_code == 200
            etag = upload_response.headers["ETag"]
            completed_parts.append({"part_number": part_number, "etag": etag})

        # 5. 回報 Parts 完成
        for part in completed_parts:
            api_client.post(
                f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete",
                headers=auth_headers,
                json=part,
            )

        # 6. 完成上傳
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete",
            headers=auth_headers,
            json={"parts": completed_parts},
        )
        assert response.status_code == 200, response.json()

        # 7. 驗證
        s3_response = s3_client.head_object(Bucket=bucket, Key=object_key)
        assert s3_response["ContentLength"] == file_size

    def test_batch_upload_two_files(
        self,
        api_client,
        auth_headers,
        test_deployment,
        test_file_content,
        cleanup,
        s3_client,
    ):
        """測試批量上傳 2 個檔案"""
        recorder_sn = test_deployment["recorder"].sn
        bucket = test_deployment["project"].name
        # 使用不同秒數確保時間戳不同 (檔名格式為 YYMMDDHHMMSS)
        import time

        files_to_upload = []
        for i in range(2):
            if i > 0:
                time.sleep(1.1)  # 等待超過 1 秒確保時間戳不同
            files_to_upload.append(
                {
                    "name": self.generate_valid_filename(recorder_sn),
                    "size": len(test_file_content),
                    "content": test_file_content,
                }
            )
        api_prefix = settings.api_prefix

        # 1. 建立上傳任務 for two files
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/",
            headers=auth_headers,
            json={
                "deployment_id": test_deployment["deployment"].id,
                "files": [
                    {"name": f["name"], "size": f["size"]} for f in files_to_upload
                ],
            },
        )
        assert response.status_code == 201, response.json()
        job = response.json()
        job_id = job["job_id"]
        tasks = job["tasks"]

        for i, task_data in enumerate(files_to_upload):
            task_id = tasks[i]["task_id"]
            object_key = tasks[i]["object_key"]
            cleanup.append((bucket, object_key))

            # Init
            init_res = api_client.post(
                f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init",
                headers=auth_headers,
            )
            assert init_res.status_code == 200

            # Get URL
            urls_res = api_client.post(
                f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls",
                headers=auth_headers,
                json={"part_numbers": [1]},
            )
            presigned_url = urls_res.json()["parts"][0]["presigned_url"]

            # Upload
            upload_res = httpx.put(presigned_url, content=task_data["content"])
            etag = upload_res.headers["ETag"]

            # Part Complete
            part_complete_res = api_client.post(
                f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete",
                headers=auth_headers,
                json={"part_number": 1, "etag": etag},
            )
            assert part_complete_res.status_code == 200

            # Complete
            complete_res = api_client.post(
                f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete",
                headers=auth_headers,
                json={"parts": [{"part_number": 1, "etag": etag}]},
            )
            assert complete_res.status_code == 200

            # 7. Verify each file
            s3_response = s3_client.head_object(Bucket=bucket, Key=object_key)
            assert s3_response["ContentLength"] == task_data["size"]

    def test_project_creates_bucket(
        self,
        api_client,
        auth_headers,
        s3_client,
    ):
        """測試建立 Project 時自動建立 MinIO Bucket"""
        unique_id = uuid.uuid4().hex[:6]
        project_name = f"test-bucket-{unique_id}"
        api_prefix = settings.api_prefix

        # 1. 建立 Project (透過 API)
        response = api_client.post(
            f"{api_prefix}/projects/",
            headers=auth_headers,
            json={"name": project_name, "name_zh": f"測試專案 {unique_id}"},
        )
        assert response.status_code == 200, response.json()

        # 2. 驗證 MinIO Bucket 已建立
        bucket_response = s3_client.head_bucket(Bucket=project_name)
        assert bucket_response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # 3. 清理: 刪除 Bucket (因為 Project 在 db_session rollback 後會消失)
        s3_client.delete_bucket(Bucket=project_name)

    def test_download_url_after_upload(
        self,
        api_client,
        auth_headers,
        test_deployment,
        test_file_content,
        s3_client,
        cleanup,
        db_session,
    ):
        """測試上傳完成後取得下載 URL 並驗證可下載"""
        recorder_sn = test_deployment["recorder"].sn
        file_name = self.generate_valid_filename(recorder_sn)
        file_size = len(test_file_content)
        api_prefix = settings.api_prefix
        bucket = test_deployment["project"].name

        # 1. 建立上傳任務
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/",
            headers=auth_headers,
            json={
                "deployment_id": test_deployment["deployment"].id,
                "files": [{"name": file_name, "size": file_size}],
            },
        )
        assert response.status_code == 201, response.json()
        job = response.json()
        job_id = job["job_id"]
        task_id = job["tasks"][0]["task_id"]
        object_key = job["tasks"][0]["object_key"]
        cleanup.append((bucket, object_key))

        # 2. 初始化 Multipart
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init",
            headers=auth_headers,
        )
        assert response.status_code == 200, response.json()

        # 3. 取得 Part URL
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls",
            headers=auth_headers,
            json={"part_numbers": [1]},
        )
        assert response.status_code == 200, response.json()
        presigned_url = response.json()["parts"][0]["presigned_url"]

        # 4. 實際上傳檔案到 MinIO
        upload_response = httpx.put(presigned_url, content=test_file_content)
        assert upload_response.status_code == 200
        etag = upload_response.headers["ETag"]

        # 5. 回報 Part 完成
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete",
            headers=auth_headers,
            json={"part_number": 1, "etag": etag},
        )
        assert response.status_code == 200, response.json()

        # 6. 完成上傳
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete",
            headers=auth_headers,
            json={"parts": [{"part_number": 1, "etag": etag}]},
        )
        assert response.status_code == 200, response.json()

        # 7. 取得 AudioInfo ID
        audio = (
            db_session.query(AudioInfo)
            .filter(
                AudioInfo.object_key == object_key,
                AudioInfo.is_deleted.is_(False),
            )
            .first()
        )
        assert audio is not None, "AudioInfo 記錄應存在"
        audio_id = audio.id

        # 8. 取得下載 URL
        response = api_client.get(
            f"{api_prefix}/audio/{audio_id}/download-url",
            headers=auth_headers,
        )
        assert response.status_code == 200, response.json()
        download_data = response.json()
        assert "presigned_url" in download_data
        assert download_data["expires_in"] == 3600
        assert download_data["file_name"] == file_name
        assert download_data["file_size"] == file_size

        # 9. 驗證可下載
        download_response = httpx.get(download_data["presigned_url"])
        assert download_response.status_code == 200
        assert len(download_response.content) == file_size
        assert download_response.content == test_file_content

    def test_download_url_with_custom_expires(
        self,
        api_client,
        auth_headers,
        test_deployment,
        test_file_content,
        s3_client,
        cleanup,
        db_session,
    ):
        """測試自訂下載 URL 有效期"""
        recorder_sn = test_deployment["recorder"].sn
        file_name = self.generate_valid_filename(recorder_sn)
        file_size = len(test_file_content)
        api_prefix = settings.api_prefix
        bucket = test_deployment["project"].name

        # 上傳檔案 (簡化流程)
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/",
            headers=auth_headers,
            json={
                "deployment_id": test_deployment["deployment"].id,
                "files": [{"name": file_name, "size": file_size}],
            },
        )
        job = response.json()
        job_id = job["job_id"]
        task_id = job["tasks"][0]["task_id"]
        object_key = job["tasks"][0]["object_key"]
        cleanup.append((bucket, object_key))

        # Init -> URLs -> Upload -> Part Complete -> Complete
        api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/init",
            headers=auth_headers,
        )
        urls_resp = api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/urls",
            headers=auth_headers,
            json={"part_numbers": [1]},
        )
        presigned_url = urls_resp.json()["parts"][0]["presigned_url"]
        upload_resp = httpx.put(presigned_url, content=test_file_content)
        etag = upload_resp.headers["ETag"]
        api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/part-complete",
            headers=auth_headers,
            json={"part_number": 1, "etag": etag},
        )
        api_client.post(
            f"{api_prefix}/audio-upload-jobs/{job_id}/tasks/{task_id}/multipart/complete",
            headers=auth_headers,
            json={"parts": [{"part_number": 1, "etag": etag}]},
        )

        # 取得 AudioInfo ID
        audio = (
            db_session.query(AudioInfo)
            .filter(AudioInfo.object_key == object_key)
            .first()
        )

        # 測試自訂 expires_in
        custom_expires = 7200
        response = api_client.get(
            f"{api_prefix}/audio/{audio.id}/download-url",
            headers=auth_headers,
            params={"expires_in": custom_expires},
        )
        assert response.status_code == 200
        assert response.json()["expires_in"] == custom_expires

    def test_download_url_not_found(
        self,
        api_client,
        auth_headers,
    ):
        """測試不存在的 Audio 回傳 404"""
        api_prefix = settings.api_prefix
        response = api_client.get(
            f"{api_prefix}/audio/999999/download-url",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_download_url_upload_not_completed(
        self,
        api_client,
        auth_headers,
        test_deployment,
        db_session,
    ):
        """測試 upload_status 非 completed 時回傳 400"""
        api_prefix = settings.api_prefix
        file_name = self.generate_valid_filename(test_deployment["recorder"].sn)

        # 建立上傳任務 (不完成上傳)
        response = api_client.post(
            f"{api_prefix}/audio-upload-jobs/",
            headers=auth_headers,
            json={
                "deployment_id": test_deployment["deployment"].id,
                "files": [{"name": file_name, "size": 1024}],
            },
        )
        job = response.json()
        object_key = job["tasks"][0]["object_key"]

        # 查詢 AudioInfo (此時 status 應為 pending)
        audio = (
            db_session.query(AudioInfo)
            .filter(AudioInfo.object_key == object_key)
            .first()
        )

        # 嘗試取得下載 URL
        response = api_client.get(
            f"{api_prefix}/audio/{audio.id}/download-url",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "not completed" in response.json()["message"]
