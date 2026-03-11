---
name: new-resource
description: >
  洋聲新資源建立引導。當需要新增完整 CRUD 資源時使用（含 model/schema/service/endpoint）。
  Guides through the standard 8-step resource creation flow with soft-delete, AppException,
  pagination, and all project conventions built in.
tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
---

# New Resource — 洋聲新資源建立引導

## 用途

引導新增一個完整 CRUD 資源，確保每一層都符合專案規範。

---

## 開始前：讀取參考範本

在開始任何實作前，必須先讀取以下檔案作為範本：

```
Read: app/models/recorder.py          — ORM Model 範本（含軟刪除欄位）
Read: app/schemas/recorder.py         — Pydantic Schema 範本
Read: app/services/project_service.py — 最完整的 Service 範本
Read: app/api/v1/endpoints/api_recorders.py — Router 範本
Read: app/utils/query.py              — apply_search, apply_sorting, paginate
Read: app/core/exceptions.py          — AppException 常數命名慣例
Read: docs/error-list.md              — 現有錯誤碼（避免重複）
Read: tests/conftest.py               — fixture 定義
```

---

## 標準 8 步流程

### 步驟 1：ORM Model（`app/models/{resource}.py`）

必要欄位：
```python
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base
import datetime

class ResourceName(Base):
    __tablename__ = "resource_names"

    id = Column(Integer, primary_key=True, index=True)
    # ... 業務欄位 ...
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 軟刪除欄位（必須）
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, nullable=True)

# 部分唯一索引（活躍記錄的唯一性）
Index(
    "uq_resource_name_active",
    "name",
    unique=True,
    postgresql_where=(ResourceName.is_deleted.is_(False)),
)
```

完成後將 model import 加入 `app/db/base.py`（若有統一的 metadata 匯集）。

### 步驟 2：Pydantic Schemas（`app/schemas/{resource}.py`）

```python
class ResourceCreate(BaseModel):
    """建立請求"""
    name: str
    # ... 必填欄位 ...

class ResourceUpdate(BaseModel):
    """更新請求（所有欄位可選）"""
    name: str | None = None

class ResourceResponse(BaseModel):
    """回應"""
    id: int
    name: str
    created_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)
```

### 步驟 3：AppException 常數（`app/core/exceptions.py`）

命名規則：`MODULE_SPECIFIC_CONDITION`

```python
# {RESOURCE} 相關錯誤
RESOURCE_NOT_FOUND = AppException(error_code="RESOURCE_NOT_FOUND", status_code=404, message="...")
RESOURCE_NAME_DUPLICATE = AppException(error_code="RESOURCE_NAME_DUPLICATE", status_code=409, message="...")
```

### 步驟 4：更新 `docs/error-list.md`

**必須**在新增常數後同步更新：
```
Read: docs/error-list.md
```

按照文件開頭的 SOP 在對應表格新增一行。

### 步驟 5：Service 類別（`app/services/{resource}_service.py`）

```python
class ResourceService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_resource(self, resource_id: int) -> ResourceModel:
        """取得單筆，不存在或已刪除則 raise AppException"""
        resource = (
            self._db.query(ResourceModel)
            .filter(
                ResourceModel.id == resource_id,
                ResourceModel.is_deleted.is_(False),  # 注意：用 .is_(False)
            )
            .first()
        )
        if not resource:
            raise AppException(RESOURCE_NOT_FOUND)
        return resource

    def list_resources(self, pagination: PaginationParams, ...) -> tuple[list[ResourceModel], int]:
        """列表查詢（含分頁）"""
        query = self._db.query(ResourceModel).filter(ResourceModel.is_deleted.is_(False))
        query = apply_sorting(query, ResourceModel, pagination.sort_by, pagination.sort_order)
        return paginate(query, pagination)

    def create_resource(self, payload: ResourceCreate, created_by: int) -> ResourceModel:
        """建立，名稱重複則 raise AppException"""
        existing = (
            self._db.query(ResourceModel)
            .filter(ResourceModel.name == payload.name, ResourceModel.is_deleted.is_(False))
            .first()
        )
        if existing:
            raise AppException(RESOURCE_NAME_DUPLICATE)
        resource = ResourceModel(**payload.model_dump(), created_by=created_by)
        self._db.add(resource)
        self._db.commit()
        self._db.refresh(resource)
        return resource

    def update_resource(self, resource_id: int, payload: ResourceUpdate, updated_by: int) -> ResourceModel:
        """更新欄位"""
        resource = self.get_resource(resource_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(resource, field, value)
        self._db.commit()
        self._db.refresh(resource)
        return resource

    def delete_resource(self, resource_id: int, deleted_by: int) -> None:
        """軟刪除"""
        resource = self.get_resource(resource_id)
        resource.is_deleted = True
        resource.deleted_at = datetime.datetime.utcnow()
        resource.deleted_by = deleted_by
        self._db.commit()
```

### 步驟 6：Router 端點（`app/api/v1/endpoints/api_{resource}s.py`）

```python
router = APIRouter()

@router.get("", response_model=PaginatedResponse[ResourceResponse])
def list_resources(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[ResourceResponse]:
    """列表查詢"""
    service = ResourceService(db)
    resources, total = service.list_resources(pagination)
    return PaginatedResponse(items=resources, total=total, ...)

@router.post("", response_model=ResourceResponse, status_code=201)
def create_resource(
    payload: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResourceResponse:
    """建立資源"""
    service = ResourceService(db)
    return service.create_resource(payload, created_by=current_user.id)
```

**禁止**在 router 函式內寫 try-catch。

### 步驟 7：掛載 Router（`app/api/v1/api.py`）

```python
from app.api.v1.endpoints.api_resources import router as resources_router

api_router.include_router(resources_router, prefix="/resources", tags=["resources"])
```

### 步驟 8：Alembic Migration

```bash
alembic revision --autogenerate -m "add {resource} table"
alembic upgrade head
```

---

## 完成後

1. 呼叫 `convention-checker` 審查新增的 service 與 endpoint
2. 呼叫 `test-writer` 生成對應測試
3. 更新 `.claude/docs/changelog.md` 與 `.claude/docs/todo.md`
