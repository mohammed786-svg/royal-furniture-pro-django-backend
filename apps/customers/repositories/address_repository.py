from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class AddressRepository:
    schema = "royal"
    table = "addresstbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        customer_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "a.is_deleted = FALSE"
        if search:
            where += " AND (a.full_name ILIKE %s OR a.city ILIKE %s OR a.pincode ILIKE %s OR c.full_name ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
        if customer_id:
            where += " AND a.customer_id = %s"
            params.append(customer_id)

        allowed_sort = {
            "full_name": "a.full_name",
            "city": "a.city",
            "created_at": "a.created_at",
        }
        order_col = allowed_sort.get(sort_by, "a.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} a
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = a.customer_id
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT a.*, c.full_name AS customer_name, c.email AS customer_email
            FROM {self.schema}.{self.table} a
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = a.customer_id
            WHERE {where}
            ORDER BY a.is_default DESC, {order_col} {direction}, a.address_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, address_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT a.*, c.full_name AS customer_name
            FROM {self.schema}.{self.table} a
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = a.customer_id
            WHERE a.address_id = %s AND a.is_deleted = FALSE
        """
        return select_one(sql, [address_id])

    def list_by_customer(self, customer_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE customer_id = %s AND is_deleted = FALSE
            ORDER BY is_default DESC, created_at DESC
        """
        return select_query(sql, [customer_id])

    def clear_default_for_customer(
        self,
        customer_id: int,
        *,
        exclude_id: Optional[int] = None,
        conn: Optional[PgConnection] = None,
    ) -> None:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_default = FALSE, updated_at = NOW()
            WHERE customer_id = %s AND is_deleted = FALSE AND is_default = TRUE
        """
        params: list[Any] = [customer_id]
        if exclude_id:
            sql += " AND address_id <> %s"
            params.append(exclude_id)
        if conn is not None:
            execute(sql, params, conn=conn, fetch=False)
        else:
            update_query(sql, params)

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (customer_id, address_type, full_name, phone,
                 address_line1, address_line2, landmark, city, state, pincode, country,
                 is_default, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, values)
        return row or {}

    def update(
        self,
        address_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(address_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE address_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        params = [*data.values(), address_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return rows[0] if rows else None
        rows = execute(sql, params, fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, address_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE address_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [address_id]) > 0


address_repository = AddressRepository()
