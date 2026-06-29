from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from apps.inventory.repositories.inventory_log_repository import inventory_log_repository
from apps.inventory.repositories.inventory_repository import inventory_repository
from apps.orders.repositories.order_item_repository import order_item_repository
from core.database import select_query
from core.database import select_one
from core.exceptions.base import ValidationException


class InventoryStockService:
    schema = "royal"

    def fetch_primary_inventory(
        self,
        *,
        product_id: int,
        product_variant_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        params: list[Any] = [product_id]
        where = "product_id = %s AND is_deleted = FALSE AND is_active = TRUE"
        if product_variant_id is not None:
            where += " AND product_variant_id = %s"
            params.append(product_variant_id)
        if warehouse_id:
            where += " AND warehouse_id = %s"
            params.append(warehouse_id)

        sql = f"""
            SELECT *
            FROM {self.schema}.inventorytbl
            WHERE {where}
            ORDER BY available_stock DESC, inventory_id ASC
            LIMIT 1
            FOR UPDATE
        """
        row = select_one(sql, params, conn=conn)
        return row

    def get_available_stock(
        self,
        *,
        product_id: int,
        product_variant_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        conn: Optional[PgConnection] = None,
    ) -> int:
        params: list[Any] = [product_id]
        where = "product_id = %s AND is_deleted = FALSE AND is_active = TRUE"
        if product_variant_id is not None:
            where += " AND product_variant_id = %s"
            params.append(product_variant_id)
        if warehouse_id:
            where += " AND warehouse_id = %s"
            params.append(warehouse_id)

        sql = f"""
            SELECT COALESCE(SUM(available_stock), 0) AS stock
            FROM {self.schema}.inventorytbl
            WHERE {where}
        """
        row = select_one(sql, params, conn=conn)
        return int(row["stock"]) if row else 0

    def _apply_stock_change(
        self,
        *,
        inventory_row: dict[str, Any],
        quantity: int,
        action_type: str,
        transaction_type: str,
        reference_type: str,
        reference_id: int,
        reason: str,
        performed_by: Optional[int],
        conn: PgConnection,
    ) -> None:
        inventory_id = int(inventory_row["inventory_id"])
        before = int(inventory_row.get("available_stock") or 0)
        sold = int(inventory_row.get("sold_stock") or 0)
        after = before - quantity
        if after < 0:
            raise ValidationException(
                details=[{"field": "quantity", "message": "Insufficient stock for this product"}]
            )

        inventory_repository.update_stock_levels(
            inventory_id,
            {
                "available_stock": after,
                "sold_stock": sold + quantity,
                "warehouse_stock": after,
            },
            conn=conn,
        )

        product_id = int(inventory_row["product_id"])
        warehouse_id = int(inventory_row["warehouse_id"])
        variant_id = inventory_row.get("product_variant_id")

        inventory_log_repository.insert_stock_log(
            {
                "inventory_id": inventory_id,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "action_type": action_type,
                "quantity_before": before,
                "quantity_after": after,
                "quantity_changed": -quantity,
                "reason": reason,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "performed_by": performed_by,
            },
            conn=conn,
        )
        inventory_log_repository.insert_inventory_transaction(
            {
                "inventory_id": inventory_id,
                "product_id": product_id,
                "product_variant_id": variant_id,
                "warehouse_id": warehouse_id,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "notes": reason,
                "performed_by": performed_by,
            },
            conn=conn,
        )

    def deduct_for_order_item(
        self,
        *,
        product_id: int,
        product_variant_id: Optional[int],
        warehouse_id: Optional[int],
        quantity: int,
        order_id: int,
        performed_by: Optional[int],
        conn: PgConnection,
    ) -> int:
        row = self.fetch_primary_inventory(
            product_id=product_id,
            product_variant_id=product_variant_id,
            warehouse_id=warehouse_id,
            conn=conn,
        )
        if not row:
            raise ValidationException(
                details=[
                    {
                        "field": "productId",
                        "message": (
                            f"No active inventory for product {product_id}"
                            + (f" variant {product_variant_id}" if product_variant_id else "")
                        ),
                    }
                ]
            )
        if int(row.get("available_stock") or 0) < quantity:
            raise ValidationException(
                details=[{"field": "quantity", "message": "Insufficient stock for one or more items"}]
            )

        self._apply_stock_change(
            inventory_row=row,
            quantity=quantity,
            action_type="SALE",
            transaction_type="ORDER_SALE",
            reference_type="ORDER",
            reference_id=order_id,
            reason=f"Stock deducted for order #{order_id}",
            performed_by=performed_by,
            conn=conn,
        )
        return int(row["warehouse_id"])

    def restore_for_order(
        self,
        order_id: int,
        *,
        performed_by: Optional[int],
        conn: PgConnection,
    ) -> None:
        existing = select_query(
            f"""
            SELECT inventory_transaction_id
            FROM {self.schema}.inventory_transactiontbl
            WHERE reference_type = 'ORDER'
              AND reference_id = %s
              AND transaction_type = 'ORDER_CANCEL'
              AND is_deleted = FALSE
            LIMIT 1
            """,
            [order_id],
            conn=conn,
        )
        if existing:
            return

        sale_rows = select_query(
            f"""
            SELECT *
            FROM {self.schema}.inventory_transactiontbl
            WHERE reference_type = 'ORDER'
              AND reference_id = %s
              AND transaction_type = 'ORDER_SALE'
              AND is_deleted = FALSE
            """,
            [order_id],
            conn=conn,
        )
        if not sale_rows:
            items = order_item_repository.list_by_order(order_id)
            for item in items:
                self._restore_item(
                    product_id=int(item["product_id"]),
                    product_variant_id=item.get("product_variant_id"),
                    warehouse_id=item.get("warehouse_id"),
                    quantity=int(item["quantity"]),
                    order_id=order_id,
                    performed_by=performed_by,
                    conn=conn,
                )
            return

        for sale in sale_rows:
            self._restore_item(
                product_id=int(sale["product_id"]),
                product_variant_id=sale.get("product_variant_id"),
                warehouse_id=int(sale["warehouse_id"]),
                quantity=int(sale["quantity"]),
                order_id=order_id,
                performed_by=performed_by,
                conn=conn,
            )

    def _restore_item(
        self,
        *,
        product_id: int,
        product_variant_id: Optional[int],
        warehouse_id: Optional[int],
        quantity: int,
        order_id: int,
        performed_by: Optional[int],
        conn: PgConnection,
    ) -> None:
        wh_id = int(warehouse_id) if warehouse_id else None
        row = self.fetch_primary_inventory(
            product_id=product_id,
            product_variant_id=int(product_variant_id) if product_variant_id else None,
            warehouse_id=wh_id,
            conn=conn,
        )
        if not row:
            return

        inventory_id = int(row["inventory_id"])
        before = int(row.get("available_stock") or 0)
        sold = int(row.get("sold_stock") or 0)
        after = before + quantity
        sold_after = max(0, sold - quantity)

        inventory_repository.update_stock_levels(
            inventory_id,
            {
                "available_stock": after,
                "sold_stock": sold_after,
                "warehouse_stock": after,
            },
            conn=conn,
        )

        inventory_log_repository.insert_stock_log(
            {
                "inventory_id": inventory_id,
                "product_id": product_id,
                "warehouse_id": int(row["warehouse_id"]),
                "action_type": "RESTOCK",
                "quantity_before": before,
                "quantity_after": after,
                "quantity_changed": quantity,
                "reason": f"Stock restored for cancelled order #{order_id}",
                "reference_type": "ORDER",
                "reference_id": order_id,
                "performed_by": performed_by,
            },
            conn=conn,
        )
        inventory_log_repository.insert_inventory_transaction(
            {
                "inventory_id": inventory_id,
                "product_id": product_id,
                "product_variant_id": row.get("product_variant_id"),
                "warehouse_id": int(row["warehouse_id"]),
                "transaction_type": "ORDER_CANCEL",
                "quantity": quantity,
                "reference_type": "ORDER",
                "reference_id": order_id,
                "notes": f"Restocked from cancelled order #{order_id}",
                "performed_by": performed_by,
            },
            conn=conn,
        )


inventory_stock_service = InventoryStockService()
