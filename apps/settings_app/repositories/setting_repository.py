from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class SettingRepository:
    schema = "royal"
    table = "settingstbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        group: str = "",
        sort_by: str = "setting_key",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "s.is_deleted = FALSE"
        if search:
            where += " AND (s.setting_key ILIKE %s OR s.setting_value ILIKE %s OR s.description ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if group:
            where += " AND s.setting_group = %s"
            params.append(group)

        allowed_sort = {
            "setting_key": "s.setting_key",
            "setting_group": "s.setting_group",
            "created_at": "s.created_at",
        }
        order_col = allowed_sort.get(sort_by, "s.setting_key")
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
            ORDER BY {order_col} {direction}, s.setting_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, setting_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE setting_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [setting_id])

    def key_exists(self, key: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT setting_id
            FROM {self.schema}.{self.table}
            WHERE setting_key = %s AND is_deleted = FALSE
        """
        params: list[Any] = [key]
        if exclude_id:
            sql += " AND setting_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (setting_key, setting_value, setting_group, value_type,
                 is_encrypted, description, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, setting_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(setting_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE setting_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), setting_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, setting_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE setting_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [setting_id]) > 0

    def list_groups(self) -> list[str]:
        sql = f"""
            SELECT DISTINCT setting_group
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE
              AND setting_group IS NOT NULL
              AND setting_group <> 'NA'
            ORDER BY setting_group
        """
        rows = select_query(sql)
        return [row["setting_group"] for row in rows]


setting_repository = SettingRepository()
