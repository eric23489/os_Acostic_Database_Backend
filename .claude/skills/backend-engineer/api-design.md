---
name: api-design
description: 設計 RESTful API 端點，包含路由、參數和回應格式。
---

設計「$ARGUMENTS」的 API：

**端點設計:**
```
METHOD /api/v1/{resource}/{id}/{action}
```

**路徑參數:**
| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| | | | |

**Query 參數:**
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| | | | |

**Request Body:**
```python
class RequestSchema(BaseModel):
    field: type = Field(..., description="")
```

**Response:**
```python
class ResponseSchema(BaseModel):
    field: type
```

**HTTP 狀態碼:**
| 狀態碼 | 情境 |
|--------|------|
| 200 | 成功 |
| 400 | 請求錯誤 |
| 401 | 未授權 |
| 403 | 禁止存取 |
| 404 | 資源不存在 |

**權限需求:**
- 需要登入？
- 需要 Admin？
- 資源所有權檢查？
