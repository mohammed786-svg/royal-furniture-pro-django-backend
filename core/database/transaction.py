"""Transaction management for raw SQL operations."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from psycopg2.extensions import connection as PgConnection

from core.database.connection import get_connection


@contextmanager
def atomic(alias: str = "default", readonly: bool = False) -> Generator[PgConnection, None, None]:
    with get_connection(alias=alias, readonly=readonly) as conn:
        try:
            yield conn
            if not readonly:
                conn.commit()
        except Exception:
            conn.rollback()
            raise


@contextmanager
def savepoint(conn: PgConnection, name: str = "sp1") -> Generator[None, None, None]:
    with conn.cursor() as cur:
        cur.execute(f"SAVEPOINT {name}")
    try:
        yield
        with conn.cursor() as cur:
            cur.execute(f"RELEASE SAVEPOINT {name}")
    except Exception:
        with conn.cursor() as cur:
            cur.execute(f"ROLLBACK TO SAVEPOINT {name}")
        raise
