from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class SearchHistoryRepository:
    schema = "royal"
    table = "search_historytbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        customer_id: Optional[int] = None,
        sort_by: str = "searched_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "sh.is_deleted = FALSE"
        if search:
            where += " AND sh.search_query ILIKE %s"
            params.append(f"%{search}%")
        if customer_id:
            where += " AND sh.customer_id = %s"
            params.append(customer_id)

        allowed_sort = {
            "search_query": "sh.search_query",
            "results_count": "sh.results_count",
            "searched_at": "sh.searched_at",
            "created_at": "sh.created_at",
        }
        order_col = allowed_sort.get(sort_by, "sh.searched_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} sh
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT sh.*
            FROM {self.schema}.{self.table} sh
            WHERE {where}
            ORDER BY {order_col} {direction}, sh.search_history_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, search_history_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE search_history_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [search_history_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (search_query, customer_id, session_id, results_count,
                 clicked_product_id, ip_address, searched_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, search_history_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(search_history_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE search_history_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), search_history_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, search_history_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE search_history_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [search_history_id]) > 0

    def dashboard_summary(self, *, days: int = 30) -> dict[str, Any]:
        sql = f"""
            SELECT
                COUNT(*) AS total_searches,
                COALESCE(AVG(sh.results_count), 0) AS avg_results,
                COUNT(CASE WHEN sh.results_count = 0 THEN 1 END) AS zero_result_count
            FROM {self.schema}.{self.table} sh
            WHERE sh.is_deleted = FALSE
              AND sh.searched_at >= NOW() - INTERVAL '{days} days'
        """
        return select_one(sql) or {}

    def top_queries(self, *, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                sh.search_query AS query,
                COUNT(*) AS count
            FROM {self.schema}.{self.table} sh
            WHERE sh.is_deleted = FALSE
              AND sh.searched_at >= NOW() - INTERVAL '{days} days'
              AND sh.search_query IS NOT NULL
              AND sh.search_query <> 'NA'
            GROUP BY sh.search_query
            ORDER BY count DESC
            LIMIT %s
        """
        return select_query(sql, [limit])

    def searches_trend(self, *, days: int = 30) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                TO_CHAR(sh.searched_at, 'Mon DD') AS label,
                COUNT(*) AS value
            FROM {self.schema}.{self.table} sh
            WHERE sh.is_deleted = FALSE
              AND sh.searched_at >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(sh.searched_at), TO_CHAR(sh.searched_at, 'Mon DD')
            ORDER BY DATE(sh.searched_at)
        """
        return select_query(sql)

    def zero_result_queries(self, *, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                sh.search_query AS query,
                COUNT(*) AS count
            FROM {self.schema}.{self.table} sh
            WHERE sh.is_deleted = FALSE
              AND sh.results_count = 0
              AND sh.searched_at >= NOW() - INTERVAL '{days} days'
              AND sh.search_query IS NOT NULL
              AND sh.search_query <> 'NA'
            GROUP BY sh.search_query
            ORDER BY count DESC
            LIMIT %s
        """
        return select_query(sql, [limit])


search_history_repository = SearchHistoryRepository()
