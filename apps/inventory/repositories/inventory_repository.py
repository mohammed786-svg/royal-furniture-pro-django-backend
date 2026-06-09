from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class InventoryRepository:
    schema = "royal"
    table = "inventorytbl"

    _SELECT_COLUMNS = """
        i.inventory_id,
        i.product_id,
        i.product_variant_id,
        i.warehouse_id,
        i.available_stock,
        i.reserved_stock,
        i.sold_stock,
        i.damaged_stock,
        i.returned_stock,
        i.warehouse_stock,
        i.reorder_level,
        i.last_restocked_at,
        i.is_active,
        i.created_at,
        i.updated_at,
        p.name AS product_name,
        p.sku AS product_sku,
        pv.variant_name,
        pv.sku AS variant_sku,
        w.warehouse_code,
        w.name AS warehouse_name
    """

    _FROM_JOIN = f"""
        FROM {{schema}}.{{table}} i
        INNER JOIN {{schema}}.producttbl p ON p.product_id = i.product_id
        LEFT JOIN {{schema}}.product_varianttbl pv
            ON pv.product_variant_id = i.product_variant_id
        INNER JOIN {{schema}}.warehousetbl w ON w.warehouse_id = i.warehouse_id
    """

    def _from_clause(self) -> str:
        return self._FROM_JOIN.format(schema=self.schema, table=self.table)

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "i.is_deleted = FALSE AND p.is_deleted = FALSE AND w.is_deleted = FALSE"
        if search:
            where += """
                AND (
                    p.name ILIKE %s OR p.sku ILIKE %s
                    OR pv.sku ILIKE %s OR w.name ILIKE %s
                )
            """
            term = f"%{search}%"
            params.extend([term, term, term, term])
        if warehouse_id:
            where += " AND i.warehouse_id = %s"
            params.append(warehouse_id)
        if product_id:
            where += " AND i.product_id = %s"
            params.append(product_id)

        allowed_sort = {
            "product_name": "p.name",
            "warehouse_name": "w.name",
            "available_stock": "i.available_stock",
            "warehouse_stock": "i.warehouse_stock",
            "created_at": "i.created_at",
        }
        order_col = allowed_sort.get(sort_by, "i.created_at")
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
            ORDER BY {order_col} {direction}, i.inventory_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, inventory_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT {self._SELECT_COLUMNS}
            {self._from_clause()}
            WHERE i.inventory_id = %s AND i.is_deleted = FALSE
        """
        return select_one(sql, [inventory_id])

    def fetch_by_product_warehouse(
        self,
        *,
        product_id: int,
        warehouse_id: int,
        product_variant_id: Optional[int] = None,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if product_variant_id is None:
            sql = f"""
                SELECT *
                FROM {self.schema}.{self.table}
                WHERE product_id = %s
                  AND product_variant_id IS NULL
                  AND warehouse_id = %s
                  AND is_deleted = FALSE
            """
            params: list[Any] = [product_id, warehouse_id]
        else:
            sql = f"""
                SELECT *
                FROM {self.schema}.{self.table}
                WHERE product_id = %s
                  AND product_variant_id = %s
                  AND warehouse_id = %s
                  AND is_deleted = FALSE
            """
            params = [product_id, product_variant_id, warehouse_id]
        return select_one(sql, params, conn=conn)

    def fetch_for_update(
        self,
        inventory_id: int,
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE inventory_id = %s AND is_deleted = FALSE
            FOR UPDATE
        """
        return select_one(sql, [inventory_id], conn=conn)

    def fetch_by_product_warehouse_for_update(
        self,
        *,
        product_id: int,
        warehouse_id: int,
        product_variant_id: Optional[int] = None,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        if product_variant_id is None:
            sql = f"""
                SELECT *
                FROM {self.schema}.{self.table}
                WHERE product_id = %s
                  AND product_variant_id IS NULL
                  AND warehouse_id = %s
                  AND is_deleted = FALSE
                FOR UPDATE
            """
            params: list[Any] = [product_id, warehouse_id]
        else:
            sql = f"""
                SELECT *
                FROM {self.schema}.{self.table}
                WHERE product_id = %s
                  AND product_variant_id = %s
                  AND warehouse_id = %s
                  AND is_deleted = FALSE
                FOR UPDATE
            """
            params = [product_id, product_variant_id, warehouse_id]
        return select_one(sql, params, conn=conn)

    def combo_exists(
        self,
        *,
        product_id: int,
        warehouse_id: int,
        product_variant_id: Optional[int] = None,
        exclude_id: Optional[int] = None,
    ) -> bool:
        row = self.fetch_by_product_warehouse(
            product_id=product_id,
            warehouse_id=warehouse_id,
            product_variant_id=product_variant_id,
        )
        if not row:
            return False
        if exclude_id and int(row["inventory_id"]) == exclude_id:
            return False
        return True

    def create(
        self,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (product_id, product_variant_id, warehouse_id,
                 available_stock, reserved_stock, sold_stock,
                 damaged_stock, returned_stock, warehouse_stock,
                 reorder_level, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING inventory_id
        """
        if conn is not None:
            rows = execute(sql, list(data.values()), conn=conn, fetch=True)
            inventory_id = rows[0]["inventory_id"]
            return self.fetch_by_id(inventory_id) or rows[0]
        row = insert_query_returning(sql, list(data.values()))
        if row:
            return self.fetch_by_id(int(row["inventory_id"])) or row
        return {}

    def update(
        self,
        inventory_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(inventory_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE inventory_id = %s AND is_deleted = FALSE
            RETURNING inventory_id
        """
        params = [*data.values(), inventory_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(inventory_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(inventory_id) if rows else None

    def update_stock_levels(
        self,
        inventory_id: int,
        data: dict[str, Any],
        *,
        conn: PgConnection,
    ) -> Optional[dict[str, Any]]:
        return self.update(inventory_id, data, conn=conn)

    def soft_delete(self, inventory_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE inventory_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [inventory_id]) > 0

    def list_low_stock(
        self,
        *,
        page: int,
        page_size: int,
        warehouse_id: Optional[int] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = """
            i.is_deleted = FALSE
            AND i.is_active = TRUE
            AND i.reorder_level > 0
            AND i.available_stock <= i.reorder_level
            AND p.is_deleted = FALSE
            AND w.is_deleted = FALSE
        """
        if warehouse_id:
            where += " AND i.warehouse_id = %s"
            params.append(warehouse_id)

        count_sql = f"""
            SELECT COUNT(*) AS total
            {self._from_clause()}
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                {self._SELECT_COLUMNS},
                (i.reorder_level - i.available_stock) AS shortage
            {self._from_clause()}
            WHERE {where}
            ORDER BY shortage DESC, i.available_stock ASC, i.inventory_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total


inventory_repository = InventoryRepository()
