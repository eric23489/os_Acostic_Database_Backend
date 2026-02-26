# Todo 待辦清單

## 已完成

### 批量音檔上傳 (`feature/batch-upload-audio`) - Phase 6
- [x] 路徑 A：UploadJob 分段上傳（POST `/audio-upload-jobs/` + 9 個 multipart 端點）
- [x] 路徑 B：AudioBatch metadata 建立（POST `/audio/batch`）
- [x] 冪等設計：active/deleted object_key 衝突處理、207 部分成功
- [x] 斷點續傳：GET progress 端點回傳 completed_parts / remaining_parts
- [x] IDOR 防護：所有 job/task 操作驗證 user_id
- [x] MinIO/DB 一致性：分離 502/500 錯誤處理
- [x] PR review 修復（C1-C9 critical issues）
- [x] 前端整合指南文件

---

## Phase 1 待辦

### 批量下載
- [ ] 批量下載音檔端點

### 健康檢查
- [ ] `GET /health` 端點（DB、MinIO 連線狀態）

### 即時資料更新 - SSE
- [ ] 建立 `GET /api/v1/events/stream` SSE 端點
- [ ] 資料變更時推送 event（含 resource、action、id、changed_by）
- [ ] 前端即時刷新受影響的查詢快取
- [ ] 依使用者權限過濾推送內容

### 輸入資料驗證
- [ ] 全面審查並補強各端點的輸入驗證規則

### 佈放次數欄位
- [ ] Point 回應新增 `deployment_count` 計算欄位

### 儀器（Recorder）功能擴充
- [ ] 增加釋放儀的儀器類型
- [ ] 所有儀器可上傳照片
- [ ] 新增 `is_deploying` 欄位（顯示儀器當前佈放狀態）
- [ ] 回傳儀器統計狀態

### 增加佈放和回收人員
- [ ] Deployment 新增佈放人員與回收人員欄位

### API Logger
- [ ] 建立 error detail list（`.claude/docs/error-list.md`）
