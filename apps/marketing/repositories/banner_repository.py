from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class BannerRepository:
    schema = "royal"
    table = "bannertbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "display_order",
        sort_dir: str = "asc",
        position_id: Optional[int] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "b.is_deleted = FALSE"
        if search:
            where += " AND (b.title ILIKE %s OR b.subtitle ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term])
        if position_id is not None:
            where += " AND b.banner_position_id = %s"
            params.append(position_id)

        allowed_sort = {
            "title": "b.title",
            "display_order": "b.display_order",
            "starts_at": "b.starts_at",
            "ends_at": "b.ends_at",
            "created_at": "b.created_at",
        }
        order_col = allowed_sort.get(sort_by, "b.display_order")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} b
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                b.*,
                bp.position_code,
                bp.position_name,
                cat.name AS category_name
            FROM {self.schema}.{self.table} b
            INNER JOIN {self.schema}.banner_positiontbl bp
                ON bp.banner_position_id = b.banner_position_id
            LEFT JOIN {self.schema}.categorytbl cat
                ON cat.category_id = b.category_id
            WHERE {where}
            ORDER BY {order_col} {direction}, b.banner_id ASC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_id(self, banner_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                b.*,
                bp.position_code,
                bp.position_name,
                cat.name AS category_name
            FROM {self.schema}.{self.table} b
            INNER JOIN {self.schema}.banner_positiontbl bp
                ON bp.banner_position_id = b.banner_position_id
            LEFT JOIN {self.schema}.categorytbl cat
                ON cat.category_id = b.category_id
            WHERE b.banner_id = %s AND b.is_deleted = FALSE
        """
        return select_one(sql, [banner_id])

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (banner_position_id, category_id, title, subtitle, image_url,
                 mobile_image_url, link_url, link_type, display_order,
                 starts_at, ends_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        row = insert_query_returning(sql, list(data.values()))
        return row or {}

    def update(self, banner_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(banner_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE banner_id = %s AND is_deleted = FALSE
            RETURNING *
        """
        rows = execute(sql, [*data.values(), banner_id], fetch=True)
        if not rows:
            return None
        return self.fetch_by_id(banner_id)

    def soft_delete(self, banner_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE banner_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [banner_id]) > 0


banner_repository = BannerRepository()
