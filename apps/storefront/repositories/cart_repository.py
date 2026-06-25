from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import select_one, select_query
from core.database.raw_queries import execute


class CartRepository:
    schema = "royal"

    def fetch_active_cart(
        self,
        *,
        customer_id: Optional[int] = None,
        session_id: Optional[str] = None,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        params: list[Any] = []
        if customer_id:
            sql = f"""
                SELECT *
                FROM {self.schema}.carttbl
                WHERE customer_id = %s
                  AND is_active = TRUE
                  AND is_deleted = FALSE
                ORDER BY updated_at DESC
                LIMIT 1
            """
            params = [customer_id]
        elif session_id:
            sql = f"""
                SELECT *
                FROM {self.schema}.carttbl
                WHERE session_id = %s
                  AND is_guest = TRUE
                  AND is_active = TRUE
                  AND is_deleted = FALSE
                ORDER BY updated_at DESC
                LIMIT 1
            """
            params = [session_id]
        else:
            return None
        return select_one(sql, params, conn=conn)

    def create_cart(
        self,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.carttbl
                (customer_id, session_id, is_guest, subtotal, discount_amount,
                 tax_amount, total_amount, item_count, last_activity_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)
            RETURNING *
        """
        rows = execute(sql, list(data.values()), conn=conn, fetch=True)
        return rows[0] if rows else {}

    def update_cart(
        self,
        cart_id: int,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> None:
        if not data:
            return
        sets = ", ".join(f"{col} = %s" for col in data)
        sql = f"""
            UPDATE {self.schema}.carttbl
            SET {sets}, updated_at = NOW(), last_activity_at = NOW(),
                epoch = EXTRACT(EPOCH FROM NOW())
            WHERE cart_id = %s AND is_deleted = FALSE
        """
        execute(sql, [*data.values(), cart_id], conn=conn, fetch=False)

    def list_items(self, cart_id: int, *, conn: Optional[PgConnection] = None) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                ci.*,
                p.name AS product_name,
                p.slug AS product_slug,
                p.sale_price AS product_sale_price,
                p.base_price AS product_base_price,
                p.mrp AS product_mrp,
                (
                    SELECT pi.image_url
                    FROM {self.schema}.product_imagestbl pi
                    WHERE pi.product_id = p.product_id
                      AND pi.is_deleted = FALSE
                      AND pi.is_active = TRUE
                    ORDER BY pi.is_primary DESC, pi.display_order ASC
                    LIMIT 1
                ) AS product_image_url
            FROM {self.schema}.cart_itemtbl ci
            INNER JOIN {self.schema}.producttbl p ON p.product_id = ci.product_id
            WHERE ci.cart_id = %s
              AND ci.is_deleted = FALSE
              AND ci.is_active = TRUE
              AND p.is_deleted = FALSE
            ORDER BY ci.cart_item_id ASC
        """
        return select_query(sql, [cart_id], conn=conn)

    def fetch_item(self, cart_item_id: int, *, conn: Optional[PgConnection] = None) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.cart_itemtbl
            WHERE cart_item_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [cart_item_id], conn=conn)

    def fetch_item_by_product(
        self,
        cart_id: int,
        product_id: int,
        product_variant_id: Optional[int],
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        if product_variant_id is None:
            sql = f"""
                SELECT *
                FROM {self.schema}.cart_itemtbl
                WHERE cart_id = %s
                  AND product_id = %s
                  AND product_variant_id IS NULL
                  AND is_deleted = FALSE
            """
            params: list[Any] = [cart_id, product_id]
        else:
            sql = f"""
                SELECT *
                FROM {self.schema}.cart_itemtbl
                WHERE cart_id = %s
                  AND product_id = %s
                  AND product_variant_id = %s
                  AND is_deleted = FALSE
            """
            params = [cart_id, product_id, product_variant_id]
        return select_one(sql, params, conn=conn)

    def add_item(
        self,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.cart_itemtbl
                (cart_id, product_id, product_variant_id, quantity, unit_price, line_total, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            RETURNING *
        """
        rows = execute(sql, list(data.values()), conn=conn, fetch=True)
        return rows[0] if rows else {}

    def update_item(
        self,
        cart_item_id: int,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> None:
        if not data:
            return
        sets = ", ".join(f"{col} = %s" for col in data)
        sql = f"""
            UPDATE {self.schema}.cart_itemtbl
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE cart_item_id = %s AND is_deleted = FALSE
        """
        execute(sql, [*data.values(), cart_item_id], conn=conn, fetch=False)

    def soft_delete_item(self, cart_item_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.cart_itemtbl
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE cart_item_id = %s
        """
        execute(sql, [cart_item_id], conn=conn, fetch=False)

    def clear_items(self, cart_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.cart_itemtbl
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE cart_id = %s AND is_deleted = FALSE
        """
        execute(sql, [cart_id], conn=conn, fetch=False)

    def deactivate_cart(self, cart_id: int, *, conn: PgConnection) -> None:
        sql = f"""
            UPDATE {self.schema}.carttbl
            SET is_active = FALSE, updated_at = NOW()
            WHERE cart_id = %s
        """
        execute(sql, [cart_id], conn=conn, fetch=False)


cart_repository = CartRepository()
