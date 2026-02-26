# Changelog 開發歷程

## 已完成功能

### Phase 1: 基礎建設 (2025-01)
- [x] 專案初始化
- [x] 資料庫連線設定
- [x] 使用者登入/註冊 API

### Phase 2: 核心功能 (2025-01)
- [x] Project/Point/Deployment/Audio CRUD API
- [x] MinIO 整合至 Docker Compose

### Phase 3: 刪除功能 (2025-02)
- [x] 軟刪除功能 (Soft Delete)
- [x] Recorder 刪除/還原端點
- [x] Hard Delete 功能 (Project/Point/Deployment/Audio)
- [x] Hard Delete 測試 (17 個案例)

### Phase 4: 認證增強 (2026-02)
- [x] Google OAuth 登入/註冊
- [x] OAuth 帳號設定密碼
- [x] 綁定/解除綁定 Google
- [x] 忘記密碼/重設密碼
- [x] OAuth 測試 (28 個案例)

### Phase 5: 測試覆蓋率提升 (2026-02)
- [x] UserService 單元測試 (19 個案例)
- [x] Auth 單元測試 (10 個案例)
- [x] PasswordResetService 單元測試 (13 個案例)
- [x] OAuthService 單元測試 (17 個案例)
- [x] 覆蓋率提升 75% → 85%

### Phase 6: 批量音檔上傳 (2026-02)
- [x] 路徑 A：UploadJob 含分段上傳 (9 個端點)
  - POST `/api/v1/audio-upload-jobs/`（建立任務，預建 AudioInfo status=PENDING）
  - POST `/{job_id}/tasks/{task_id}/multipart/init`（初始化 Multipart Upload）
  - POST `/{job_id}/tasks/{task_id}/multipart/urls`（取得 Part presigned URLs）
  - POST `/{job_id}/tasks/{task_id}/multipart/part-complete`（回報 Part 完成 + ETag）
  - POST `/{job_id}/tasks/{task_id}/multipart/complete`（完成整個檔案上傳）
  - GET `/{job_id}`（查詢任務進度）
  - GET `/{job_id}/tasks/{task_id}/progress`（斷點續傳查詢）
  - POST `/{job_id}/cancel`（取消任務，abort MinIO + 軟刪除 AudioInfo）
- [x] 路徑 B：AudioBatch metadata 建立（POST `/api/v1/audio/batch`）
  - 1–100 筆批量建立，前端提供 object_key
  - 冪等：active/deleted 碰撞 → skipped（207），含既有 audio_id
  - 批次內重複 object_key → 第一筆通過，後續 skipped
  - 並行競爭 IntegrityError → 409 Conflict
- [x] AudioBatchResultItem model_validator 強制跨欄位不變量
- [x] IDOR 防護：所有 job/task 操作過濾 user_id（回傳 404）
- [x] MinIO/DB 一致性：complete_multipart MinIO 失敗 502，DB commit 失敗 500
- [x] WAV header 自動解析（fs, channels, duration, header_warning）
- [x] PR review 修復 C1-C9（佔位端點、IDOR、一致性、TOCTOU、不變量等）
- [x] 前端整合指南（object_key 格式、時序圖、錯誤代碼速查）
