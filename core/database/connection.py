"""
PostgreSQL connection management — PgBouncer-ready.
Supports read/write separation and health checks.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from django.conf import settings

logger = logging.getLogger("database")

_pools: dict[str, pool.ThreadedConnectionPool] = {}
_pool_lock = threading.Lock()


def _pool_config(alias: str = "default") -> dict[str, Any]:
    db = settings.DATABASES[alias]
    return {
        "host": db.get("HOST", "localhost"),
        "port": int(db.get("PORT", 5432)),
        "database": db["NAME"],
        "user": db["USER"],
        "password": db["PASSWORD"],
        "options": db.get("OPTIONS", {}).get("options", ""),
    }


def get_connection_pool(alias: str = "default", minconn: int = 2, maxconn: int = 20) -> pool.ThreadedConnectionPool:
    with _pool_lock:
        if alias not in _pools:
            cfg = _pool_config(alias)
            _pools[alias] = pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                cursor_factory=RealDictCursor,
                **{k: v for k, v in cfg.items() if k != "options"},
                options=cfg.get("options") or f"-c search_path={settings.DB_SCHEMA},public -c timezone=Asia/Kolkata",
            )
            logger.info("Initialized connection pool: %s", alias)
        return _pools[alias]


def health_check(alias: str = "default") -> bool:
    try:
        with get_connection(alias) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        logger.exception("Database health check failed: %s", alias)
        return False


@contextmanager
def get_connection(alias: str = "default", readonly: bool = False) -> Generator[PgConnection, None, None]:
    """
    Acquire connection from pool.
    Use alias='read' for replica when READ_DATABASE is configured.
    """
    pool_alias = "read" if readonly and "read" in settings.DATABASES else alias
    pg_pool = get_connection_pool(pool_alias)
    conn = pg_pool.getconn()
    try:
        conn.autocommit = False
        yield conn
    finally:
        pg_pool.putconn(conn)


def close_all_pools() -> None:
    with _pool_lock:
        for alias, pg_pool in _pools.items():
            pg_pool.closeall()
            logger.info("Closed connection pool: %s", alias)
        _pools.clear()
