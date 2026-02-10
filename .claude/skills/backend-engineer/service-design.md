---
name: service-design
description: 設計 Service 層方法，包含業務邏輯和資料庫操作。
---

設計「$ARGUMENTS」的 Service 方法：

**方法簽名:**
```python
def method_name(
    self,
    param1: Type,
    param2: Type,
) -> ReturnType:
    """
    方法說明。

    Args:
        param1: 參數說明
        param2: 參數說明

    Returns:
        回傳值說明

    Raises:
        HTTPException: 錯誤情境
    """
```

**業務邏輯流程:**
1. 驗證輸入
2. 查詢資料
3. 執行操作
4. 回傳結果

**資料庫操作:**
```python
# 查詢範例
self.db.query(Model).filter(
    Model.field == value,
    Model.is_deleted.is_(False),
).first()
```

**錯誤處理:**
| 情境 | 狀態碼 | 訊息 |
|------|--------|------|
| | | |

**事務管理:**
- 需要 commit？
- 需要 rollback？
- 多步驟操作處理？
