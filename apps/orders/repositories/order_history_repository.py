from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_query
from core.database.raw_queries import execute


class OrderHistoryRepository:
    schema = "royal"
    table = "order_historytbl"

    def list_by_order(self, order_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT h.*, u.full_name AS changed_by_name
            FROM {self.schema}.{self.table} h
            LEFT JOIN {self.schema}.usertbl u ON u.user_id = h.changed_by
            WHERE h.order_id = %s AND h.is_deleted = FALSE
            ORDER BY h.changed_at DESC
        """
        return select_query(sql, [order_id])

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (order_id, from_status, to_status, changed_by, change_reason, metadata, changed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, values)
        return row or {}


order_history_repository = OrderHistoryRepository()
