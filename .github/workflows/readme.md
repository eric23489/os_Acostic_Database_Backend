# OS_Acoustic_Database_Backend CI/CD 與自動審查說明

## 專案簡介 (Introduction)

此文件說明 GitHub Actions 工作流程，包括 CI 測試、自動 PR 審查與標籤功能。

### 可用的工作流程 (Available Workflows)

1. **CI 測試** (`test connection config of db.yml`)：在指定分支自動安裝相依、生成 `.env` 並執行 `pytest`，確保每次提交都有基本測試。
   > 註：此檔名包含空格，建議未來重新命名為 `test-connection-config-of-db.yml` 以符合標準命名慣例。
2. **PR 自動審查** (`pr-review.yml`)：當建立或更新 PR 時，自動執行程式碼品質檢查、測試與安全檢查，並發布審查摘要評論。
3. **PR 自動標籤** (`pr-labeler.yml`)：根據 PR 變更的檔案類型與大小，自動加上適當的標籤。

## CI 內容摘要 (Features)

### 1. CI 測試 (CI Tests)
- 觸發條件：push 或 PR 至 `eric23489/feature/auth-token-flows` 或 `main`。
- 環境：GitHub Actions `ubuntu-latest`，Python 3.11，pip 快取。
- 步驟：
  1. checkout 原始碼。
  2. 依 Secrets/Variables 寫入 `.env`。
  3. 安裝 `requirements.txt`。
  4. 執行 `pytest`（`PYTHONPATH` 指向工作目錄）。

### 2. PR 自動審查 (PR Auto Review)
- 觸發條件：當 PR 開啟、同步或重新開啟時（針對 `main`、`develop` 與 `feature/**` 分支）。
- 功能：
  - **程式碼品質檢查**：使用 Black、isort、flake8 檢查程式碼格式與風格。
  - **測試執行**：執行完整的測試套件並產生覆蓋率報告。
  - **安全檢查**：使用 safety 檢查相依套件是否有已知的安全漏洞。
  - **審查摘要**：在 PR 中自動發布包含所有檢查結果的評論。

### 3. PR 自動標籤 (PR Auto Labeler)
- 觸發條件：當 PR 開啟或同步時。
- 功能：
  - 根據變更的檔案自動加上分類標籤（如 `api`、`database`、`documentation` 等）。
  - 根據變更大小加上尺寸標籤（`size/XS` 到 `size/XL`）。

## 使用方式 (Usage)

### CI 測試
- 想要其他分支也跑 CI：編輯 `.github/workflows/test connection config of db.yml` 的 `on:` 區段，加入分支名稱。
- 本地驗證：建立 `.env` 後執行 `pip install -r requirements.txt`，再跑 `pytest`，避免 CI 才發現問題。
- 觀察結果：在 GitHub 的 Actions 分頁可查看每次工作流的執行情況與日誌。

### PR 自動審查
- 自動觸發：當您建立或更新針對 `main`、`develop` 或 `feature/**` 分支的 PR 時，工作流會自動執行。
- 審查結果：檢查完成後，會在 PR 中自動發布包含所有檢查結果與狀態的評論。
- 本地預檢：
  ```bash
  # 程式碼格式檢查
  pip install black isort flake8
  black --check app/ tests/
  isort --check-only app/ tests/
  flake8 app/ tests/
  
  # 執行測試
  pytest --cov=app
  
  # 安全檢查
  pip install safety
  safety check
  ```

### PR 自動標籤
- 自動觸發：當您建立或更新 PR 時，系統會根據變更的檔案自動加上標籤。
- 標籤類型：
  - 類別標籤：`api`、`database`、`configuration`、`documentation`、`tests`、`dependencies`
  - 大小標籤：`size/XS`（<10 行）、`size/S`（<50 行）、`size/M`（<200 行）、`size/L`（<500 行）、`size/XL`（≥500 行）

## 必要設定 (Secrets / Variables)

在 GitHub Repo 的 Settings > Secrets and variables 設定：

### CI 測試所需 (Required for CI Tests)
- Secrets：`DB_USER`（或 `POSTGRES_USER`）, `DB_PASSWORD`（或 `POSTGRES_PASSWORD`）, `POSTGRES_DB`, `SECRET_KEY`
- Variables：`POSTGRES_IP_ADDRESS`, `POSTGRES_PORT`, `POSTGRES_PORT_OUT`, `APP_PORT`, `APP_PORT_OUT`, `MINIO_IP_ADDRESS`, `MINIO_PORT`, `MINIO_BUCKET_NAME`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`

### PR 自動審查所需 (Required for PR Auto Review)
- Secrets：
  - `DB_USER`, `DB_PASSWORD`, `POSTGRES_DB`, `SECRET_KEY` - 用於測試環境
  - `CODECOV_TOKEN` (選用) - 如需上傳覆蓋率報告至 Codecov

> **注意**：PR 自動審查使用與 CI 測試相同的 secrets。如果 Codecov 上傳失敗，可以忽略（已設定 `continue-on-error: true`）。

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
