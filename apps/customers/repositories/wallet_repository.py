from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class WalletRepository:
    schema = "royal"
    table = "customer_wallettbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "w.is_deleted = FALSE"
        if search:
            where += " AND (c.full_name ILIKE %s OR c.email ILIKE %s OR c.phone ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        allowed_sort = {
            "balance": "w.balance",
            "created_at": "w.created_at",
            "customer_name": "c.full_name",
        }
        order_col = allowed_sort.get(sort_by, "w.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} w
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = w.customer_id
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT w.*, c.full_name AS customer_name, c.email AS customer_email, c.phone AS customer_phone
            FROM {self.schema}.{self.table} w
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = w.customer_id
            WHERE {where}
            ORDER BY {order_col} {direction}, w.customer_wallet_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, customer_wallet_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT w.*, c.full_name AS customer_name, c.email AS customer_email, c.phone AS customer_phone
            FROM {self.schema}.{self.table} w
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = w.customer_id
            WHERE w.customer_wallet_id = %s AND w.is_deleted = FALSE
        """
        return select_one(sql, [customer_wallet_id])

    def fetch_by_customer(self, customer_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE customer_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [customer_id])

    def fetch_for_update(
        self,
        customer_wallet_id: int,
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE customer_wallet_id = %s AND is_deleted = FALSE
            FOR UPDATE
        """
        return select_one(sql, [customer_wallet_id], conn=conn)

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (customer_id, balance, currency, is_active)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, values)
        return row or {}

    def update_balance(
        self,
        customer_wallet_id: int,
        balance: float,
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET balance = %s, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE customer_wallet_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [balance, customer_wallet_id], conn=conn, fetch=True)
        return rows[0] if rows else None


wallet_repository = WalletRepository()
