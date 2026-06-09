from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class OrderStatusRepository:
    schema = "royal"
    table = "order_statustbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "display_order",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "s.is_deleted = FALSE"
        if search:
            where += " AND (s.status_code ILIKE %s OR s.status_name ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])

        allowed_sort = {
            "status_code": "s.status_code",
            "status_name": "s.status_name",
            "display_order": "s.display_order",
            "created_at": "s.created_at",
        }
        order_col = allowed_sort.get(sort_by, "s.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} s
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT s.*
            FROM {self.schema}.{self.table} s
            WHERE {where}
            ORDER BY {order_col} {direction}, s.order_status_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def list_all_active(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY display_order ASC, order_status_id ASC
        """
        return select_query(sql)

    def fetch_by_id(self, order_status_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE order_status_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [order_status_id])

    def fetch_by_code(self, status_code: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE status_code = %s AND is_deleted = FALSE
        """
        return select_one(sql, [status_code])

    def code_exists(self, code: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT order_status_id
            FROM {self.schema}.{self.table}
            WHERE status_code = %s AND is_deleted = FALSE
        """
        params: list[Any] = [code]
        if exclude_id:
            sql += " AND order_status_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (status_code, status_name, description, display_order, is_terminal, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, order_status_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(order_status_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE order_status_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), order_status_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, order_status_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE order_status_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [order_status_id]) > 0


order_status_repository = OrderStatusRepository()
