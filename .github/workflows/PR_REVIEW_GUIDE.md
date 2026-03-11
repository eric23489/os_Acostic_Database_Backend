# PR 自動審查流程 (PR Auto Review Process)

## 概述 (Overview)

當您建立或更新 Pull Request 時，系統會自動執行三個 GitHub Actions 工作流程來審查您的變更。

## 工作流程圖 (Workflow Diagram)

```
PR 建立或更新
    │
    ├─→ PR Labeler (pr-labeler.yml)
    │   ├─ 分析變更的檔案
    │   ├─ 計算變更大小
    │   └─ 自動加上標籤
    │
    └─→ PR Auto Review (pr-review.yml)
        │
        ├─→ Job 1: Code Quality Check
        │   ├─ ruff check：Linting 檢查
        │   └─ ruff format --check：格式化檢查
        │
        ├─→ Job 2: Run Tests
        │   ├─ 執行 pytest
        │   ├─ 產生覆蓋率報告
        │   └─ 上傳至 codecov
        │
        ├─→ Job 3: Security Check
        │   └─ 使用 safety 檢查套件安全性
        │
        └─→ Job 4: Review Summary
            └─ 在 PR 發布審查摘要評論
```

## 審查項目詳細說明

### 1. 程式碼品質檢查 (Code Quality)

#### ruff check - Linting 檢查
- **目的**：檢查語法錯誤、未定義名稱、import 排序等問題
- **檢查範圍**：`app/` 和 `tests/` 目錄
- **修正方法**：執行 `ruff check --fix app/ tests/`

#### ruff format --check - 格式化檢查
- **目的**：確保程式碼符合統一格式規範（取代 Black）
- **檢查範圍**：`app/` 和 `tests/` 目錄
- **修正方法**：執行 `ruff format app/ tests/`

### 2. 測試執行 (Testing)

- **測試框架**：pytest
- **覆蓋率工具**：pytest-cov
- **報告格式**：XML 與終端輸出
- **覆蓋率目標**：檢查 `app/` 目錄的測試覆蓋率
- **整合**：自動上傳至 Codecov（如有設定）

### 3. 安全檢查 (Security)

- **工具**：safety
- **檢查內容**：掃描 `requirements.txt` 中的套件是否有已知的安全漏洞
- **資料來源**：Python Advisory Database
- **處理方式**：發現漏洞時會產生警告

### 4. 自動標籤 (Auto Labeling)

#### 類別標籤 (Category Labels)
- `api` - API 相關變更（`app/api/` 目錄）
- `database` - 資料庫相關變更（`alembic/`、`app/models/`、`app/db/` 目錄）
- `configuration` - 設定檔變更（Docker、YAML 檔案，但不包含工作流程）
- `ci-cd` - CI/CD 工作流程變更（`.github/workflows/` 目錄）
- `documentation` - 文件變更（README、Markdown 檔案）
- `tests` - 測試相關變更（`tests/` 目錄）
- `dependencies` - 相依套件變更（`requirements.txt`、`Dockerfile`）

#### 大小標籤 (Size Labels)
- `size/XS` - 極小變更（< 10 行）
- `size/S` - 小變更（10-49 行）
- `size/M` - 中等變更（50-199 行）
- `size/L` - 大變更（200-499 行）
- `size/XL` - 超大變更（≥ 500 行）

## 審查結果 (Review Results)

審查完成後，系統會在 PR 中自動發布一則評論，包含：

```
## Automated PR Review Summary

**Status:** passed

### Results:
- [PASS] **Code Quality Check**: success
- [PASS] **Run Tests**: success
- [PASS] **Security Check**: success

### Details:
- Total checks: 3
- Passed: 3
- Failed: 0
- Skipped: 0

All checks passed!

---
*This is an automated review. For detailed logs, check the Actions tab.*
```

## 如何回應審查結果

### 如果所有檢查都通過
- 您的 PR 已經符合標準，可以請求人工審查

### 如果程式碼品質檢查失敗
```bash
# 本地修正
ruff check --fix app/ tests/
ruff format app/ tests/

# 提交修正
git add .
git commit -m "Fix code quality issues"
git push
```

### 如果測試失敗
```bash
# 本地執行測試
pytest -v

# 查看失敗的測試
pytest --lf

# 修正問題後重新測試
pytest
```

### 如果安全檢查失敗
```bash
# 查看詳細的安全報告
pip install safety
safety check

# 根據報告更新有問題的套件
pip install --upgrade <package-name>
pip freeze > requirements.txt
```

## Pre-push 本地檢查設定

首次設定（僅需執行一次）：
```bash
pre-commit install --hook-type pre-push
```

設定後，每次 `git push` 前會自動執行：
- pytest（排除 integration 測試）
- safety 安全性掃描

如需跳過（緊急情況）：
```bash
git push --no-verify
```

手動觸發 pre-push 階段的所有 hook：
```bash
pre-commit run --hook-stage pre-push --all-files
```

## 最佳實踐 (Best Practices)

1. **提交前本地檢查**：在提交 PR 前，先在本地執行上述檢查命令
2. **小批次提交**：將大型變更拆分為較小的 PR，更容易審查
3. **遵循標籤**：注意系統自動加上的標籤，確認 PR 的分類正確
4. **及時修正**：看到審查失敗時，儘快修正並重新推送
5. **查看詳細日誌**：如果不確定失敗原因，到 Actions 分頁查看完整日誌

## 疑難排解 (Troubleshooting)

### 問題：工作流程沒有執行
- 檢查 PR 的目標分支是否為 `main`、`develop` 或 `feature/**`
- 確認 `.github/workflows/` 目錄中的 YAML 檔案格式正確

### 問題：測試一直失敗
- 檢查是否正確設定了 GitHub Secrets（`DB_USER`、`DB_PASSWORD` 等）
- 查看 Actions 日誌中的錯誤訊息

### 問題：安全檢查報告誤報
- 如果確認是誤報，可以在 PR 評論中說明
- 考慮建立 `.safety-policy.yml` 來忽略特定警告

## 相關連結 (Related Links)

- [GitHub Actions 文件](https://docs.github.com/en/actions)
- [Ruff 文件](https://docs.astral.sh/ruff/)
- [pytest 文件](https://docs.pytest.org/)
- [safety 文件](https://pyup.io/safety/)
