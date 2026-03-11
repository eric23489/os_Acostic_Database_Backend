# Todo 待辦清單

## 已完成

### 批量音檔上傳 (`feature/batch-upload-audio`) - Phase 6
- [x] 路徑 A：UploadJob 分段上傳（POST `/audio-upload-jobs/` + 9 個 multipart 端點）
- [x] 路徑 B：AudioBatch metadata 建立（POST `/audio/batch`）
- [x] 冪等設計：active/deleted object_key 衝突處理、207 部分成功
- [x] 斷點續傳：GET progress 端點回傳 completed_parts / remaining_parts
- [x] IDOR 防護：所有 job/task 操作驗證 user_id
- [x] MinIO/DB 一致性：分離 502/500 錯誤處理
- [x] SHA256 Checksum 驗證：MinIO `ChecksumAlgorithm="SHA256"`、per-part `checksum_sha256` 欄位
- [x] PR review 修復（C1-C9 critical issues）
- [x] 前端整合指南文件

### 自定義 Error Code - Phase 7
- [x] 建立 `app/core/exceptions.py`：`AppException` frozen dataclass + 41 個 error code 常數
- [x] 建立 `app/schemas/common.py`：`ErrorResponse` schema
- [x] 修改 `app/main.py`：註冊 AppException 與 422 統一 exception handler
- [x] 遷移所有 service 層（10 個檔案）到 AppException
- [x] 遷移 API 端點層（api_projects、api_audio、api_users、api_recorders）
- [x] 更新 17 個測試檔案（全部使用新的 error_code / message 欄位）
- [x] 更新 `error-list.md` 加入 error_code 欄位

### 健康檢查 - Phase 7
- [x] `GET /health` 端點（DB、MinIO 連線狀態）

### 輸入驗證與欄位擴充 - Phase 8
- [x] 全面審查並補強各端點的輸入驗證規則
- [x] Point 回應新增 `deployment_count` 計算欄位（`@computed_field` + `selectinload.load_only`）
- [x] Deployment 新增佈放人員與回收人員欄位
- [x] `record_duration` 型別由 float 改為 int（含 Alembic migration）
- [x] `fs` 欄位驗證下限放寬為 `ge=0`

---

## PR #17 Copilot Review 修正

> 來源：PR #17 收到 24 條 Copilot review comments，依嚴重性分 5 批執行。各批次獨立 commit。

### Batch 1：DB / Migration Bug（最高優先）`[輕量]` [x] 已完成
- [x] `alembic/versions/2026_03_05_*change_record_duration_to_integer.py:31` — ALTER COLUMN DOUBLE→INT 需加 `postgresql_using="record_duration::integer"`
- [x] `app/models/audio.py:59` — `server_default="'completed'"` 改 `server_default=text("'completed'")`
- [x] `alembic/versions/2026_02_12_add_upload_jobs.py` — 已確認 migration 中已使用 `sa.text("'completed'")`，無需修正
- [x] `app/tasks/audio_tasks.py:105` — `cleanup_abandoned_audio_records()` 刪 AudioInfo 前先刪 UploadTask，避免 FK 違規

### Batch 2：API 一致性（HTTP 回傳格式 / error_code 不統一）`[中等]` [x] 已完成
- [x] `app/api/v1/endpoints/api_deployments.py` — 已確認無 HTTPException，不需修改
- [x] `app/api/v1/endpoints/api_points.py` — 已確認無 HTTPException，不需修改
- [x] `app/core/auth.py:45` — 已確認使用 `PERMISSION_ADMIN_REQUIRED`，不需修改
- [x] `app/api/v1/endpoints/api_users.py:72,105,117,129` — 4 處 `PERMISSION_DENIED` 改 `PERMISSION_ADMIN_REQUIRED`
- [x] `app/services/recorder_service.py` — restore 的 `RECORDER_IDENTIFIER_COLLISION` 改 `RECORDER_IDENTIFIER_DUPLICATE`；`RECORDER_IDENTIFIER_COLLISION` 已從 exceptions.py 移除
- [x] `entrypoint.sh:5` — `alembic upgrade heads` 改 `alembic upgrade head`
- [x] `docs/error-list.md` — 移除 `RECORDER_IDENTIFIER_COLLISION`，更新統計（45→44）

### Batch 3：Exception 架構（module-level instance 跨請求 traceback 污染）`[複雜]` [x] 已完成
- [x] `app/core/exceptions.py` — 44 個常數全轉為 class，raise 語法無需更動
- [x] `tests/test_password_reset.py` — `is` 比較改 `isinstance`
- [x] `tests/test_recorders.py`, `test_soft_delete.py` — COLLISION → DUPLICATE（Batch 2 遺漏）
- [x] `docs/error-list.md` — 測試 SOP 更新
- [x] `pyproject.toml` — tests/ per-file-ignores（N806 MockService、E501）
- [x] `scripts/check_error_list_sync.py` — regex 支援 `super().__init__()` 寫法

