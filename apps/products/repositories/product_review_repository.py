from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class ProductReviewRepository:
    schema = "royal"
    table = "product_reviewtbl"
    rating_table = "product_ratingtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        product_id: Optional[int] = None,
        is_approved: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "r.is_deleted = FALSE"
        if search:
            where += " AND (r.title ILIKE %s OR r.review_text ILIKE %s OR p.name ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if product_id is not None:
            where += " AND r.product_id = %s"
            params.append(product_id)
        if is_approved is not None:
            where += " AND r.is_approved = %s"
            params.append(is_approved)

        allowed_sort = {
            "created_at": "r.created_at",
            "rating": "r.rating",
            "title": "r.title",
        }
        order_col = allowed_sort.get(sort_by, "r.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} r
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = r.product_id
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                r.*,
                p.name AS product_name,
                p.sku AS product_sku,
                c.full_name AS customer_name,
                c.email AS customer_email
            FROM {self.schema}.{self.table} r
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = r.product_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = r.customer_id
            WHERE {where}
            ORDER BY {order_col} {direction}, r.product_review_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, review_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                r.*,
                p.name AS product_name,
                p.sku AS product_sku,
                c.full_name AS customer_name,
                c.email AS customer_email
            FROM {self.schema}.{self.table} r
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = r.product_id
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = r.customer_id
            WHERE r.product_review_id = %s AND r.is_deleted = FALSE
        """
        return select_one(sql, [review_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (product_id, customer_id, order_id, title, review_text, rating,
                 is_verified_purchase, is_approved, approved_by, approved_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(
        self,
        review_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(review_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE product_review_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), review_id], conn=conn, fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, review_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE product_review_id = %s AND is_deleted = FALSE
            RETURNING product_id, is_approved
        """
        rows = execute(sql, [review_id], fetch=True)
        return rows[0] if rows else None

    def recalculate_product_rating(
        self,
        product_id: int,
        *,
        conn: Optional[PgConnection] = None,
    ) -> None:
        agg_sql = f"""
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(AVG(rating), 0) AS average_rating,
                COUNT(*) FILTER (WHERE rating = 1) AS rating_1_count,
                COUNT(*) FILTER (WHERE rating = 2) AS rating_2_count,
                COUNT(*) FILTER (WHERE rating = 3) AS rating_3_count,
                COUNT(*) FILTER (WHERE rating = 4) AS rating_4_count,
                COUNT(*) FILTER (WHERE rating = 5) AS rating_5_count
            FROM {self.schema}.{self.table}
            WHERE product_id = %s
              AND is_deleted = FALSE
              AND is_active = TRUE
              AND is_approved = TRUE
        """
        agg = select_one(agg_sql, [product_id], conn=conn) or {}

        upsert_sql = f"""
            INSERT INTO {self.schema}.{self.rating_table}
                (product_id, total_reviews, average_rating,
                 rating_1_count, rating_2_count, rating_3_count,
                 rating_4_count, rating_5_count, last_calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (product_id) DO UPDATE SET
                total_reviews = EXCLUDED.total_reviews,
                average_rating = EXCLUDED.average_rating,
                rating_1_count = EXCLUDED.rating_1_count,
                rating_2_count = EXCLUDED.rating_2_count,
                rating_3_count = EXCLUDED.rating_3_count,
                rating_4_count = EXCLUDED.rating_4_count,
                rating_5_count = EXCLUDED.rating_5_count,
                last_calculated_at = NOW(),
                updated_at = NOW(),
                epoch = EXTRACT(EPOCH FROM NOW())
        """
        execute(
            upsert_sql,
            [
                product_id,
                int(agg.get("total_reviews") or 0),
                float(agg.get("average_rating") or 0),
                int(agg.get("rating_1_count") or 0),
                int(agg.get("rating_2_count") or 0),
                int(agg.get("rating_3_count") or 0),
                int(agg.get("rating_4_count") or 0),
                int(agg.get("rating_5_count") or 0),
            ],
            conn=conn,
        )


product_review_repository = ProductReviewRepository()
