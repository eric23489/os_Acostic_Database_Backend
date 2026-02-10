---
name: code-structure
description: 規劃程式碼結構，確定需要修改和新增的檔案。
---

規劃「$ARGUMENTS」的程式碼結構：

**需要修改的檔案:**

| 檔案 | 修改內容 |
|------|----------|
| `app/api/v1/endpoints/api_xxx.py` | 新增 API 端點 |
| `app/services/xxx_service.py` | 新增 Service 方法 |
| `app/schemas/xxx.py` | 新增 Schema (如需要) |
| `app/models/xxx.py` | 修改 Model (如需要) |

**新增的檔案:**
- (通常不需要新增，優先修改現有檔案)

**程式碼組織:**
```
app/
├── api/v1/endpoints/
│   └── api_xxx.py      # API 路由
├── services/
│   └── xxx_service.py  # 業務邏輯
├── schemas/
│   └── xxx.py          # Pydantic Schema
└── models/
    └── xxx.py          # SQLAlchemy Model
```

**依賴關係:**
```
API → Service → Model
         ↓
       MinIO (如需要)
```

**實作順序:**
1. Schema (如需要)
2. Service 方法
3. API 端點
4. 測試