### Batch 4：測試與小修`[輕量]` [x] 已完成
- [x] `tests/test_recorders.py:7` — 已在 Batch 3 移除
- [x] `tests/integration/conftest.py:22` — 修正 comment（"separate DB" → "same DB as app"）
- [x] `tests/integration/conftest.py:45,46` — `.clear()` 改 `.pop(get_db, None)`
- [x] `app/core/celery_app.py:21` — `os.getenv` 改用 `settings.celery_broker_url/celery_result_backend`
- [x] `app/services/oauth_service.py:107` — 已使用 `OAUTH_USERINFO_FETCH_FAILED`，不需修改

### Batch 5：效能優化（可 defer）`[中等]` [x] 已完成
- [x] `app/utils/query.py:105` — `query.count()` 含 ORDER BY，改 `query.order_by(None).count()`
- [x] `app/services/point_service.py:82` — `selectinload(deployments)` 載入全欄位只為 count，改用 `.load_only(DeploymentInfo.id)` 只載 id 欄位
- [x] `app/api/v1/endpoints/api_health.py:45` — MinIO 健康檢查無 timeout，新增 `get_s3_health_client()`（connect/read timeout 3s）於 `app/core/minio.py`

---

## Phase 1 待辦

> 複雜度標註：`[輕量]` 半天以內、`[中等]` 1-2 天含 migration、`[複雜]` 3 天以上

### `[P1-1]` 批量下載 `[中等]`
- [ ] 批量下載音檔端點
- **備註**：保留，後續決定
- **先決條件**：確認「討論中」的批量下載方式（ZIP vs presigned URL）

### `[P1-3]` 儀器（Recorder）功能擴充 `[複雜]`（暫時保留）
- **Releaseinfo（釋放儀）**：
  - [ ] 草擬 Releaseinfo model
  - [ ] 新增 `is_deploying` 欄位（顯示儀器當前佈放狀態）
  - [ ] 上傳照片回傳統計狀態
- **Recorderinfo**：
  - [ ] 新增 `is_deploying` 欄位（顯示儀器當前佈放狀態）
  - [ ] 回傳儀器統計狀態
  - [ ] 新增量測值、標準值、校正日期欄位

### `[P1-4]` 即時資料更新 - SSE `[複雜]`
- [ ] 建立 `GET /api/v1/events/stream` SSE 端點
- [ ] 資料變更時推送 event（含 resource、action、id、changed_by）
- [ ] 前端即時刷新受影響的查詢快取
- [ ] 依使用者權限過濾推送內容
- **先決條件**：P1-1、P1-3 完成後，確保資料變更來源完整

---

## Phase 2 待辦

### 統計 API `[中等]`
- [ ] 各資源統計查詢端點

### 時間範圍查詢 `[中等]`
- [ ] 各端點支援時間範圍過濾參數

### 即時通知 `[複雜]`
- [ ] Email 通知
- [ ] Line 通知

### Lifecycle Rules `[中等]`
- [ ] MinIO 設定規則：自動刪除超過 7 天未完成的 Incomplete Multipart Uploads
- [ ] DB 上傳紀錄定期清理（30 / 60 / 90 天）
- [ ] DB 軟刪除記錄定期清理（Celery Beat task，清理超過 N 天的 is_deleted=True 記錄）

### 串流播放 `[複雜]`
- [ ] 音檔串流播放端點

### 分使用者等級權限 `[複雜]`
- [ ] 細分使用者角色與存取控制

### Refresh Token 機制 `[中等]`
- [ ] 登入回應新增 `refresh_token`
- [ ] `POST /users/refresh` 換發端點
- [ ] 前端 Axios interceptor 攔截 401 自動換發並重試原請求
- [ ] 確認 MinIO presigned URL 是否受 token 過期影響（待討論）

---

## 佈署

- [ ] Nginx 反向代理
- [ ] 網域設定
- [ ] 監測工具
  - [ ] Flower：監控 Celery 任務佇列、worker 狀態、重試次數
  - [ ] Prometheus / Grafana：監控 MinIO 流量、API 回應時間、DB Connection Pool 使用率
- [ ] 速率限制（slowapi）

---

## Phase 3 待辦

### Redis 快取 `[中等]`
- [ ] 減少重複查詢資料庫負載

### 資料庫索引 `[中等]`
- [ ] 加速常用查詢的索引設計

### 查詢優化 `[中等]`
- [ ] 審查並優化 N+1 及慢查詢

### 審計日誌 `[複雜]`
- [ ] 追蹤所有修改操作的審計日誌

### QR Code 建立 Deployment 草稿 `[複雜]`
- [ ] 佈放和回收人員掃描 QR code 自動建立 Deployment 草稿

### 冷儲存 `[複雜]`
- [ ] 過久資料移至冷儲存層

### MinIO Bucket 層級設定 `[中等]`
- [ ] 在 MinIO Bucket 層級設定存取策略

---

## 討論中

### 統計回傳內容
- [ ] 確認各統計 API 的回傳欄位與格式

### Refresh Token 與 MinIO presigned URL
- presigned URL 有效期限可能與 refresh token 換發時機衝突，需確認影響範圍與解法

### 批量下載方式
- [ ] 確認批量下載的實作方式（ZIP 打包 vs 逐一 presigned URL）
