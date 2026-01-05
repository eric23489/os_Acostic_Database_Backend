# OS_Acoustic_Database_Backend CI 說明

## 專案簡介 (Introduction)

此文件說明 `.github/workflows/ci.yml` 的行為：在指定分支自動安裝相依、生成 `.env` 並執行 `pytest`，確保每次提交都有基本測試。

## CI 內容摘要 (Features)

- 觸發條件：push 或 PR 至 `eric23489/feature/auth-token-flows`。
- 環境：GitHub Actions `ubuntu-latest`，Python 3.11，pip 快取。
- 步驟：
  1. checkout 原始碼。
  2. 依 Secrets/Variables 寫入 `.env`。
  3. 安裝 `requirements.txt`。
  4. 執行 `pytest`（`PYTHONPATH` 指向工作目錄）。

## 使用方式 (Usage)

- 想要其他分支也跑 CI：編輯 `.github/workflows/ci.yml` 的 `on:` 區段，加入分支名稱。
- 本地驗證：建立 `.env` 後執行 `pip install -r requirements.txt`，再跑 `pytest`，避免 CI 才發現問題。
- 觀察結果：在 GitHub 的 Actions 分頁可查看每次工作流的執行情況與日誌。

## 必要設定 (Secrets / Variables)

在 GitHub Repo 的 Settings > Secrets and variables 設定：
- Secrets：`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SECRET_KEY`
- Variables：`POSTGRES_IP_ADDRESS`, `POSTGRES_PORT`, `POSTGRES_PORT_OUT`, `APP_PORT`, `APP_PORT_OUT`, `MINIO_IP_ADDRESS`, `MINIO_PORT`, `MINIO_BUCKET_NAME`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`

本地 `.env` 範例：
```env
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_db
POSTGRES_IP_ADDRESS=localhost
POSTGRES_PORT=5431
POSTGRES_PORT_OUT=5431
APP_PORT=80
APP_PORT_OUT=8000
MINIO_IP_ADDRESS=localhost
MINIO_PORT=9000
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
MINIO_BUCKET_NAME=data
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
