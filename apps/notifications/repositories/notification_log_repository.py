from __future__ import annotations

import json
from typing import Any, Optional

from core.database import select_one, select_query


class NotificationLogRepository:
    schema = "royal"
    table = "notification_logtbl"

    def list_by_notification_id(self, notification_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                nl.*,
                c.full_name AS customer_full_name,
                c.email AS customer_email,
                u.full_name AS user_full_name,
                u.email AS user_email
            FROM {self.schema}.{self.table} nl
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = nl.customer_id
            LEFT JOIN {self.schema}.usertbl u ON u.user_id = nl.user_id
            WHERE nl.notification_id = %s AND nl.is_deleted = FALSE
            ORDER BY nl.created_at DESC, nl.notification_log_id DESC
        """
        return select_query(sql, [notification_id])

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        notification_id: Optional[int] = None,
        status: str = "",
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "nl.is_deleted = FALSE"
        if notification_id is not None:
            where += " AND nl.notification_id = %s"
            params.append(notification_id)
        if status:
            where += " AND nl.status = %s"
            params.append(status)

        allowed_sort = {
            "status": "nl.status",
            "sent_at": "nl.sent_at",
            "created_at": "nl.created_at",
        }
        order_col = allowed_sort.get(sort_by, "nl.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} nl
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                nl.*,
                n.title AS notification_title,
                c.full_name AS customer_full_name,
                c.email AS customer_email,
                u.full_name AS user_full_name,
                u.email AS user_email
            FROM {self.schema}.{self.table} nl
            LEFT JOIN {self.schema}.notificationtbl n ON n.notification_id = nl.notification_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = nl.customer_id
            LEFT JOIN {self.schema}.usertbl u ON u.user_id = nl.user_id
            WHERE {where}
            ORDER BY {order_col} {direction}, nl.notification_log_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, notification_log_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                nl.*,
                n.title AS notification_title,
                c.full_name AS customer_full_name,
                c.email AS customer_email,
                u.full_name AS user_full_name,
                u.email AS user_email
            FROM {self.schema}.{self.table} nl
            LEFT JOIN {self.schema}.notificationtbl n ON n.notification_id = nl.notification_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = nl.customer_id
            LEFT JOIN {self.schema}.usertbl u ON u.user_id = nl.user_id
            WHERE nl.notification_log_id = %s AND nl.is_deleted = FALSE
        """
        return select_one(sql, [notification_log_id])

    @staticmethod
    def parse_metadata(value: Any) -> dict[str, Any]:
        if value in (None, "", "NA"):
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


notification_log_repository = NotificationLogRepository()
