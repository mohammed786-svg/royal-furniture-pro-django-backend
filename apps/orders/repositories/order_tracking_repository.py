from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query
from core.database.raw_queries import execute


class OrderTrackingRepository:
    schema = "royal"
    table = "order_trackingtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        order_id: Optional[int] = None,
        sort_by: str = "tracked_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "t.is_deleted = FALSE"
        if search:
            where += " AND (t.status_code ILIKE %s OR t.status_message ILIKE %s OR o.order_number ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if order_id:
            where += " AND t.order_id = %s"
            params.append(order_id)

        allowed_sort = {
            "tracked_at": "t.tracked_at",
            "status_code": "t.status_code",
            "created_at": "t.created_at",
        }
        order_col = allowed_sort.get(sort_by, "t.tracked_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} t
            INNER JOIN {self.schema}.ordertbl o ON o.order_id = t.order_id
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                t.*,
                o.order_number,
                c.full_name AS customer_name
            FROM {self.schema}.{self.table} t
            INNER JOIN {self.schema}.ordertbl o ON o.order_id = t.order_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = o.customer_id
            WHERE {where}
            ORDER BY {order_col} {direction}, t.order_tracking_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def list_by_order(self, order_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE order_id = %s AND is_deleted = FALSE
            ORDER BY tracked_at DESC
        """
        return select_query(sql, [order_id])

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (order_id, status_code, status_message, location, tracked_at, is_customer_visible)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, values)
        return row or {}


order_tracking_repository = OrderTrackingRepository()
