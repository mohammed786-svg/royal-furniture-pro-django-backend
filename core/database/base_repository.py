"""Base repository for raw SQL data access."""
from __future__ import annotations

from abc import ABC
from typing import Any, Optional, Sequence

from core.database import raw_queries
from core.database.query_builder import QueryBuilder


class BaseRepository(ABC):
    schema: str = "royal"

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.qualified_table = f"{self.schema}.{table_name}"

    def _builder(self, select: str = "*") -> QueryBuilder:
        return QueryBuilder(
            f"SELECT {select} FROM {self.qualified_table} WHERE is_deleted = FALSE",
            schema=self.schema,
        )

    def fetch_one(self, sql: str, params: Optional[Sequence[Any] | dict[str, Any]] = None) -> Any:
        rows = raw_queries.execute(sql, params, fetch=True)
        return rows[0] if rows else None

    def fetch_all(self, sql: str, params: Optional[Sequence[Any] | dict[str, Any]] = None) -> list[Any]:
        return raw_queries.execute(sql, params, fetch=True) or []
