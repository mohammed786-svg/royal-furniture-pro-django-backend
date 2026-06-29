from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class OrderRepository:
    schema = "royal"
    table = "ordertbl"

    _SELECT_COLUMNS = """
        o.*,
        c.full_name AS customer_name,
        c.email AS customer_email,
        c.phone AS customer_phone,
        os.status_code,
        os.status_name,
        sa.address_line1 AS shipping_address_line1,
        sa.address_line2 AS shipping_address_line2,
        sa.city AS shipping_city,
        sa.state AS shipping_state,
        sa.pincode AS shipping_pincode,
        sa.full_name AS shipping_full_name,
        sa.phone AS shipping_phone,
        ba.address_line1 AS billing_address_line1,
        ba.address_line2 AS billing_address_line2,
        ba.city AS billing_city,
        ba.state AS billing_state,
        ba.pincode AS billing_pincode,
        ba.full_name AS billing_full_name,
        ba.phone AS billing_phone
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} o
        INNER JOIN {{schema}}.customertbl c ON c.customer_id = o.customer_id
        INNER JOIN {{schema}}.order_statustbl os ON os.order_status_id = o.order_status_id
        LEFT JOIN {{schema}}.addresstbl sa ON sa.address_id = o.shipping_address_id
        LEFT JOIN {{schema}}.addresstbl ba ON ba.address_id = o.billing_address_id
    """

    def _from_join(self) -> str:
        return self._FROM_JOIN.format(schema=self.schema, table=self.table)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        customer_id: Optional[int] = None,
        status_code: Optional[str] = None,
        current_status: Optional[str] = None,
        status_codes: Optional[list[str]] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "o.is_deleted = FALSE"
        if search:
            where += " AND (o.order_number ILIKE %s OR c.full_name ILIKE %s OR c.email ILIKE %s OR c.phone ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
        if customer_id:
            where += " AND o.customer_id = %s"
            params.append(customer_id)
        if status_code:
            where += " AND os.status_code = %s"
            params.append(status_code)
        if current_status:
            where += " AND o.current_status = %s"
            params.append(current_status)
        if status_codes:
            placeholders = ", ".join(["%s"] * len(status_codes))
            where += f" AND o.current_status IN ({placeholders})"
            params.extend(status_codes)

        allowed_sort = {
            "order_number": "o.order_number",
            "total_amount": "o.total_amount",
            "current_status": "o.current_status",
            "created_at": "o.created_at",
        }
        order_col = allowed_sort.get(sort_by, "o.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            {self._from_join()}
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_join()}
            WHERE {where}
            ORDER BY {order_col} {direction}, o.order_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, order_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_join()}
            WHERE o.order_id = %s AND o.is_deleted = FALSE
        """
        return select_one(sql, [order_id])

    def fetch_by_order_number(self, order_number: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_join()}
            WHERE UPPER(o.order_number) = UPPER(%s) AND o.is_deleted = FALSE
            ORDER BY o.order_id DESC
            LIMIT 1
        """
        return select_one(sql, [order_number])

    def count_orders_for_date_prefix(self, prefix: str, *, conn: Optional[PgConnection] = None) -> int:
        sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table}
            WHERE order_number LIKE %s AND is_deleted = FALSE
        """
        row = select_one(sql, [f"{prefix}%"], conn=conn)
        return int(row["total"]) if row else 0

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (order_number, customer_id, order_status_id, current_status,
                 subtotal, discount_amount, tax_amount, shipping_amount, total_amount,
                 coupon_id, coupon_code, shipping_address_id, billing_address_id,
                 payment_method, notes, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            order_id = int(rows[0]["order_id"])
            return self.fetch_by_id(order_id) or rows[0]
        row = insert_query_returning(sql, values)
        if row:
            return self.fetch_by_id(int(row["order_id"])) or row
        return {}

    def update(
        self,
        order_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(order_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE order_id = %s AND is_deleted = FALSE
            RETURNING order_id
        """
        params = [*data.values(), order_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(order_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(order_id) if rows else None

    def soft_delete(self, order_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE order_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [order_id]) > 0

    def fetch_shipments(self, order_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.shipmenttbl
            WHERE order_id = %s AND is_deleted = FALSE
            ORDER BY created_at DESC
        """
        return select_query(sql, [order_id])

    def fetch_shipment_tracking(self, order_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.shipment_trackingtbl
            WHERE order_id = %s AND is_deleted = FALSE
            ORDER BY tracked_at DESC
        """
        return select_query(sql, [order_id])


order_repository = OrderRepository()
