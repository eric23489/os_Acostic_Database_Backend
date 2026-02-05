# Project Context: 洋聲聲學資料庫與後端

## 1. 專案概述 (Project Overview)
- **簡介**: 本系統基於 Python FastAPI 與 Docker 技術堆疊，專為處理高通量水下錄音數據設計。後端採用 PostgreSQL 結合 PostGIS 處理佈放資訊，並以 MinIO 建構可擴充的音檔儲存層。
- **主要功能**:
  - 高通量水下錄音數據處理與管理
  - 地理空間資訊儲存與查詢 (PostGIS)
  - 可擴充音檔物件儲存 (MinIO)
- **目標受眾**: 海洋聲學研究人員、數據分析師

## 2. 技術堆疊 (Tech Stack)
- **前端 (Frontend)**:
  - (本專案為後端 API 服務)
- **後端 (Backend)**:
  - Language: Python 3.14
  - Framework: FastAPI, Uvicorn
  - Database: PostgreSQL, PostGIS
  - Migration: Alembic
  - Storage: MinIO
- **基礎設施 (Infrastructure)**:
  - Containerization: Docker, Docker Compose
  - Object Storage: MinIO (containerized)

## 3. 專案結構 (Project Structure)
主要目錄結構說明：
- `/app`: 應用程式原始碼
  - `main.py`: 應用程式進入點 (Entry Point)
  - `/api`: API 路由定義 (Routes)
  - `/core`: 核心設定 (Config, Security)
  - `/models`: 資料庫模型 (SQLAlchemy/GeoAlchemy2 Models)
  - `/schemas`: Pydantic 資料驗證模型
  - `/services`: 業務邏輯層
  - `/db`: 資料庫連線與 Session 管理
- `/alembic`: 資料庫遷移腳本 (Migrations)
- `/tests`: 測試檔案
- `docker-compose.yml`: Docker 編排設定
- `requirements.txt`: Python 相依套件清單

## 4. 程式碼規範 (Coding Guidelines)
**AI 在生成程式碼時請嚴格遵守以下規則：**

### 一般原則 (General)
- **語言**: Python 3.14
- **風格**: 遵循 **PEP 8**，並強制通過 **Ruff** 檢查。
- **工具**: 使用 `ruff` 進行 Linting 與 Formatting，`pre-commit` 進行提交前檢查。

### 命名慣例 (Naming)
- **變數/函式**: `snake_case` (例如: `fetch_user_data`)。
- **類別**: `PascalCase` (例如: `UserProfile`)。
- **私有屬性**: `_snake_case` (例如: `_internal_cache`)。
- **函式命名**: 需反映行為
  - 動作: `create_`, `calculate_`, `send_` (例如: `create_user`)
  - 取得: `get_` (例如: `get_user_by_id`)
  - 布林: `is_`, `has_` (例如: `is_admin`)
  - 屬性 (@property): 名詞 (例如: `user.full_name`)

### 函式設計 (Function Design)
- **型別提示 (Type Hints)**: 所有參數與回傳值**必須**標註型別。
- **參數 (Arguments)**:
  - **禁止**使用可變物件 (`list`, `dict`) 作為預設參數，請使用 `None` 並在內部檢查。
  - 參數過多 (3-4+) 時：
    - **跨系統邊界** (API Body, Config): 使用 **Pydantic**。
    - **內部資料傳遞**: 使用 **dataclass**。
- **單一職責 (SRP)**: 一個函式只做一件事。
- **回傳**: 成功回傳單一型別，失敗使用 Exception 表達錯誤。
- **文件**: 必須撰寫 Docstrings 說明目的。

### 格式與引用 (Formatting & Imports)
- **Import 排序**: 標準庫 -> 第三方庫 -> 專案模組 (由 Ruff I 規則自動處理)。
- **別名**: `pandas as pd`, `numpy as np`, `scipy as sp`, `scipy.signal as ss`。
- **TODO**: `# TODO (Name): 說明`。

## 5. 常用指令 (Common Commands)
- 啟動開發環境: `docker-compose up -d`
- 執行 Migration: `alembic upgrade head`
- 建立新 Migration: `alembic revision --autogenerate -m "description"`
- 執行測試: `pytest`
- 本地啟動伺服器: `uvicorn app.main:app --reload`

## 6. 環境變數 (Environment Variables)
*(僅列出需要的 Key，不要包含真實數值，參考 `.env.example`)*
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `POSTGRES_IP_ADDRESS`, `POSTGRES_PORT`, `POSTGRES_PORT_OUT`
- `SECRET_KEY` (JWT)
- `APP_PORT`, `APP_PORT_OUT`
- `MINIO_IP_ADDRESS`, `MINIO_PORT`, `MINIO_PORT_OUT`, `MINIO_CONSOLE_PORT`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## 7. 目前開發狀態與待辦事項 (Current Status & TODOs)
- [x] 專案初始化
- [x] 資料庫連線設定
- [x] 使用者登入/註冊 API
- [x] Project/Point/Deployment/Audio CRUD API
- [x] 軟刪除功能 (Soft Delete)
- [x] Recorder 刪除/還原端點
- [x] MinIO 整合至 Docker Compose

## 8. 設計模式 (Design Patterns)

### 軟刪除 (Soft Delete)
所有主要 Model 使用軟刪除模式：
- `is_deleted`: Boolean，標記是否已刪除
- `deleted_at`: DateTime，刪除時間
- `deleted_by`: Integer，執行刪除的使用者 ID

使用 PostgreSQL 部分唯一索引確保活躍記錄的唯一性：
```python
Index("uq_xxx_active", "field", unique=True, postgresql_where=(is_deleted.is_(False)))
```

級聯刪除順序：Project → Points → Deployments → Audios

### Hard Delete 模式
永久刪除資源及相關 MinIO 物件：
- API: `DELETE /api/v1/{resources}/{id}/permanent` (需 Admin)
- 刪除順序：MinIO 物件 → MinIO Bucket → DB 記錄 (先子後父)
- 軟刪除名稱保留，直到 Hard Delete 釋放
- 詳細範本參考：`.claude/docs/delete-patterns.md`

### 多角色討論模式
手動觸發不同角色的 Task Agent 進行深度討論：
- 🎯 **提問者**: 使用者視角、邊界情況、失敗情境
- 🏗️ **架構師**: 一致性、可靠性、方案比較
- 💻 **後端工程師**: 程式碼結構、錯誤處理、測試

## 9. Claude回覆語言
- 中文
