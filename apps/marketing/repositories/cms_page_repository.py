from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class CmsPageRepository:
    schema = "royal"
    table = "cms_pagetbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "p.is_deleted = FALSE"
        if search:
            where += " AND (p.title ILIKE %s OR p.slug ILIKE %s OR p.page_code ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        allowed_sort = {
            "title": "p.title",
            "slug": "p.slug",
            "page_code": "p.page_code",
            "published_at": "p.published_at",
            "created_at": "p.created_at",
        }
        order_col = allowed_sort.get(sort_by, "p.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} p
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT p.*
            FROM {self.schema}.{self.table} p
            WHERE {where}
            ORDER BY {order_col} {direction}, p.cms_page_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, cms_page_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE cms_page_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [cms_page_id])

    def code_exists(self, page_code: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT cms_page_id
            FROM {self.schema}.{self.table}
            WHERE page_code = %s AND is_deleted = FALSE
        """
        params: list[Any] = [page_code]
        if exclude_id:
            sql += " AND cms_page_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def slug_exists(self, slug: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT cms_page_id
            FROM {self.schema}.{self.table}
            WHERE slug = %s AND is_deleted = FALSE
        """
        params: list[Any] = [slug]
        if exclude_id:
            sql += " AND cms_page_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (page_code, title, slug, content, seo_title, seo_description,
                 seo_keywords, is_published, published_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, cms_page_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(cms_page_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE cms_page_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), cms_page_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, cms_page_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE cms_page_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [cms_page_id]) > 0


cms_page_repository = CmsPageRepository()
