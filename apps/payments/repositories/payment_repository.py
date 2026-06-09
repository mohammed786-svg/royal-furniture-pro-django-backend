from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class PaymentRepository:
    schema = "royal"
    table = "paymenttbl"

    _SELECT_COLUMNS = """
        p.payment_id,
        p.order_id,
        p.customer_id,
        p.payment_method,
        p.payment_amount,
        p.currency,
        p.payment_status,
        p.transaction_ref,
        p.paid_at,
        p.created_at,
        p.updated_at,
        o.order_number,
        c.full_name AS customer_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} p
        INNER JOIN {{schema}}.ordertbl o ON o.order_id = p.order_id
        INNER JOIN {{schema}}.customertbl c ON c.customer_id = p.customer_id
    """

    def _from_clause(self) -> str:
        return self._FROM_JOIN.format(schema=self.schema, table=self.table)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        order_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        payment_status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "p.is_deleted = FALSE AND o.is_deleted = FALSE"
        if search:
            where += """
                AND (
                    o.order_number ILIKE %s
                    OR c.full_name ILIKE %s
                    OR p.transaction_ref ILIKE %s
                )
            """
            term = f"%{search}%"
            params.extend([term, term, term])
        if order_id:
            where += " AND p.order_id = %s"
            params.append(order_id)
        if customer_id:
            where += " AND p.customer_id = %s"
            params.append(customer_id)
        if payment_status:
            where += " AND p.payment_status = %s"
            params.append(payment_status.upper())

        allowed_sort = {
            "created_at": "p.created_at",
            "paid_at": "p.paid_at",
            "payment_amount": "p.payment_amount",
            "payment_status": "p.payment_status",
            "order_number": "o.order_number",
        }
        order_col = allowed_sort.get(sort_by, "p.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            {self._from_clause()}
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE {where}
            ORDER BY {order_col} {direction}, p.payment_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def list_by_order(self, order_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE order_id = %s AND is_deleted = FALSE
            ORDER BY created_at DESC
        """
        return select_query(sql, [order_id])

    def fetch_by_id(self, payment_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE p.payment_id = %s AND p.is_deleted = FALSE
        """
        return select_one(sql, [payment_id])

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (order_id, customer_id, payment_method, payment_amount, currency,
                 payment_status, transaction_ref, paid_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING payment_id
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            payment_id = rows[0]["payment_id"]
            return self.fetch_by_id(payment_id) or rows[0]
        row = insert_query_returning(sql, values)
        if row:
            return self.fetch_by_id(int(row["payment_id"])) or row
        return {}

    def update(
        self,
        payment_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(payment_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE payment_id = %s AND is_deleted = FALSE
            RETURNING payment_id
        """
        params = [*data.values(), payment_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(payment_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(payment_id) if rows else None

    def soft_delete(self, payment_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE payment_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [payment_id]) > 0


payment_repository = PaymentRepository()
