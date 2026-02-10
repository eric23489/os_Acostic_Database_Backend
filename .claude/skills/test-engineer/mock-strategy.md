---
name: mock-strategy
description: 設計 Mock 策略，確定哪些依賴需要 Mock 及如何 Mock。
---

設計「$ARGUMENTS」的 Mock 策略：

**需要 Mock 的依賴:**

| 依賴 | Mock 方式 | 理由 |
|------|-----------|------|
| DB Session | MagicMock | 隔離測試 |
| MinIO Client | MagicMock | 避免真實操作 |
| get_current_user | dependency_overrides | 控制用戶 |

**Mock 範例:**

```python
from unittest.mock import MagicMock, patch

# Mock DB
mock_db = MagicMock()
mock_db.query.return_value.filter.return_value.first.return_value = mock_obj

# Mock MinIO
with patch("app.services.xxx.get_s3_client") as mock_s3:
    mock_s3.return_value = MagicMock()
    mock_s3.return_value.delete_object.return_value = None

# Mock 當前用戶
from app.core.auth import get_current_user
app.dependency_overrides[get_current_user] = lambda: mock_user
```

**Mock 粒度:**
- 函式層級: `patch("module.function")`
- 類別層級: `patch.object(Class, "method")`
- 回傳值: `return_value`
- 例外: `side_effect = Exception("error")`

**不需要 Mock:**
- 純函式邏輯
- Pydantic 驗證
- 簡單計算
