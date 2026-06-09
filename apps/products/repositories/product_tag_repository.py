from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class ProductTagRepository:
    schema = "royal"
    table = "product_tagtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "tag_name",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "t.is_deleted = FALSE"
        if search:
            where += " AND (t.tag_name ILIKE %s OR t.slug ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])

        allowed_sort = {
            "tag_name": "t.tag_name",
            "slug": "t.slug",
            "created_at": "t.created_at",
        }
        order_col = allowed_sort.get(sort_by, "t.tag_name")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} t
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                t.*,
                (
                    SELECT COUNT(*)
                    FROM {self.schema}.product_tag_maptbl m
                    WHERE m.product_tag_id = t.product_tag_id
                      AND m.is_deleted = FALSE
                      AND m.is_active = TRUE
                ) AS product_count
            FROM {self.schema}.{self.table} t
            WHERE {where}
            ORDER BY {order_col} {direction}, t.product_tag_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, tag_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE product_tag_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [tag_id])

    def slug_exists(self, slug: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT product_tag_id
            FROM {self.schema}.{self.table}
            WHERE slug = %s AND is_deleted = FALSE
        """
        params: list[Any] = [slug]
        if exclude_id:
            sql += " AND product_tag_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (tag_name, slug, is_active)
            VALUES (%s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()), conn=conn)
        return row or {}

    def update(
        self,
        tag_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(tag_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE product_tag_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), tag_id], conn=conn, fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, tag_id: int, *, conn: Optional[PgConnection] = None) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE product_tag_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [tag_id], conn=conn) > 0


product_tag_repository = ProductTagRepository()
