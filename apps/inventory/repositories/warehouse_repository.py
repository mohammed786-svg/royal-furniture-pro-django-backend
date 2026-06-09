from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class WarehouseRepository:
    schema = "royal"
    table = "warehousetbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "w.is_deleted = FALSE"
        if search:
            where += " AND (w.name ILIKE %s OR w.warehouse_code ILIKE %s OR w.city ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        allowed_sort = {
            "name": "w.name",
            "warehouse_code": "w.warehouse_code",
            "city": "w.city",
            "created_at": "w.created_at",
        }
        order_col = allowed_sort.get(sort_by, "w.name")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} w
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT w.*
            FROM {self.schema}.{self.table} w
            WHERE {where}
            ORDER BY w.is_primary DESC, {order_col} {direction}, w.warehouse_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, warehouse_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE warehouse_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [warehouse_id])

    def code_exists(self, code: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT warehouse_id
            FROM {self.schema}.{self.table}
            WHERE warehouse_code = %s AND is_deleted = FALSE
        """
        params: list[Any] = [code]
        if exclude_id:
            sql += " AND warehouse_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def clear_primary_flag(self, *, exclude_id: Optional[int] = None) -> None:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_primary = FALSE, updated_at = NOW()
            WHERE is_deleted = FALSE AND is_primary = TRUE
        """
        params: list[Any] = []
        if exclude_id:
            sql += " AND warehouse_id <> %s"
            params.append(exclude_id)
        update_query(sql, params)

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (warehouse_code, name, address_line1, address_line2,
                 city, state, pincode, country,
                 contact_phone, contact_email, is_primary, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, warehouse_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(warehouse_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE warehouse_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), warehouse_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, warehouse_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, is_primary = FALSE,
                updated_at = NOW()
            WHERE warehouse_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [warehouse_id]) > 0

    def list_options(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT warehouse_id, warehouse_code, name, is_primary
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY is_primary DESC, name
        """
        return select_query(sql)


warehouse_repository = WarehouseRepository()
