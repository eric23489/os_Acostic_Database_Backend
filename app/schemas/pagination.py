"""分頁相關的 Schema 定義。"""

from enum import Enum

from pydantic import BaseModel, Field


class SortOrder(str, Enum):
    """排序方向。"""

    ASC = "asc"
    DESC = "desc"


class PaginatedResponse[T](BaseModel):
    """分頁回應的通用 Schema。"""

    items: list[T] = Field(..., description="資料項目列表")
    total: int = Field(..., description="符合條件的總筆數")
    skip: int = Field(..., description="跳過的筆數")
    limit: int = Field(..., description="每頁筆數上限")
