from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query


class SubCategoryRepository:
    schema = "royal"
    table = "sub_categorytbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        category_id: Optional[int] = None,
        sort_by: str = "display_order",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "sc.is_deleted = FALSE"
        if search:
            where += " AND (sc.name ILIKE %s OR sc.slug ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])
        if category_id:
            where += " AND sc.category_id = %s"
            params.append(category_id)

        allowed_sort = {
            "name": "sc.name",
            "slug": "sc.slug",
            "display_order": "sc.display_order",
            "created_at": "sc.created_at",
        }
        order_col = allowed_sort.get(sort_by, "sc.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} sc
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                sc.sub_category_id,
                sc.category_id,
                c.name AS category_name,
                sc.name,
                sc.slug,
                sc.image_url,
                sc.icon_url,
                sc.banner_url,
                sc.seo_title,
                sc.seo_description,
                sc.seo_keywords,
                sc.display_order,
                sc.is_visible,
                sc.is_active,
                sc.created_at,
                sc.updated_at,
                (
                    SELECT COUNT(*)
                    FROM {self.schema}.under_sub_categorytbl usc
                    WHERE usc.sub_category_id = sc.sub_category_id
                      AND usc.is_deleted = FALSE
                ) AS under_sub_category_count
            FROM {self.schema}.{self.table} sc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = sc.category_id
            WHERE {where}
            ORDER BY {order_col} {direction}, sc.sub_category_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, sub_category_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT sc.*, c.name AS category_name
            FROM {self.schema}.{self.table} sc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = sc.category_id
            WHERE sc.sub_category_id = %s AND sc.is_deleted = FALSE
        """
        return select_one(sql, [sub_category_id])

    def fetch_by_slug(self, category_id: int, slug: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT sc.*, c.name AS category_name, c.slug AS category_slug
            FROM {self.schema}.{self.table} sc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = sc.category_id
            WHERE sc.category_id = %s
              AND sc.slug = %s
              AND sc.is_deleted = FALSE
              AND sc.is_visible = TRUE
              AND sc.is_active = TRUE
              AND c.is_deleted = FALSE
        """
        return select_one(sql, [category_id, slug])

    def slug_exists(
        self,
        category_id: int,
        slug: str,
        *,
        exclude_id: Optional[int] = None,
    ) -> bool:
        sql = f"""
            SELECT sub_category_id
            FROM {self.schema}.{self.table}
            WHERE category_id = %s AND slug = %s
        """
        params: list[Any] = [category_id, slug]
        if exclude_id:
            sql += " AND sub_category_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (category_id, name, slug, image_url, icon_url, banner_url,
                 seo_title, seo_description, seo_keywords,
                 display_order, is_visible, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, sub_category_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(sub_category_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE sub_category_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        from core.database.raw_queries import execute

        rows = execute(sql, [*data.values(), sub_category_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, sub_category_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE sub_category_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [sub_category_id]) > 0

    def list_options(self, category_id: Optional[int] = None) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = "sc.is_deleted = FALSE AND sc.is_active = TRUE"
        if category_id:
            where += " AND sc.category_id = %s"
            params.append(category_id)
        sql = f"""
            SELECT sc.sub_category_id, sc.category_id, sc.name, sc.slug, c.name AS category_name
            FROM {self.schema}.{self.table} sc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = sc.category_id
            WHERE {where}
            ORDER BY sc.display_order, sc.name
        """
        return select_query(sql, params or None)


sub_category_repository = SubCategoryRepository()
