from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query, select_one, select_query


class LoginHistoryRepository:
    schema = "royal"
    table = "login_historytbl"

    def record(
        self,
        *,
        user_id: int | None,
        login_type: str,
        status: str,
        ip_address: str,
        user_agent: str,
        failure_reason: str = "NA",
    ) -> None:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (user_id, login_type, ip_address, user_agent, status, failure_reason)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        insert_query(sql, [user_id, login_type, ip_address, user_agent, status, failure_reason])

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        user_id: Optional[int] = None,
        status: str = "",
        login_type: str = "",
        sort_by: str = "login_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "lh.is_deleted = FALSE"
        if user_id is not None:
            where += " AND lh.user_id = %s"
            params.append(user_id)
        if status:
            where += " AND lh.status = %s"
            params.append(status)
        if login_type:
            where += " AND lh.login_type = %s"
            params.append(login_type)

        allowed_sort = {
            "login_at": "lh.login_at",
            "status": "lh.status",
            "login_type": "lh.login_type",
            "created_at": "lh.created_at",
        }
        order_col = allowed_sort.get(sort_by, "lh.login_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} lh
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                lh.*,
                u.email AS user_email,
                u.full_name AS user_full_name,
                c.email AS customer_email,
                c.full_name AS customer_full_name
            FROM {self.schema}.{self.table} lh
            LEFT JOIN {self.schema}.usertbl u ON u.user_id = lh.user_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = lh.customer_id
            WHERE {where}
            ORDER BY {order_col} {direction}, lh.login_history_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, login_history_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                lh.*,
                u.email AS user_email,
                u.full_name AS user_full_name,
                c.email AS customer_email,
                c.full_name AS customer_full_name
            FROM {self.schema}.{self.table} lh
            LEFT JOIN {self.schema}.usertbl u ON u.user_id = lh.user_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = lh.customer_id
            WHERE lh.login_history_id = %s AND lh.is_deleted = FALSE
        """
        return select_one(sql, [login_history_id])


login_history_repository = LoginHistoryRepository()
