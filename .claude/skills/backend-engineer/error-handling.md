---
name: error-handling
description: 設計錯誤處理機制，包含異常類型和錯誤訊息格式。
---

設計「$ARGUMENTS」的錯誤處理：

**可能的錯誤類型:**

| 錯誤情境 | HTTP 狀態碼 | 錯誤訊息 |
|----------|-------------|----------|
| 資源不存在 | 404 | "{Resource} not found" |
| 權限不足 | 403 | "Permission denied" |
| 驗證失敗 | 400 | "Invalid {field}" |
| 衝突 | 409 | "{Resource} already exists" |
| 伺服器錯誤 | 500 | "Internal server error" |

**錯誤回應格式:**
```python
{
    "detail": "錯誤訊息",
    "code": "ERROR_CODE",  # 可選
    "field": "欄位名"      # 可選
}
```

**異常處理模式:**
```python
try:
    # 操作
except SpecificException as e:
    logger.warning(f"Context: {e}")
    raise HTTPException(status_code=400, detail="User message")
except Exception as e:
    logger.error(f"Unexpected: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

**日誌記錄:**
- WARNING: 預期錯誤 (用戶錯誤)
- ERROR: 非預期錯誤 (系統錯誤)
- 不記錄敏感資訊
