# Backend FastAPI Development
Use this skill when working on the Python backend (API, DB interactions, MinIO storage).

## Quick Start
```bash
# 1. 複製環境變數範本
cp .env.example .env

# 2. 啟動所有服務
docker-compose up --build -d

# 3. 確認服務狀態
docker ps

# 4. 開始開發
# API Docs: http://localhost:8000/docs
# MinIO Console: http://localhost:9001
```

## When to use
- Editing FastAPI routes under `app/api/`
- Changing business logic under `app/services/`
- Updating SQLAlchemy/GeoAlchemy2 models under `app/models/`
- Running `ruff` / `pytest`, or diagnosing failing backend tests
- Debugging DB migrations (Alembic) or MinIO interactions

## Local dev (outside Docker)
**Prereqs:**
- Python 3.14 (Project standard)
- A running Postgres with PostGIS 17 (Recommend using Docker for DB: `docker-compose up -d db`)

**Workflow:**
- Create venv (repo root): `python -m venv .venv`
- Activate venv: `.\.venv\Scripts\Activate` (Windows) or `source .venv/bin/activate` (Linux/Mac)
- Install deps: `pip install -r requirements.txt`
- Apply migrations: `alembic upgrade head`
- Run the backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

**Health check:**
- Command: `curl http://localhost:8000/` (or check `/docs`)
- Note: Local `uvicorn` usually runs on 8000.

## Recommended dev workflow (Docker full stack)
This repo's default dev workflow is running the full compose stack.

1. Ensure `.env` exists (refer to `.env.example` for template).
2. Start stack: `docker-compose up --build -d`

**Common endpoints:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

**容器與 Port:**
| Service | Container Name | Port |
|---------|---------------|------|
| fastapi-app | os-acoustic-backend | ${APP_PORT_OUT}:${APP_PORT} |
| db | os-acoustic-postgres | ${POSTGRES_PORT_OUT}:${POSTGRES_PORT} |
| minio | os-acoustic-minio | ${MINIO_PORT_OUT}:9000 (API), ${MINIO_CONSOLE_PORT}:9001 (Console) |

預設值請參考 `.env` (通常 APP_PORT_OUT=8000, MINIO_PORT_OUT=9000)

## MinIO (Object Storage)
MinIO 已整合至 Docker Compose，作為本地開發的物件儲存服務。

**連線配置:**
- Docker 內部: `http://minio:9000` (使用服務名稱)
- 本機存取: `http://localhost:9000` (S3 API)
- Web Console: `http://localhost:9001`

**登入憑證:**
- 帳號/密碼取決於 `.env` 中的 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
- 預設開發環境建議: `minioadmin` / `minioadmin`

**環境變數:**
```env
MINIO_IP_ADDRESS=minio          # Docker 內部服務名稱
MINIO_PORT=9000
MINIO_PORT_OUT=9000             # 對外 S3 API Port
MINIO_CONSOLE_PORT=9001         # Web Console Port
AWS_ACCESS_KEY_ID=minioadmin    # MinIO 帳號
AWS_SECRET_ACCESS_KEY=minioadmin # MinIO 密碼
```

**路徑結構:**
- Bucket = Project `name` 欄位
- 物件: `{point_name}/{YYYY}/{MM}/Raw_Data/{filename}`
- 預簽名 URL 有效期: 1 小時

**開發注意:**
- 建立 Project 時自動建立 Bucket
- 測試使用 mock S3 client
- 資料持久化於 Docker volume `minio_data`

## Soft Delete 開發注意

**欄位:** `is_deleted`, `deleted_at`, `deleted_by`

**查詢過濾:**
```python
# 正確
.filter(Model.is_deleted.is_(False))
# 錯誤
.filter(Model.is_deleted == False)
```

**級聯刪除:** Project -> Points -> Deployments -> Audios
**還原:** 僅還原刪除時間相近 (±5秒) 的子記錄

## Code quality
**ALWAYS run before committing:**
- Format: `ruff format .`
- Lint: `ruff check . --fix`
- Tests: `pytest`

**Pre-commit:**
- Ensure hooks are installed: `pre-commit install`
- Run manually: `pre-commit run --all-files`

**Testing:**
- 測試目錄: `tests/`, 配置: `pytest.ini`
- Fixtures: `tests/conftest.py`
- 執行: `pytest` / `pytest -v` / `pytest tests/test_audio.py`
- 策略: 使用 mock，不連接真實資料庫

## Debugging checklist
- If backend doesn't start, check if Database (PostGIS) and MinIO are ready.
- Check logs:
  - Backend: `docker-compose logs -f fastapi-app` 或 `docker logs -f os-acoustic-backend`
  - Database: `docker-compose logs -f db` 或 `docker logs -f os-acoustic-postgres`
  - MinIO: `docker-compose logs -f minio` 或 `docker logs -f os-acoustic-minio`
- If Alembic fails:
    - Check `alembic current`
    - Ensure `geoalchemy2` is imported in migration scripts if using geometry types.
    - Check `env.py` for table exclusions (e.g., `spatial_ref_sys`).

## 常見錯誤排解

**MinIO 無法登入:**
- 確認 `.env` 中 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` 的值
- 重啟容器: `docker-compose down && docker-compose up -d`

**Presigned URL 失效或無法存取:**
- 確認 `MINIO_IP_ADDRESS=minio`（Docker 內部）而非外部 IP
- 檢查 Bucket 是否已建立

**資料庫連線失敗:**
- 確認 `POSTGRES_IP_ADDRESS=db`（Docker 內部服務名稱）
- 檢查 PostgreSQL 容器是否正常運行

## API 端點快速參考

| 功能 | Method | Endpoint |
|------|--------|----------|
| 建立 Project | POST | `/api/v1/projects/` |
| 取得 Project 列表 | GET | `/api/v1/projects/` |
| 上傳 Presigned URL | POST | `/api/v1/audio/upload/presigned-url` |
| 批量 Presigned URL | POST | `/api/v1/audio/upload/presigned-urls` |
| 軟刪除 | DELETE | `/api/v1/{resource}/{id}` |
| 還原 | POST | `/api/v1/{resource}/{id}/restore` |

完整 API 文件請參考: http://localhost:8000/docs

## Environment Variables

| 變數 | 說明 |
|------|------|
| POSTGRES_USER/PASSWORD/DB | DB 認證 |
| POSTGRES_IP_ADDRESS/PORT | DB 連線 |
| SECRET_KEY | JWT 密鑰 |
| APP_PORT / APP_PORT_OUT | App Port |
| MINIO_IP_ADDRESS | MinIO 連線 (Docker: `minio`) |
| MINIO_PORT / MINIO_PORT_OUT | MinIO S3 API Port |
| MINIO_CONSOLE_PORT | MinIO Web Console Port |
| AWS_ACCESS_KEY_ID/SECRET | MinIO 認證 |

## Related docs
- Project Context: `../../CLAUDE.md`
- Project Readme: `../../README.md`
- Database Config: `../../alembic.ini`
- Environment Template: `../../.env.example`
