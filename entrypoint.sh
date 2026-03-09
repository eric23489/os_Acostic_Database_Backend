#!/bin/sh

# 1. 先執行資料庫遷移
echo "Running Database Migrations..."
alembic upgrade head

# 2. 啟動 FastAPI 服務
echo "Starting Server..."
# 注意：正式環境通常不用 --reload
exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} 