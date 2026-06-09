"""Parameterized raw SQL execution — SQL injection safe."""
from __future__ import annotations

from typing import Any, Optional, Sequence

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import execute_values

from core.database.connection import get_connection
from core.database.transaction import atomic
from core.debug.api_logger import log_sql_query


def execute(
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]] = None,
    *,
    conn: Optional[PgConnection] = None,
    fetch: bool = False,
    many: bool = False,
) -> Any:
    if conn is not None:
        return _run(conn, sql, params, fetch=fetch, many=many)
    with atomic() as connection:
        return _run(connection, sql, params, fetch=fetch, many=many)


def _run(
    conn: PgConnection,
    sql: str,
    params: Optional[Sequence[Any] | dict[str, Any]],
    *,
    fetch: bool,
    many: bool,
) -> Any:
    log_sql_query(sql, params)

    with conn.cursor() as cur:
        if many and isinstance(params, list):
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)
        if fetch:
            return cur.fetchall()
        if cur.description and cur.rowcount == 1:
            return cur.fetchone()
        return cur.rowcount


def execute_values_insert(
    sql: str,
    argslist: Sequence[Sequence[Any]],
    *,
    conn: Optional[PgConnection] = None,
    page_size: int = 100,
) -> None:
    runner = conn if conn is not None else None
    if runner is None:
        with atomic() as connection:
            with connection.cursor() as cur:
                execute_values(cur, sql, argslist, page_size=page_size)
        return
    with runner.cursor() as cur:
        execute_values(cur, sql, argslist, page_size=page_size)
