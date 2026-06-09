from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class OrderItemRepository:
    schema = "royal"
    table = "order_itemtbl"

    def list_by_order(self, order_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                oi.*,
                p.gst_percent AS product_gst_percent
            FROM {self.schema}.{self.table} oi
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = oi.product_id
            WHERE oi.order_id = %s AND oi.is_deleted = FALSE
            ORDER BY oi.order_item_id ASC
        """
        return select_query(sql, [order_id])

    def fetch_by_id(self, order_item_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE order_item_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [order_item_id])

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (order_id, product_id, product_variant_id, product_name, sku,
                 quantity, unit_price, discount_amount, tax_amount, line_total,
                 hsn_code, warehouse_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, values)
        return row or {}

    def create_many(
        self,
        items: list[dict[str, Any]],
        *,
        conn: Optional[PgConnection] = None,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for item in items:
            created.append(self.create(item, conn=conn))
        return created

    def soft_delete_by_order(self, order_id: int, *, conn: Optional[PgConnection] = None) -> None:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE order_id = %s AND is_deleted = FALSE
        """
        if conn is not None:
            execute(sql, [order_id], conn=conn, fetch=False)
        else:
            update_query(sql, [order_id])


order_item_repository = OrderItemRepository()
