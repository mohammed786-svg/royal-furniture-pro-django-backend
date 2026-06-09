from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database.raw_queries import execute


class InventoryLogRepository:
    schema = "royal"

    def insert_stock_log(
        self,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.stock_logtbl
                (inventory_id, product_id, warehouse_id,
                 action_type, quantity_before, quantity_after,
                 quantity_changed, reason, reference_type,
                 reference_id, performed_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        rows = execute(sql, list(data.values()), conn=conn, fetch=True)
        return rows[0] if rows else {}

    def insert_inventory_transaction(
        self,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.inventory_transactiontbl
                (inventory_id, product_id, product_variant_id, warehouse_id,
                 transaction_type, quantity, reference_type,
                 reference_id, notes, performed_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        rows = execute(sql, list(data.values()), conn=conn, fetch=True)
        return rows[0] if rows else {}


inventory_log_repository = InventoryLogRepository()
