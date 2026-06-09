from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_query
from core.database.raw_queries import execute


class WalletTransactionRepository:
    schema = "royal"
    table = "wallet_transactiontbl"

    def list_by_wallet(
        self,
        customer_wallet_id: int,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE customer_wallet_id = %s AND is_deleted = FALSE
            ORDER BY created_at DESC
            LIMIT %s
        """
        return select_query(sql, [customer_wallet_id, limit])

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (customer_wallet_id, customer_id, transaction_type, amount,
                 balance_before, balance_after, reference_type, reference_id, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, values)
        return row or {}


wallet_transaction_repository = WalletTransactionRepository()
