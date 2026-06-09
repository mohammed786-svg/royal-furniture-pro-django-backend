from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class NotificationRepository:
    schema = "royal"
    table = "notificationtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        channel: str = "",
        target_type: str = "",
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "n.is_deleted = FALSE"
        if search:
            where += " AND (n.title ILIKE %s OR n.message ILIKE %s OR n.template_code ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if channel:
            where += " AND n.channel = %s"
            params.append(channel)
        if target_type:
            where += " AND n.target_type = %s"
            params.append(target_type)
        if is_active is not None:
            where += " AND n.is_active = %s"
            params.append(is_active)

        allowed_sort = {
            "title": "n.title",
            "channel": "n.channel",
            "target_type": "n.target_type",
            "created_at": "n.created_at",
        }
        order_col = allowed_sort.get(sort_by, "n.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} n
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT n.*
            FROM {self.schema}.{self.table} n
            WHERE {where}
            ORDER BY {order_col} {direction}, n.notification_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, notification_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE notification_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [notification_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (title, message, channel, template_code, target_type, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, notification_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(notification_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE notification_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), notification_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, notification_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE notification_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [notification_id]) > 0


notification_repository = NotificationRepository()
