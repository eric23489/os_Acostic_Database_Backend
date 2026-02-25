# API Error List

本文件整理所有 API 錯誤回傳的 detail，方便前端開發與除錯參考。

---

## 1. 認證與授權 (Auth)

| HTTP Status | Detail | 位置 |
|-------------|--------|------|
| 401 | Could not validate credentials | core/auth.py |
| 400 | Inactive user | core/auth.py |
| 401 | Incorrect email or password | api_users.py |
| 403 | The user doesn't have enough privileges | core/auth.py, api_users.py |
| 403 | Admin permission required for permanent deletion | 多個 endpoint |
| 403 | Only the deleter or admin can restore this resource | 多個 endpoint |

---

## 2. Project

| HTTP Status | Detail |
|-------------|--------|
| 404 | Project not found |
| 400 | Either 'name' or 'name_zh' must be provided. |
| 400 | Project with this name already exists |
| 400 | Project with this Chinese name (name_zh) already exists |
| 400 | Name reserved by deleted project. Hard delete to release. |
| 400 | name_zh reserved by deleted project. Hard delete to release. |
| 400 | Active project with this name already exists. Cannot restore. |
| 400 | Active project with this name_zh already exists. Cannot restore. |

---

## 3. Point

| HTTP Status | Detail |
|-------------|--------|
| 404 | Point not found |
| 404 | Parent project not found |
| 400 | Point name already exists in this project |
| 400 | Name reserved by deleted point. Hard delete to release. |
| 400 | Active point with this name already exists in the project. Cannot restore. |

---

## 4. Deployment

| HTTP Status | Detail |
|-------------|--------|
| 404 | Deployment not found |
| 404 | Parent point not found |
| 404 | Parent project not found |
| 400 | Active deployment with this phase already exists for the point. Cannot restore. |

---

## 5. Audio

| HTTP Status | Detail |
|-------------|--------|
| 404 | Audio not found |
| 404 | Parent deployment not found |
| 404 | Parent point not found |
| 404 | Parent project not found |
| 400 | Audio with this object_key already exists |
| 400 | object_key reserved by deleted audio. Hard delete to release. |
| 400 | Active audio with this object_key already exists. Cannot restore. |
| 400 | Audio upload not completed. Current status: {audio.upload_status} |

---

## 6. Upload Job

| HTTP Status | Detail |
|-------------|--------|
| 404 | Deployment not found |
| 404 | Job not found |
| 404 | Task not found |
| 400 | Multipart upload not initialized |
| 400 | All files skipped: no valid files to upload |

---

## 7. Recorder

| HTTP Status | Detail |
|-------------|--------|
| 404 | Recorder not found |
| 400 | Identifier reserved by deleted recorder. Hard delete to release. |
| 400 | Active recorder with this brand/model/sn already exists. Cannot restore. |

---

## 8. User

| HTTP Status | Detail |
|-------------|--------|
| 404 | User not found |
| 400 | UserInfo with the same email already exists. |
| 400 | Active user with this email already exists. Cannot restore. |
| 400 | Password must be at least 8 characters |

---

## 9. Password Reset

| HTTP Status | Detail |
|-------------|--------|
| 400 | This account has been deactivated |
| 400 | Invalid or expired reset token |
| 400 | Reset token has expired. Please request a new one. |
| 400 | Password must be at least 8 characters |

---

## 10. OAuth (Google)

| HTTP Status | Detail |
|-------------|--------|
| 500 | Google OAuth is not configured |
| 401 | Failed to exchange authorization code |
| 401 | Failed to fetch user info from Google |
| 401 | No access token in response |
| 401 | Invalid user info from Google |
| 400 | Account already linked to Google |
| 400 | This Google account is already linked to another user |
| 400 | Account is not linked to Google |
| 400 | Please set a password before unlinking Google account |
| 403 | This account has been deactivated |
| 403 | This account has been deactivated. Please contact support. |

---

## 統計

| 類型 | 數量 | 說明 |
|-----|------|------|
| 404 Not Found | 20 | 資源不存在 |
| 400 Bad Request | 27 | 驗證失敗、重複、衝突 |
| 401 Unauthorized | 9 | 認證失敗 |
| 403 Forbidden | 6 | 權限不足 |
| 500 Server Error | 1 | 伺服器設定錯誤 |
