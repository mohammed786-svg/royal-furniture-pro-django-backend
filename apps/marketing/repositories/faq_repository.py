from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class FaqRepository:
    schema = "royal"
    table = "faqtbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "display_order",
        sort_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "f.is_deleted = FALSE"
        if search:
            where += " AND (f.category ILIKE %s OR f.question ILIKE %s OR f.answer ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        allowed_sort = {
            "category": "f.category",
            "question": "f.question",
            "display_order": "f.display_order",
            "created_at": "f.created_at",
        }
        order_col = allowed_sort.get(sort_by, "f.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} f
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT f.*
            FROM {self.schema}.{self.table} f
            WHERE {where}
            ORDER BY {order_col} {direction}, f.faq_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, faq_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE faq_id = %s AND is_deleted = FALSE
        """
        return select_one(sql, [faq_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (category, question, answer, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, faq_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(faq_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE faq_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), faq_id], fetch=True)
        return rows[0] if rows else None

    def soft_delete(self, faq_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE faq_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [faq_id]) > 0


faq_repository = FaqRepository()
