from __future__ import annotations

from typing import Any, Optional

from core.database import delete_query, insert_query_returning, select_one, select_query, update_query


class CategoryRepository:
    schema = "royal"
    table = "categorytbl"

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
        where = "c.is_deleted = FALSE"
        if search:
            where += " AND (c.name ILIKE %s OR c.slug ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])

        allowed_sort = {
            "name": "c.name",
            "slug": "c.slug",
            "display_order": "c.display_order",
            "created_at": "c.created_at",
        }
        order_col = allowed_sort.get(sort_by, "c.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} c
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                c.category_id,
                c.name,
                c.slug,
                c.image_url,
                c.icon_url,
                c.banner_url,
                c.seo_title,
                c.seo_description,
                c.seo_keywords,
                c.display_order,
                c.is_visible,
                c.is_featured,
                c.is_active,
                c.created_at,
                c.updated_at,
                (
                    SELECT COUNT(*)
                    FROM {self.schema}.sub_categorytbl sc
                    WHERE sc.category_id = c.category_id
                      AND sc.is_deleted = FALSE
                ) AS sub_category_count
            FROM {self.schema}.{self.table} c
            WHERE {where}
            ORDER BY {order_col} {direction}, c.category_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, category_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE category_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [category_id])

    def slug_exists(self, slug: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT category_id
            FROM {self.schema}.{self.table}
            WHERE slug = %s AND is_deleted = FALSE
        """
        params: list[Any] = [slug]
        if exclude_id:
            sql += " AND category_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (name, slug, image_url, icon_url, banner_url,
                 seo_title, seo_description, seo_keywords,
                 display_order, is_visible, is_featured, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, category_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(category_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE category_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        from core.database.raw_queries import execute

        rows = execute(sql, [*data.values(), category_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, category_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE category_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [category_id]) > 0

    def list_options(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT category_id, name, slug
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY display_order, name
        """
        return select_query(sql)


category_repository = CategoryRepository()
