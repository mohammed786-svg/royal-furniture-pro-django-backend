from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class PageViewRepository:
    schema = "royal"
    table = "page_viewtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        customer_id: Optional[int] = None,
        product_id: Optional[int] = None,
        sort_by: str = "viewed_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "pv.is_deleted = FALSE"
        if search:
            where += " AND (pv.page_url ILIKE %s OR pv.page_title ILIKE %s OR pv.referrer ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if customer_id:
            where += " AND pv.customer_id = %s"
            params.append(customer_id)
        if product_id:
            where += " AND pv.product_id = %s"
            params.append(product_id)

        allowed_sort = {
            "page_url": "pv.page_url",
            "page_title": "pv.page_title",
            "viewed_at": "pv.viewed_at",
            "created_at": "pv.created_at",
        }
        order_col = allowed_sort.get(sort_by, "pv.viewed_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} pv
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT pv.*
            FROM {self.schema}.{self.table} pv
            WHERE {where}
            ORDER BY {order_col} {direction}, pv.page_view_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, page_view_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE page_view_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [page_view_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (page_url, page_title, customer_id, session_id,
                 category_id, sub_category_id, product_id, referrer, ip_address, viewed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, page_view_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(page_view_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE page_view_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), page_view_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, page_view_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE page_view_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [page_view_id]) > 0

    def dashboard_summary(self, *, days: int = 30) -> dict[str, Any]:
        sql = f"""
            SELECT
                COUNT(*) AS total_views,
                COUNT(DISTINCT pv.session_id) AS unique_sessions
            FROM {self.schema}.{self.table} pv
            WHERE pv.is_deleted = FALSE
              AND pv.viewed_at >= NOW() - INTERVAL '{days} days'
        """
        summary = select_one(sql) or {}

        referrer_sql = f"""
            SELECT pv.referrer AS label, COUNT(*) AS value
            FROM {self.schema}.{self.table} pv
            WHERE pv.is_deleted = FALSE
              AND pv.viewed_at >= NOW() - INTERVAL '{days} days'
              AND pv.referrer IS NOT NULL
              AND pv.referrer <> 'NA'
            GROUP BY pv.referrer
            ORDER BY value DESC
            LIMIT 1
        """
        top_referrer = select_one(referrer_sql)
        summary["top_referrer"] = top_referrer.get("label") if top_referrer else None
        return summary

    def views_trend(self, *, days: int = 30) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                TO_CHAR(pv.viewed_at, 'Mon DD') AS label,
                COUNT(*) AS value
            FROM {self.schema}.{self.table} pv
            WHERE pv.is_deleted = FALSE
              AND pv.viewed_at >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(pv.viewed_at), TO_CHAR(pv.viewed_at, 'Mon DD')
            ORDER BY DATE(pv.viewed_at)
        """
        return select_query(sql)

    def top_pages(self, *, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                pv.page_url,
                pv.page_title,
                COUNT(*) AS views
            FROM {self.schema}.{self.table} pv
            WHERE pv.is_deleted = FALSE
              AND pv.viewed_at >= NOW() - INTERVAL '{days} days'
            GROUP BY pv.page_url, pv.page_title
            ORDER BY views DESC
            LIMIT %s
        """
        return select_query(sql, [limit])

    def views_by_product(self, *, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                COALESCE(p.name, 'Unknown') AS product_name,
                COUNT(*) AS views
            FROM {self.schema}.{self.table} pv
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = pv.product_id
            WHERE pv.is_deleted = FALSE
              AND pv.product_id IS NOT NULL
              AND pv.viewed_at >= NOW() - INTERVAL '{days} days'
            GROUP BY p.name
            ORDER BY views DESC
            LIMIT %s
        """
        return select_query(sql, [limit])


page_view_repository = PageViewRepository()
