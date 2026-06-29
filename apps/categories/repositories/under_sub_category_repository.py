from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query


class UnderSubCategoryRepository:
    schema = "royal"
    table = "under_sub_categorytbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
        sort_by: str = "display_order",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "usc.is_deleted = FALSE"
        if search:
            where += " AND (usc.name ILIKE %s OR usc.slug ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])
        if category_id:
            where += " AND usc.category_id = %s"
            params.append(category_id)
        if sub_category_id:
            where += " AND usc.sub_category_id = %s"
            params.append(sub_category_id)

        allowed_sort = {
            "name": "usc.name",
            "slug": "usc.slug",
            "display_order": "usc.display_order",
            "created_at": "usc.created_at",
        }
        order_col = allowed_sort.get(sort_by, "usc.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} usc
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                usc.under_sub_category_id,
                usc.sub_category_id,
                usc.category_id,
                c.name AS category_name,
                sc.name AS sub_category_name,
                usc.name,
                usc.slug,
                usc.image_url,
                usc.icon_url,
                usc.banner_url,
                usc.seo_title,
                usc.seo_description,
                usc.seo_keywords,
                usc.display_order,
                usc.is_visible,
                usc.is_active,
                usc.created_at,
                usc.updated_at
            FROM {self.schema}.{self.table} usc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = usc.category_id
            INNER JOIN {self.schema}.sub_categorytbl sc ON sc.sub_category_id = usc.sub_category_id
            WHERE {where}
            ORDER BY {order_col} {direction}, usc.under_sub_category_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_slug(self, sub_category_id: int, slug: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT usc.*, c.name AS category_name, sc.name AS sub_category_name
            FROM {self.schema}.{self.table} usc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = usc.category_id
            INNER JOIN {self.schema}.sub_categorytbl sc ON sc.sub_category_id = usc.sub_category_id
            WHERE usc.sub_category_id = %s
              AND usc.slug = %s
              AND usc.is_deleted = FALSE
              AND usc.is_visible = TRUE
              AND usc.is_active = TRUE
        """
        return select_one(sql, [sub_category_id, slug])

    def resolve_for_listing(
        self,
        sub_category_id: int,
        slug_or_id: str,
    ) -> Optional[dict[str, Any]]:
        """Resolve under-sub-category by numeric ID or slug (with simple plural tolerance)."""
        token = (slug_or_id or "").strip()
        if not token:
            return None

        if token.isdigit():
            row = self.fetch_by_id(int(token))
            if row and int(row["sub_category_id"]) == sub_category_id:
                return row
            return None

        row = self.fetch_by_slug(sub_category_id, token)
        if row:
            return row

        if token.endswith("s"):
            return self.fetch_by_slug(sub_category_id, token[:-1])

        return self.fetch_by_slug(sub_category_id, f"{token}s")

    def fetch_by_id(self, under_sub_category_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT usc.*, c.name AS category_name, sc.name AS sub_category_name
            FROM {self.schema}.{self.table} usc
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = usc.category_id
            INNER JOIN {self.schema}.sub_categorytbl sc ON sc.sub_category_id = usc.sub_category_id
            WHERE usc.under_sub_category_id = %s AND usc.is_deleted = FALSE
        """
        return select_one(sql, [under_sub_category_id])

    def slug_exists(
        self,
        sub_category_id: int,
        slug: str,
        *,
        exclude_id: Optional[int] = None,
    ) -> bool:
        sql = f"""
            SELECT under_sub_category_id
            FROM {self.schema}.{self.table}
            WHERE sub_category_id = %s AND slug = %s
        """
        params: list[Any] = [sub_category_id, slug]
        if exclude_id:
            sql += " AND under_sub_category_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (sub_category_id, category_id, name, slug, image_url, icon_url, banner_url,
                 seo_title, seo_description, seo_keywords,
                 display_order, is_visible, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, under_sub_category_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(under_sub_category_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE under_sub_category_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        from core.database.raw_queries import execute

        rows = execute(sql, [*data.values(), under_sub_category_id], fetch=True)
        return rows[0] if rows else None

    def list_options(
        self,
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = "usc.is_deleted = FALSE AND usc.is_active = TRUE"
        if category_id:
            where += " AND usc.category_id = %s"
            params.append(category_id)
        if sub_category_id:
            where += " AND usc.sub_category_id = %s"
            params.append(sub_category_id)
        sql = f"""
            SELECT
                usc.under_sub_category_id,
                usc.sub_category_id,
                usc.category_id,
                usc.name,
                usc.slug,
                sc.name AS sub_category_name,
                c.name AS category_name
            FROM {self.schema}.{self.table} usc
            INNER JOIN {self.schema}.sub_categorytbl sc ON sc.sub_category_id = usc.sub_category_id
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = usc.category_id
            WHERE {where}
            ORDER BY usc.display_order, usc.name
        """
        return select_query(sql, params or None)

    def soft_delete(self, under_sub_category_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE under_sub_category_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [under_sub_category_id]) > 0


under_sub_category_repository = UnderSubCategoryRepository()
