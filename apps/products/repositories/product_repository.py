from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class ProductRepository:
    schema = "royal"
    table = "producttbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
        under_sub_category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "p.is_deleted = FALSE"
        if search:
            where += " AND (p.name ILIKE %s OR p.sku ILIKE %s OR p.slug ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if category_id:
            where += " AND p.category_id = %s"
            params.append(category_id)
        if sub_category_id:
            where += " AND p.sub_category_id = %s"
            params.append(sub_category_id)
        if under_sub_category_id:
            where += " AND p.under_sub_category_id = %s"
            params.append(under_sub_category_id)
        if brand_id:
            where += " AND p.brand_id = %s"
            params.append(brand_id)

        allowed_sort = {
            "name": "p.name",
            "sku": "p.sku",
            "base_price": "p.base_price",
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
            SELECT
                p.product_id,
                p.brand_id,
                p.category_id,
                p.sub_category_id,
                p.under_sub_category_id,
                p.name,
                p.slug,
                p.sku,
                p.short_description,
                p.base_price,
                p.sale_price,
                p.mrp,
                p.is_featured,
                p.is_new_arrival,
                p.is_best_seller,
                p.is_trending,
                p.is_active,
                p.created_at,
                p.updated_at,
                c.name AS category_name,
                sc.name AS sub_category_name,
                usc.name AS under_sub_category_name,
                b.name AS brand_name,
                (
                    SELECT pi.image_url
                    FROM {self.schema}.product_imagestbl pi
                    WHERE pi.product_id = p.product_id
                      AND pi.is_deleted = FALSE
                      AND pi.is_active = TRUE
                    ORDER BY pi.is_primary DESC, pi.display_order ASC
                    LIMIT 1
                ) AS primary_image_url
            FROM {self.schema}.{self.table} p
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = p.category_id
            LEFT JOIN {self.schema}.sub_categorytbl sc ON sc.sub_category_id = p.sub_category_id
            LEFT JOIN {self.schema}.under_sub_categorytbl usc
                ON usc.under_sub_category_id = p.under_sub_category_id
            LEFT JOIN {self.schema}.brandtbl b ON b.brand_id = p.brand_id
            WHERE {where}
            ORDER BY {order_col} {direction}, p.product_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, product_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                p.*,
                c.name AS category_name,
                sc.name AS sub_category_name,
                usc.name AS under_sub_category_name,
                b.name AS brand_name
            FROM {self.schema}.{self.table} p
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = p.category_id
            LEFT JOIN {self.schema}.sub_categorytbl sc ON sc.sub_category_id = p.sub_category_id
            LEFT JOIN {self.schema}.under_sub_categorytbl usc
                ON usc.under_sub_category_id = p.under_sub_category_id
            LEFT JOIN {self.schema}.brandtbl b ON b.brand_id = p.brand_id
            WHERE p.product_id = %s AND p.is_deleted = FALSE
        """
        return select_one(sql, [product_id])

    def slug_exists(self, slug: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT product_id FROM {self.schema}.{self.table}
            WHERE slug = %s AND is_deleted = FALSE
        """
        params: list[Any] = [slug]
        if exclude_id:
            sql += " AND product_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def sku_exists(self, sku: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT product_id FROM {self.schema}.{self.table}
            WHERE sku = %s AND is_deleted = FALSE
        """
        params: list[Any] = [sku]
        if exclude_id:
            sql += " AND product_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (brand_id, category_id, sub_category_id, under_sub_category_id,
                 name, slug, sku, hsn_code, barcode,
                 short_description, long_description, material, fabric, color,
                 dimensions, weight, assembly_required, warranty, country_of_origin,
                 base_price, sale_price, mrp, gst_percent,
                 seo_title, seo_description, seo_keywords,
                 is_featured, is_new_arrival, is_best_seller, is_trending, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING product_id
        """
        if conn is not None:
            rows = execute(sql, list(data.values()), conn=conn, fetch=True)
            product_id = rows[0]["product_id"]
            return self.fetch_by_id(product_id) or rows[0]
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(
        self,
        product_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(product_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE product_id = %s AND is_deleted = FALSE
            RETURNING product_id
        """
        params = [*data.values(), product_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(product_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(product_id) if rows else None

    def soft_delete(self, product_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE product_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [product_id]) > 0


product_repository = ProductRepository()
