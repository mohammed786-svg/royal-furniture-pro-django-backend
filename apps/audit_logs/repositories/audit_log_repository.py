from __future__ import annotations

import json
from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query


class AuditLogRepository:
    schema = "royal"
    table = "audit_logtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        action_type: str = "",
        table_name: str = "",
        user_id: Optional[int] = None,
        sort_by: str = "logged_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "al.is_deleted = FALSE"
        if search:
            where += " AND (al.table_name ILIKE %s OR al.remarks ILIKE %s OR al.action_type ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if action_type:
            where += " AND al.action_type = %s"
            params.append(action_type)
        if table_name:
            where += " AND al.table_name = %s"
            params.append(table_name)
        if user_id:
            where += " AND al.user_id = %s"
            params.append(user_id)

        allowed_sort = {
            "action_type": "al.action_type",
            "table_name": "al.table_name",
            "logged_at": "al.logged_at",
            "created_at": "al.created_at",
        }
        order_col = allowed_sort.get(sort_by, "al.logged_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} al
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT al.*
            FROM {self.schema}.{self.table} al
            WHERE {where}
            ORDER BY {order_col} {direction}, al.audit_log_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, audit_log_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE audit_log_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [audit_log_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        old_values = data.get("old_values")
        new_values = data.get("new_values")
        if isinstance(old_values, dict):
            old_values = json.dumps(old_values)
        if isinstance(new_values, dict):
            new_values = json.dumps(new_values)

        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (user_id, customer_id, action_type, table_name, record_id,
                 old_values, new_values, ip_address, user_agent, remarks, logged_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
            RETURNING *
        """
        values = [
            data.get("user_id"),
            data.get("customer_id"),
            data.get("action_type"),
            data.get("table_name"),
            data.get("record_id"),
            old_values or "{}",
            new_values or "{}",
            data.get("ip_address"),
            data.get("user_agent"),
            data.get("remarks"),
            data.get("logged_at"),
        ]
        row = insert_query_returning(sql, values)
        return row or {}


audit_log_repository = AuditLogRepository()
