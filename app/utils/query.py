"""查詢相關的工具函式。"""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Query

from app.schemas.pagination import SortOrder


def apply_search(
    query: Query,
    model: Any,
    fields: list[str],
    search: str | None,
) -> Query:
    """
    對指定欄位套用 ILIKE 搜尋。

    Args:
        query: SQLAlchemy Query 物件
        model: SQLAlchemy Model 類別
        fields: 要搜尋的欄位名稱列表
        search: 搜尋關鍵字

    Returns:
        套用搜尋條件後的 Query
    """
    if not search:
        return query

    search_pattern = f"%{search}%"
    conditions = []
    for field_name in fields:
        column = getattr(model, field_name, None)
        if column is not None:
            conditions.append(column.ilike(search_pattern))

    if conditions:
        from sqlalchemy import or_

        query = query.filter(or_(*conditions))

    return query


def apply_sorting(
    query: Query,
    model: Any,
    sort_by: str | None,
    order: SortOrder,
    allowed_fields: list[str],
) -> Query:
    """
    對查詢結果套用排序。

    Args:
        query: SQLAlchemy Query 物件
        model: SQLAlchemy Model 類別
        sort_by: 排序欄位名稱
        order: 排序方向 (asc/desc)
        allowed_fields: 允許排序的欄位白名單

    Returns:
        套用排序後的 Query

    Raises:
        HTTPException: 當 sort_by 欄位不在白名單中
    """
    if not sort_by:
        return query

    if sort_by not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by: '{sort_by}'. Allowed: {allowed_fields}",
        )

    column = getattr(model, sort_by, None)
    if column is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sort field '{sort_by}' does not exist on model",
        )

    if order == SortOrder.DESC:
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    return query


def paginate(query: Query, skip: int, limit: int) -> tuple[list[Any], int]:
    """
    對查詢結果套用分頁並取得總筆數。

    Args:
        query: SQLAlchemy Query 物件
        skip: 跳過的筆數
        limit: 每頁筆數上限

    Returns:
        tuple: (items, total) - 分頁後的項目列表和總筆數
    """
    # 取得總筆數 (在套用 offset/limit 之前)
    total = query.count()

    # 套用分頁
    items = query.offset(skip).limit(limit).all()

    return items, total


def apply_filter(
    query: Query,
    model: Any,
    field: str,
    value: Any,
) -> Query:
    """
    對指定欄位套用相等篩選。

    Args:
        query: SQLAlchemy Query 物件
        model: SQLAlchemy Model 類別
        field: 欄位名稱
        value: 篩選值

    Returns:
        套用篩選條件後的 Query
    """
    if value is None:
        return query

    column = getattr(model, field, None)
    if column is not None:
        query = query.filter(column == value)

    return query
