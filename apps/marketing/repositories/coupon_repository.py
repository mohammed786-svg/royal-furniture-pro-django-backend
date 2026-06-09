from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class CouponRepository:
    schema = "royal"
    table = "coupontbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "c.is_deleted = FALSE"
        if search:
            where += " AND (c.coupon_code ILIKE %s OR c.coupon_name ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])
        if is_active is not None:
            where += " AND c.is_active = %s"
            params.append(is_active)

        allowed_sort = {
            "coupon_code": "c.coupon_code",
            "coupon_name": "c.coupon_name",
            "discount_value": "c.discount_value",
            "used_count": "c.used_count",
            "starts_at": "c.starts_at",
            "expires_at": "c.expires_at",
            "created_at": "c.created_at",
        }
        order_col = allowed_sort.get(sort_by, "c.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} c
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT c.*
            FROM {self.schema}.{self.table} c
            WHERE {where}
            ORDER BY {order_col} {direction}, c.coupon_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, coupon_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE coupon_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [coupon_id])

    def code_exists(self, coupon_code: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT coupon_id
            FROM {self.schema}.{self.table}
            WHERE coupon_code = %s AND is_deleted = FALSE
        """
        params: list[Any] = [coupon_code]
        if exclude_id:
            sql += " AND coupon_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (coupon_code, coupon_name, discount_type, discount_value,
                 max_discount_amount, minimum_order_amount, usage_limit,
                 usage_per_customer, used_count, starts_at, expires_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, coupon_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(coupon_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE coupon_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), coupon_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, coupon_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE coupon_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [coupon_id]) > 0


coupon_repository = CouponRepository()
