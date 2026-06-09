from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class TestimonialRepository:
    schema = "royal"
    table = "testimonialtbl"

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
        where = "t.is_deleted = FALSE"
        if search:
            where += " AND (t.customer_name ILIKE %s OR t.location ILIKE %s OR t.testimonial_text ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        allowed_sort = {
            "customer_name": "t.customer_name",
            "rating": "t.rating",
            "display_order": "t.display_order",
            "created_at": "t.created_at",
        }
        order_col = allowed_sort.get(sort_by, "t.display_order")
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
                p.name AS product_name,
                p.sku AS product_sku
            FROM {self.schema}.{self.table} t
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = t.product_id
            WHERE {where}
            ORDER BY {order_col} {direction}, t.testimonial_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, testimonial_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                t.*,
                p.name AS product_name,
                p.sku AS product_sku
            FROM {self.schema}.{self.table} t
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = t.product_id
            WHERE t.testimonial_id = %s AND t.is_deleted = FALSE
        """
        return select_one(sql, [testimonial_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (customer_name, customer_image, location, rating, testimonial_text,
                 product_id, is_featured, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, testimonial_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(testimonial_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE testimonial_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), testimonial_id], fetch=True)
        if not rows:
            return None
        return self.fetch_by_id(testimonial_id)

    def soft_delete(self, testimonial_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE testimonial_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [testimonial_id]) > 0


testimonial_repository = TestimonialRepository()
