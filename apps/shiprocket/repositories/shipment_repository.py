from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class ShipmentRepository:
    schema = "royal"
    table = "shipmenttbl"

    _SELECT_COLUMNS = """
        s.shipment_id,
        s.order_id,
        s.shiprocket_order_id,
        s.shipment_id_external,
        s.awb_number,
        s.courier_name,
        s.tracking_number,
        s.pickup_status,
        s.delivery_status,
        s.shipping_label_url,
        s.estimated_delivery_date,
        s.shipped_at,
        s.delivered_at,
        s.raw_response,
        s.created_at,
        s.updated_at,
        o.order_number,
        c.full_name AS customer_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} s
        INNER JOIN {{schema}}.ordertbl o ON o.order_id = s.order_id
        INNER JOIN {{schema}}.customertbl c ON c.customer_id = o.customer_id
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
        delivery_status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "s.is_deleted = FALSE AND o.is_deleted = FALSE"
        if search:
            where += """
                AND (
                    o.order_number ILIKE %s
                    OR c.full_name ILIKE %s
                    OR s.awb_number ILIKE %s
                    OR s.tracking_number ILIKE %s
                )
            """
            term = f"%{search}%"
            params.extend([term, term, term, term])
        if order_id:
            where += " AND s.order_id = %s"
            params.append(order_id)
        if delivery_status:
            where += " AND s.delivery_status = %s"
            params.append(delivery_status.upper())

        allowed_sort = {
            "created_at": "s.created_at",
            "shipped_at": "s.shipped_at",
            "delivered_at": "s.delivered_at",
            "delivery_status": "s.delivery_status",
            "order_number": "o.order_number",
        }
        order_col = allowed_sort.get(sort_by, "s.created_at")
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
            ORDER BY {order_col} {direction}, s.shipment_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_order_id(self, order_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE s.order_id = %s AND s.is_deleted = FALSE
            ORDER BY s.shipment_id DESC
            LIMIT 1
        """
        return select_one(sql, [order_id])

    def fetch_by_shiprocket_order_id(self, shiprocket_order_id: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE s.shiprocket_order_id = %s AND s.is_deleted = FALSE
            ORDER BY s.shipment_id DESC
            LIMIT 1
        """
        return select_one(sql, [shiprocket_order_id])

    def fetch_by_awb(self, awb_number: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE s.awb_number = %s AND s.is_deleted = FALSE
            ORDER BY s.shipment_id DESC
            LIMIT 1
        """
        return select_one(sql, [awb_number])

    def fetch_by_id(self, shipment_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE s.shipment_id = %s AND s.is_deleted = FALSE
        """
        return select_one(sql, [shipment_id])

    def list_options(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                s.shipment_id,
                s.order_id,
                s.awb_number,
                s.tracking_number,
                s.delivery_status,
                o.order_number
            FROM {self.schema}.{self.table} s
            INNER JOIN {self.schema}.ordertbl o ON o.order_id = s.order_id
            WHERE s.is_deleted = FALSE AND o.is_deleted = FALSE
            ORDER BY s.created_at DESC
            LIMIT 500
        """
        return select_query(sql)

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (order_id, shiprocket_order_id, shipment_id_external, awb_number,
                 courier_name, tracking_number, pickup_status, delivery_status,
                 shipping_label_url, estimated_delivery_date, shipped_at,
                 delivered_at, raw_response)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING shipment_id
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            shipment_id = rows[0]["shipment_id"]
            return self.fetch_by_id(shipment_id) or rows[0]
        row = insert_query_returning(sql, values)
        if row:
            return self.fetch_by_id(int(row["shipment_id"])) or row
        return {}

    def update(
        self,
        shipment_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(shipment_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE shipment_id = %s AND is_deleted = FALSE
            RETURNING shipment_id
        """
        params = [*data.values(), shipment_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(shipment_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(shipment_id) if rows else None

    def soft_delete(self, shipment_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE shipment_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [shipment_id]) > 0


shipment_repository = ShipmentRepository()
