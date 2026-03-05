# API Error List

本文件整理所有 API 錯誤回傳格式，供前後端開發與 AI 代理人參考。

## AppException 架構

所有 API 錯誤統一使用 `AppException`（`app/core/exceptions.py`）。
禁止在 service 層 raise `HTTPException`。

**dataclass 欄位：**
| 欄位 | 型別 | 說明 |
|------|------|------|
| `error_code` | str | 機器可讀識別碼，前端以此判斷錯誤類型 |
| `message` | str | 人可讀說明，可直接顯示給使用者 |
| `http_status` | int | HTTP 狀態碼 |
| `headers` | dict \| None | 選填，用於 WWW-Authenticate 等 header |

---

## 開發 SOP

### 新增錯誤常數
1. 查閱本文件，確認同義常數不存在
2. 在 `app/core/exceptions.py` 對應分類區塊末尾新增：
   ```python
   FOO_BAR_ERROR = AppException(
       error_code="FOO_BAR_ERROR",
       message="...",
       http_status=status.HTTP_4XX_...,
   )
   ```
3. 在 service 層 import 並 `raise FOO_BAR_ERROR`
4. 更新本文件對應分類表格

### 測試寫法
```python
with pytest.raises(AppException) as exc_info:
    service.some_method(...)

assert exc_info.value is FOO_BAR_ERROR   # 推薦：直接比對常數
# 或
assert exc_info.value.http_status == 400
assert exc_info.value.error_code == "FOO_BAR_ERROR"
```

---

## 回應格式

```json
{
  "error_code": "PROJECT_NOT_FOUND",
  "message": "Project not found",
  "detail": null
}
```

