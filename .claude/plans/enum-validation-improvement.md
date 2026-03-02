# Feature: Enum 輸入驗證改進

> **狀態：已完成**
>
> - deployment.py、recorder.py、user.py Schema 全部改用 Enum 型別
> - Response Schema 均有 `@field_serializer` 序列化為 string
> - 驗證通過

## 目標
確保 API 輸入自動驗證符合 Enum 規範，拒絕無效值。

## 現況問題

目前 Schema 使用 `str` 型別搭配 Enum 預設值，**不驗證輸入**:

```python
# 現況: 允許任何 string
status: Optional[str] = DeploymentStatus.UNDEPLOYED.value

# 問題: 傳入 "invalid-status" 不會報錯
```

## 解決方案

將 `str` 改為直接使用 **Enum 型別**，Pydantic 自動驗證:

```python
# 改進後: 自動驗證
status: Optional[DeploymentStatus] = DeploymentStatus.UNDEPLOYED
```

輸入無效值會得到:
```json
{
  "detail": [{
    "type": "enum",
    "msg": "Input should be 'un-deployed', 'under-monitoring', 'success', 'water-intrusion' or 'lost'"
  }]
}
```

---

## 修改清單

### app/enums/enums.py (現有 Enum)
| Enum | 用途 | 允許值 |
|------|------|--------|
| `UserRole` | 使用者角色 | admin, user, guest |
| `DeploymentStatus` | 部署狀態 | un-deployed, under-monitoring, success, water-intrusion, lost |
| `RecorderStatus` | 錄音器狀態 | in-service, out-of-service, under-repair, ... |

### app/schemas/ 需修改的檔案

| 檔案 | Schema | 欄位 | 現況 | 改為 |
|------|--------|------|------|------|
| `deployment.py` | `DeploymentBase` | `status` | `Optional[str]` | `Optional[DeploymentStatus]` |
| `deployment.py` | `DeploymentUpdate` | `status` | `Optional[str]` | `Optional[DeploymentStatus]` |
| `recorder.py` | `RecorderBase` | `status` | `Optional[str]` | `Optional[RecorderStatus]` |
| `recorder.py` | `RecorderUpdate` | `status` | `Optional[str]` | `Optional[RecorderStatus]` |
| `user.py` | 相關 Schema | `role` | 檢查是否需要 | `Optional[UserRole]` |

---

## 實作步驟

### Step 1: 修改 deployment.py
```python
from app.enums.enums import DeploymentStatus

class DeploymentBase(BaseModel):
    # ... 其他欄位 ...
    status: Optional[DeploymentStatus] = DeploymentStatus.UNDEPLOYED

class DeploymentUpdate(BaseModel):
    # ... 其他欄位 ...
    status: Optional[DeploymentStatus] = None
```

### Step 2: 修改 recorder.py
```python
from app.enums.enums import RecorderStatus

class RecorderBase(BaseModel):
    # ... 其他欄位 ...
    status: Optional[RecorderStatus] = RecorderStatus.IN_SERVICE

class RecorderUpdate(BaseModel):
    # ... 其他欄位 ...
    status: Optional[RecorderStatus] = None
```

### Step 3: 檢查 user.py
確認 role 欄位是否需要加入 UserRole 驗證。

### Step 4: Response Schema 處理
Response Schema 可能需要 `field_serializer` 將 Enum 轉為 string:

```python
@field_serializer("status")
def serialize_status(self, v: Optional[DeploymentStatus], _info):
    return v.value if v else None
```

或使用 `model_config`:
```python
model_config = ConfigDict(from_attributes=True, use_enum_values=True)
```

### Step 5: 測試
- 測試有效 Enum 值輸入
- 測試無效值輸入 (預期 422 錯誤)
- 測試 None 值 (Optional 情況)

---

## 注意事項

### 向後相容性
- API 回應格式不變 (仍回傳 string)
- 僅影響**輸入驗證**，拒絕無效值

### 資料庫影響
- Model 層不變 (仍存 string)
- 只在 Schema 層驗證

---

## 驗證方式

1. **單元測試**: 測試各 Schema 的 Enum 驗證
2. **API 測試**: 使用 curl 測試無效輸入
3. **Ruff 檢查**: `ruff check && ruff format`

---

## 實作檢查清單

- [x] deployment.py Schema 修改
- [x] recorder.py Schema 修改
- [x] user.py Schema 檢查
- [x] Response 序列化處理
- [x] 單元測試
- [x] Ruff 檢查通過
