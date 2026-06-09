from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class BrandRepository:
    schema = "royal"
    table = "brandtbl"

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
        where = "b.is_deleted = FALSE"
        if search:
            where += " AND (b.name ILIKE %s OR b.slug ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])

        allowed_sort = {
            "name": "b.name",
            "slug": "b.slug",
            "display_order": "b.display_order",
            "created_at": "b.created_at",
        }
        order_col = allowed_sort.get(sort_by, "b.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} b
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT b.*
            FROM {self.schema}.{self.table} b
            WHERE {where}
            ORDER BY {order_col} {direction}, b.brand_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, brand_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE brand_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [brand_id])

    def slug_exists(self, slug: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT brand_id
            FROM {self.schema}.{self.table}
            WHERE slug = %s AND is_deleted = FALSE
        """
        params: list[Any] = [slug]
        if exclude_id:
            sql += " AND brand_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (name, slug, logo_url, description, website_url, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, brand_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(brand_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE brand_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), brand_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, brand_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE brand_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [brand_id]) > 0

    def list_options(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT brand_id, name, slug
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY display_order, name
        """
        return select_query(sql)


brand_repository = BrandRepository()
