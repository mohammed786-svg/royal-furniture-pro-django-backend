from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query
from core.database.raw_queries import execute


class StockAdjustmentRepository:
    schema = "royal"
    table = "stock_adjustmenttbl"

    _SELECT_COLUMNS = """
        sa.stock_adjustment_id,
        sa.inventory_id,
        sa.warehouse_id,
        sa.adjustment_type,
        sa.quantity,
        sa.reason,
        sa.approved_by,
        sa.status,
        sa.adjusted_at,
        sa.created_at,
        sa.updated_at,
        i.product_id,
        i.product_variant_id,
        i.available_stock,
        p.name AS product_name,
        p.sku AS product_sku,
        pv.variant_name,
        pv.sku AS variant_sku,
        w.warehouse_code,
        w.name AS warehouse_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} sa
        INNER JOIN {{schema}}.inventorytbl i ON i.inventory_id = sa.inventory_id
        INNER JOIN {{schema}}.producttbl p ON p.product_id = i.product_id
        LEFT JOIN {{schema}}.product_varianttbl pv
            ON pv.product_variant_id = i.product_variant_id
        INNER JOIN {{schema}}.warehousetbl w ON w.warehouse_id = sa.warehouse_id
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
        warehouse_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "sa.is_deleted = FALSE"
        if search:
            where += " AND (p.name ILIKE %s OR p.sku ILIKE %s OR sa.reason ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if status:
            where += " AND sa.status = %s"
            params.append(status.upper())
        if warehouse_id:
            where += " AND sa.warehouse_id = %s"
            params.append(warehouse_id)

        allowed_sort = {
            "created_at": "sa.created_at",
            "status": "sa.status",
            "quantity": "sa.quantity",
            "adjusted_at": "sa.adjusted_at",
        }
        order_col = allowed_sort.get(sort_by, "sa.created_at")
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
            ORDER BY {order_col} {direction}, sa.stock_adjustment_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, adjustment_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE sa.stock_adjustment_id = %s AND sa.is_deleted = FALSE
        """
        return select_one(sql, [adjustment_id])

    def fetch_for_update(
        self,
        adjustment_id: int,
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE stock_adjustment_id = %s AND is_deleted = FALSE
            FOR UPDATE
        """
        return select_one(sql, [adjustment_id], conn=conn)

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (inventory_id, warehouse_id, adjustment_type,
                 quantity, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING stock_adjustment_id
        """
        if conn is not None:
            rows = execute(sql, list(data.values()), conn=conn, fetch=True)
            adjustment_id = rows[0]["stock_adjustment_id"]
            return self.fetch_by_id(adjustment_id) or rows[0]
        row = insert_query_returning(sql, list(data.values()))
        if row:
            return self.fetch_by_id(int(row["stock_adjustment_id"])) or row
        return {}

    def update(
        self,
        adjustment_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(adjustment_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE stock_adjustment_id = %s AND is_deleted = FALSE
            RETURNING stock_adjustment_id
        """
        params = [*data.values(), adjustment_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(adjustment_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(adjustment_id) if rows else None


stock_adjustment_repository = StockAdjustmentRepository()
