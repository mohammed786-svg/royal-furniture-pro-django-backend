"""Common CRUD helpers for parameterized raw SQL."""
from __future__ import annotations

from typing import Any, Optional, Sequence

from psycopg2.extensions import connection as PgConnection

from core.database.raw_queries import execute


def select_query(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
) -> list[dict[str, Any]]:
    rows = execute(sql, params, conn=conn, fetch=True)
    return list(rows or [])


def select_one(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
) -> Optional[dict[str, Any]]:
    rows = select_query(sql, params, conn=conn)
    return rows[0] if rows else None


def insert_query(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
) -> int:
    result = execute(sql, params, conn=conn, fetch=False)
    return int(result or 0)


def insert_query_returning(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
) -> Optional[dict[str, Any]]:
    rows = execute(sql, params, conn=conn, fetch=True)
    if not rows:
        return None
    return rows[0]


def update_query(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
) -> int:
    result = execute(sql, params, conn=conn, fetch=False)
    return int(result or 0)


def delete_query(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
) -> int:
    result = execute(sql, params, conn=conn, fetch=False)
    return int(result or 0)
