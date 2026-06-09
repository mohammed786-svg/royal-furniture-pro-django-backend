from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class PaymentVerificationRepository:
    schema = "royal"
    table = "payment_verificationtbl"

    _SELECT_COLUMNS = """
        pv.payment_verification_id,
        pv.payment_id,
        pv.order_id,
        pv.utr_number,
        pv.payment_amount,
        pv.screenshot_url,
        pv.verification_status,
        pv.verified_by,
        pv.verification_time,
        pv.remarks,
        pv.created_at,
        pv.updated_at,
        o.order_number,
        c.full_name AS customer_name,
        u.full_name AS verified_by_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} pv
        INNER JOIN {{schema}}.ordertbl o ON o.order_id = pv.order_id
        INNER JOIN {{schema}}.customertbl c ON c.customer_id = o.customer_id
        LEFT JOIN {{schema}}.usertbl u ON u.user_id = pv.verified_by
    """

    def _from_clause(self) -> str:
        return self._FROM_JOIN.format(schema=self.schema, table=self.table)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        payment_id: Optional[int] = None,
        order_id: Optional[int] = None,
        verification_status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "pv.is_deleted = FALSE AND o.is_deleted = FALSE"
        if search:
            where += """
                AND (
                    o.order_number ILIKE %s
                    OR c.full_name ILIKE %s
                    OR pv.utr_number ILIKE %s
                )
            """
            term = f"%{search}%"
            params.extend([term, term, term])
        if payment_id:
            where += " AND pv.payment_id = %s"
            params.append(payment_id)
        if order_id:
            where += " AND pv.order_id = %s"
            params.append(order_id)
        if verification_status:
            where += " AND pv.verification_status = %s"
            params.append(verification_status.upper())

        allowed_sort = {
            "created_at": "pv.created_at",
            "verification_time": "pv.verification_time",
            "verification_status": "pv.verification_status",
            "order_number": "o.order_number",
        }
        order_col = allowed_sort.get(sort_by, "pv.created_at")
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
            ORDER BY {order_col} {direction}, pv.payment_verification_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, verification_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE pv.payment_verification_id = %s AND pv.is_deleted = FALSE
        """
        return select_one(sql, [verification_id])

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (payment_id, order_id, utr_number, payment_amount,
                 screenshot_url, verification_status, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING payment_verification_id
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            verification_id = rows[0]["payment_verification_id"]
            return self.fetch_by_id(verification_id) or rows[0]
        row = insert_query_returning(sql, values)
        if row:
            return self.fetch_by_id(int(row["payment_verification_id"])) or row
        return {}

    def update(
        self,
        verification_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(verification_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE payment_verification_id = %s AND is_deleted = FALSE
            RETURNING payment_verification_id
        """
        params = [*data.values(), verification_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(verification_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(verification_id) if rows else None

    def soft_delete(self, verification_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE payment_verification_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [verification_id]) > 0


payment_verification_repository = PaymentVerificationRepository()
