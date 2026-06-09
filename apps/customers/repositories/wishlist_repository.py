from __future__ import annotations

from typing import Any, Optional

from core.database import select_one, select_query, update_query


class WishlistRepository:
    schema = "royal"
    table = "wishlisttbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        customer_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "w.is_deleted = FALSE"
        if search:
            where += " AND (p.name ILIKE %s OR p.sku ILIKE %s OR c.full_name ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if customer_id:
            where += " AND w.customer_id = %s"
            params.append(customer_id)

        allowed_sort = {
            "created_at": "w.created_at",
            "product_name": "p.name",
        }
        order_col = allowed_sort.get(sort_by, "w.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} w
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = w.customer_id
            INNER JOIN {self.schema}.producttbl p ON p.product_id = w.product_id
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                w.*,
                p.name AS product_name,
                p.sku AS product_sku,
                p.sale_price AS product_sale_price,
                c.full_name AS customer_name,
                (
                    SELECT pi.image_url
                    FROM {self.schema}.product_imagestbl pi
                    WHERE pi.product_id = p.product_id
                      AND pi.is_deleted = FALSE
                      AND pi.is_active = TRUE
                    ORDER BY pi.is_primary DESC, pi.display_order ASC
                    LIMIT 1
                ) AS product_image_url
            FROM {self.schema}.{self.table} w
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = w.customer_id
            INNER JOIN {self.schema}.producttbl p ON p.product_id = w.product_id
            WHERE {where}
            ORDER BY {order_col} {direction}, w.wishlist_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, wishlist_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT w.*, p.name AS product_name
            FROM {self.schema}.{self.table} w
            INNER JOIN {self.schema}.producttbl p ON p.product_id = w.product_id
            WHERE w.wishlist_id = %s AND w.is_deleted = FALSE
        """
        return select_one(sql, [wishlist_id])

    def soft_delete(self, wishlist_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE wishlist_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [wishlist_id]) > 0


wishlist_repository = WishlistRepository()
