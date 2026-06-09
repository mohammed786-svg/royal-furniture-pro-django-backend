from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query
from core.database.raw_queries import execute


class StockTransferRepository:
    schema = "royal"
    table = "stock_transfertbl"

    _SELECT_COLUMNS = """
        st.stock_transfer_id,
        st.product_id,
        st.product_variant_id,
        st.from_warehouse_id,
        st.to_warehouse_id,
        st.quantity,
        st.status,
        st.initiated_by,
        st.completed_at,
        st.notes,
        st.created_at,
        st.updated_at,
        p.name AS product_name,
        p.sku AS product_sku,
        pv.variant_name,
        pv.sku AS variant_sku,
        fw.warehouse_code AS from_warehouse_code,
        fw.name AS from_warehouse_name,
        tw.warehouse_code AS to_warehouse_code,
        tw.name AS to_warehouse_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} st
        INNER JOIN {{schema}}.producttbl p ON p.product_id = st.product_id
        LEFT JOIN {{schema}}.product_varianttbl pv
            ON pv.product_variant_id = st.product_variant_id
        INNER JOIN {{schema}}.warehousetbl fw
            ON fw.warehouse_id = st.from_warehouse_id
        INNER JOIN {{schema}}.warehousetbl tw
            ON tw.warehouse_id = st.to_warehouse_id
    """

    def _from_clause(self) -> str:
        return self._FROM_JOIN.format(schema=self.schema, table=self.table)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        status: str = "",
        from_warehouse_id: Optional[int] = None,
        to_warehouse_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "st.is_deleted = FALSE"
        if search:
            where += " AND (p.name ILIKE %s OR p.sku ILIKE %s OR st.notes ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if status:
            where += " AND st.status = %s"
            params.append(status.upper())
        if from_warehouse_id:
            where += " AND st.from_warehouse_id = %s"
            params.append(from_warehouse_id)
        if to_warehouse_id:
            where += " AND st.to_warehouse_id = %s"
            params.append(to_warehouse_id)

        allowed_sort = {
            "created_at": "st.created_at",
            "status": "st.status",
            "quantity": "st.quantity",
            "completed_at": "st.completed_at",
        }
        order_col = allowed_sort.get(sort_by, "st.created_at")
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
            ORDER BY {order_col} {direction}, st.stock_transfer_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, transfer_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE st.stock_transfer_id = %s AND st.is_deleted = FALSE
        """
        return select_one(sql, [transfer_id])

    def fetch_for_update(
        self,
        transfer_id: int,
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE stock_transfer_id = %s AND is_deleted = FALSE
            FOR UPDATE
        """
        return select_one(sql, [transfer_id], conn=conn)

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (product_id, product_variant_id, from_warehouse_id,
                 to_warehouse_id, quantity, status, initiated_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING stock_transfer_id
        """
        if conn is not None:
            rows = execute(sql, list(data.values()), conn=conn, fetch=True)
            transfer_id = rows[0]["stock_transfer_id"]
            return self.fetch_by_id(transfer_id) or rows[0]
        row = insert_query_returning(sql, list(data.values()))
        if row:
            return self.fetch_by_id(int(row["stock_transfer_id"])) or row
        return {}

    def update(
        self,
        transfer_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(transfer_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE stock_transfer_id = %s AND is_deleted = FALSE
            RETURNING stock_transfer_id
        """
        params = [*data.values(), transfer_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(transfer_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(transfer_id) if rows else None


stock_transfer_repository = StockTransferRepository()
