# Backend FastAPI Development
Use this skill when working on the Python backend (API, DB interactions, MinIO storage).

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

1. Ensure `.env` exists (refer to `README.md` for template).
2. Start stack: `docker-compose up --build -d`

**Common endpoints:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**容器與 Port:**
| Service | Container Name | Port |
|---------|---------------|------|
| fastapi-app | os-acoustic-backend | ${APP_PORT_OUT}:${APP_PORT} |
| db | os-acoustic-postgres | ${POSTGRES_PORT_OUT}:${POSTGRES_PORT} |

預設值請參考 `.env` (通常 APP_PORT_OUT=8000)

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
- If backend doesn't start, check if Database (PostGIS) is ready.
- Check logs:
  - Backend: `docker-compose logs -f fastapi-app` 或 `docker logs -f os-acoustic-backend`
  - Database: `docker-compose logs -f db` 或 `docker logs -f os-acoustic-postgres`
- If Alembic fails:
    - Check `alembic current`
    - Ensure `geoalchemy2` is imported in migration scripts if using geometry types.
    - Check `env.py` for table exclusions (e.g., `spatial_ref_sys`).

## MinIO (Object Storage)
MinIO 為獨立服務，不在 Docker Compose 內。

**連線:** `http://{MINIO_IP_ADDRESS}:{MINIO_PORT}` (預設 192.168.1.21:9000)

**路徑結構:**
- Bucket = Project `name` 欄位
- 物件: `{point_name}/{YYYY}/{MM}/Raw_Data/{filename}`
- 預簽名 URL 有效期: 1 小時

**開發注意:**
- 建立 Project 時自動建立 Bucket
- 測試使用 mock S3 client

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

## Environment Variables

| 變數 | 說明 |
|------|------|
| POSTGRES_USER/PASSWORD/DB | DB 認證 |
| POSTGRES_IP_ADDRESS/PORT | DB 連線 |
| SECRET_KEY | JWT 密鑰 |
| APP_PORT / APP_PORT_OUT | App Port |
| MINIO_IP_ADDRESS/PORT | MinIO 連線 |
| AWS_ACCESS_KEY_ID/SECRET | MinIO 認證 |

## Related docs
- Project Context: `claude.md`
- Project Readme: `README.md`
- Database Config: `alembic.ini`
