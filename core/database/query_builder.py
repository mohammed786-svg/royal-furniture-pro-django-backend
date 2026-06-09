"""Lightweight SQL query builder for dynamic filters (raw SQL, not ORM)."""
from __future__ import annotations

from typing import Any


class QueryBuilder:
    def __init__(self, base_sql: str, schema: str = "royal") -> None:
        self.base_sql = base_sql
        self.schema = schema
        self._where: list[str] = []
        self._params: list[Any] = []
        self._order: list[str] = []
        self._limit: int | None = None
        self._offset: int | None = None

    def where(self, clause: str, *params: Any) -> "QueryBuilder":
        self._where.append(clause)
        self._params.extend(params)
        return self

    def order_by(self, clause: str) -> "QueryBuilder":
        self._order.append(clause)
        return self

    def paginate(self, page: int, page_size: int) -> "QueryBuilder":
        self._limit = page_size
        self._offset = max(0, (page - 1) * page_size)
        return self

    def build(self) -> tuple[str, list[Any]]:
        sql = self.base_sql
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        if self._order:
            sql += " ORDER BY " + ", ".join(self._order)
        if self._limit is not None:
            sql += " LIMIT %s"
            self._params.append(self._limit)
        if self._offset is not None:
            sql += " OFFSET %s"
            self._params.append(self._offset)
        return sql, self._params

    def table(self, name: str) -> str:
        return f"{self.schema}.{name}"
