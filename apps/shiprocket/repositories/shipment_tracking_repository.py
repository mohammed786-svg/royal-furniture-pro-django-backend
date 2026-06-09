from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class ShipmentTrackingRepository:
    schema = "royal"
    table = "shipment_trackingtbl"

    _SELECT_COLUMNS = """
        st.shipment_tracking_id,
        st.shipment_id,
        st.order_id,
        st.status_code,
        st.status_message,
        st.location,
        st.tracked_at,
        st.source,
        st.raw_payload,
        st.created_at,
        st.updated_at,
        o.order_number,
        s.awb_number,
        c.full_name AS customer_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} st
        INNER JOIN {{schema}}.ordertbl o ON o.order_id = st.order_id
        INNER JOIN {{schema}}.customertbl c ON c.customer_id = o.customer_id
        LEFT JOIN {{schema}}.shipmenttbl s ON s.shipment_id = st.shipment_id
    """

    def _from_clause(self) -> str:
        return self._FROM_JOIN.format(schema=self.schema, table=self.table)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        shipment_id: Optional[int] = None,
        order_id: Optional[int] = None,
        sort_by: str = "tracked_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "st.is_deleted = FALSE AND o.is_deleted = FALSE"
        if search:
            where += """
                AND (
                    o.order_number ILIKE %s
                    OR st.status_message ILIKE %s
                    OR st.location ILIKE %s
                )
            """
            term = f"%{search}%"
            params.extend([term, term, term])
        if shipment_id:
            where += " AND st.shipment_id = %s"
            params.append(shipment_id)
        if order_id:
            where += " AND st.order_id = %s"
            params.append(order_id)

        allowed_sort = {
            "tracked_at": "st.tracked_at",
            "created_at": "st.created_at",
            "status_code": "st.status_code",
        }
        order_col = allowed_sort.get(sort_by, "st.tracked_at")
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
            ORDER BY {order_col} {direction}, st.shipment_tracking_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, tracking_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE st.shipment_tracking_id = %s AND st.is_deleted = FALSE
        """
        return select_one(sql, [tracking_id])

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (shipment_id, order_id, status_code, status_message,
                 location, tracked_at, source, raw_payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING shipment_tracking_id
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            tracking_id = rows[0]["shipment_tracking_id"]
            return self.fetch_by_id(tracking_id) or rows[0]
        row = insert_query_returning(sql, values)
        if row:
            return self.fetch_by_id(int(row["shipment_tracking_id"])) or row
        return {}

    def update(
        self,
        tracking_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(tracking_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE shipment_tracking_id = %s AND is_deleted = FALSE
            RETURNING shipment_tracking_id
        """
        params = [*data.values(), tracking_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(tracking_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(tracking_id) if rows else None

    def soft_delete(self, tracking_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, updated_at = NOW()
            WHERE shipment_tracking_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [tracking_id]) > 0


shipment_tracking_repository = ShipmentTrackingRepository()