422 驗證錯誤格式：
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "detail": [{"field": "files.0.name", "message": "Invalid filename format"}]
}
```

前端應以 `error_code` 判斷錯誤類型，`message` 僅用於顯示。

---

## 1. 認證與授權 (Auth)

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `AUTH_TOKEN_INVALID` | 401 | Could not validate credentials |
| `AUTH_USER_INACTIVE` | 400 | Inactive user |
| `AUTH_INCORRECT_CREDENTIALS` | 401 | Incorrect email or password |
| `PERMISSION_DENIED` | 403 | The user doesn't have enough privileges |
| `PERMISSION_ADMIN_REQUIRED` | 403 | Admin permission required |
| `PERMISSION_RESTORE_DENIED` | 403 | Only the deleter or admin can restore this resource |

---

## 2. Project

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `PROJECT_NAME_REQUIRED` | 400 | Either 'name' or 'name_zh' must be provided. |
| `PROJECT_NOT_FOUND` | 404 | Project not found |
| `PROJECT_NAME_DUPLICATE` | 400 | Project with this name already exists |
| `PROJECT_NAME_RESERVED` | 400 | Name reserved by deleted project. Hard delete to release. |
| `PROJECT_NAME_COLLISION` | 400 | Active project with this name already exists. Cannot restore. |

---

## 3. Point

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `POINT_NOT_FOUND` | 404 | Point not found |
| `PROJECT_NOT_FOUND` | 404 | Project not found |
| `POINT_NAME_DUPLICATE` | 400 | Point name already exists in this project |
| `POINT_NAME_RESERVED` | 400 | Name reserved by deleted point. Hard delete to release. |
| `POINT_NAME_COLLISION` | 400 | Active point with this name already exists in the project. Cannot restore. |

---

## 4. Deployment

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `DEPLOYMENT_NOT_FOUND` | 404 | Deployment not found |
| `POINT_NOT_FOUND` | 404 | Point not found |
| `DEPLOYMENT_PHASE_COLLISION` | 400 | Active deployment with this phase already exists for the point. Cannot restore. |

---

## 5. Audio

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `AUDIO_NOT_FOUND` | 404 | Audio not found |
| `DEPLOYMENT_NOT_FOUND` | 404 | Deployment not found |
| `POINT_NOT_FOUND` | 404 | Point not found |
| `PROJECT_NOT_FOUND` | 404 | Project not found |
| `AUDIO_OBJECT_KEY_DUPLICATE` | 400 | Audio with this object_key already exists |
| `AUDIO_OBJECT_KEY_RESERVED` | 400 | object_key reserved by deleted audio. Hard delete to release. |
| `AUDIO_OBJECT_KEY_COLLISION` | 400 | Active audio with this object_key already exists. Cannot restore. |
| `AUDIO_UPLOAD_NOT_COMPLETED` | 400 | Audio upload not completed |
| `AUDIO_CONCURRENT_CONFLICT` | 409 | Concurrent write conflict on object_key. Please retry. |
| `MINIO_DELETE_FAILED` | 502 | Failed to delete file from storage. Database record was not deleted. |
| `AUDIO_DB_COMMIT_FAILED` | 500 | Failed to save audio records. Please retry. |

---

## 6. Upload Job

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `DEPLOYMENT_NOT_FOUND` | 404 | Deployment not found |
| `UPLOAD_JOB_NOT_FOUND` | 404 | Job not found |
| `UPLOAD_TASK_NOT_FOUND` | 404 | Task not found |
| `UPLOAD_MULTIPART_NOT_INIT` | 400 | Multipart upload not initialized |
| `UPLOAD_ALL_FILES_SKIPPED` | 400 | All files skipped: no valid files to upload |
| `MINIO_UPLOAD_FAILED` | 502 | Failed to complete file upload |

---

## 7. Recorder

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `RECORDER_NOT_FOUND` | 404 | Recorder not found |
| `RECORDER_IDENTIFIER_RESERVED` | 400 | Identifier reserved by deleted recorder. Hard delete to release. |
| `RECORDER_IDENTIFIER_COLLISION` | 400 | Active recorder with this brand/model/sn already exists. Cannot restore. |
| `RECORDER_HAS_DEPLOYMENTS` | 400 | Cannot delete recorder: deployments reference this recorder. Delete deployments first. |

---

## 8. User

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `USER_NOT_FOUND` | 404 | User not found |
| `USER_EMAIL_DUPLICATE` | 400 | UserInfo with the same email already exists. |
| `USER_EMAIL_COLLISION` | 400 | Active user with this email already exists. Cannot restore. |
| `USER_PASSWORD_TOO_SHORT` | 400 | Password must be at least 8 characters |

---

## 9. Password Reset

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `AUTH_USER_INACTIVE` | 400 | Inactive user |
| `PASSWORD_RESET_TOKEN_INVALID` | 400 | Invalid or expired reset token |
| `PASSWORD_RESET_TOKEN_EXPIRED` | 400 | Reset token has expired. Please request a new one. |
| `USER_PASSWORD_TOO_SHORT` | 400 | Password must be at least 8 characters |

---

## 10. OAuth (Google)

| error_code | HTTP Status | message |
|------------|-------------|---------|
| `OAUTH_NOT_CONFIGURED` | 500 | Google OAuth is not configured |
| `OAUTH_CODE_EXCHANGE_FAILED` | 401 | Failed to exchange authorization code |
| `AUTH_USER_INACTIVE` | 400 | Inactive user |
| `OAUTH_ALREADY_LINKED` | 400 | Account already linked to Google |
| `OAUTH_ACCOUNT_IN_USE` | 400 | This Google account is already linked to another user |
| `OAUTH_NOT_LINKED` | 400 | Account is not linked to Google |
| `OAUTH_PASSWORD_REQUIRED` | 400 | Please set a password before unlinking Google account |

---

## 統計

| HTTP Status | 數量 | 說明 |
|-------------|------|------|
| 400 Bad Request | 21 | 驗證失敗、重複、衝突 |
| 401 Unauthorized | 3 | 認證失敗 |
| 403 Forbidden | 3 | 權限不足 |
| 404 Not Found | 8 | 資源不存在 |
| 409 Conflict | 1 | 並發衝突 |
| 500 Server Error | 3 | 伺服器錯誤 |
| 502 Bad Gateway | 2 | 外部儲存錯誤 |
| **合計** | **41** | 41 AppException + 0 HTTPException |
