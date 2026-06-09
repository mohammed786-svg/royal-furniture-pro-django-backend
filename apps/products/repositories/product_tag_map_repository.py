from __future__ import annotations

from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import insert_query_returning, select_query, update_query
from core.database.raw_queries import execute


class ProductTagMapRepository:
    schema = "royal"
    table = "product_tag_maptbl"

    def list_product_ids_for_tag(self, tag_id: int) -> list[int]:
        sql = f"""
            SELECT product_id
            FROM {self.schema}.{self.table}
            WHERE product_tag_id = %s
              AND is_deleted = FALSE
              AND is_active = TRUE
            ORDER BY product_id
        """
        rows = select_query(sql, [tag_id])
        return [int(r["product_id"]) for r in rows]

    def deactivate_missing(self, tag_id: int, product_ids: list[int], *, conn: Optional[PgConnection] = None) -> None:
        if product_ids:
            placeholders = ", ".join(["%s"] * len(product_ids))
            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET is_active = FALSE, is_deleted = TRUE, updated_at = NOW()
                WHERE product_tag_id = %s
                  AND is_deleted = FALSE
                  AND product_id NOT IN ({placeholders})
            """
            execute(sql, [tag_id, *product_ids], conn=conn)
        else:
            sql = f"""
                UPDATE {self.schema}.{self.table}
                SET is_active = FALSE, is_deleted = TRUE, updated_at = NOW()
                WHERE product_tag_id = %s AND is_deleted = FALSE
            """
            execute(sql, [tag_id], conn=conn)

    def upsert_mapping(
        self,
        *,
        product_id: int,
        tag_id: int,
        conn: Optional[PgConnection] = None,
    ) -> None:
        existing_sql = f"""
            SELECT product_tag_map_id, is_deleted, is_active
            FROM {self.schema}.{self.table}
            WHERE product_id = %s AND product_tag_id = %s
        """
        from core.database import select_one

        existing = select_one(existing_sql, [product_id, tag_id], conn=conn)
        if existing:
            if existing.get("is_deleted") or not existing.get("is_active"):
                update_sql = f"""
                    UPDATE {self.schema}.{self.table}
                    SET is_deleted = FALSE, is_active = TRUE, updated_at = NOW()
                    WHERE product_tag_map_id = %s
                """
                execute(update_sql, [existing["product_tag_map_id"]], conn=conn)
            return

        insert_sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (product_id, product_tag_id, is_active)
            VALUES (%s, %s, TRUE)
            RETURNING product_tag_map_id
        """
        insert_query_returning(insert_sql, [product_id, tag_id], conn=conn)

    def sync_for_tag(
        self,
        tag_id: int,
        product_ids: list[int],
        *,
        conn: Optional[PgConnection] = None,
    ) -> None:
        unique_ids = sorted({int(pid) for pid in product_ids})
        self.deactivate_missing(tag_id, unique_ids, conn=conn)
        for product_id in unique_ids:
            self.upsert_mapping(product_id=product_id, tag_id=tag_id, conn=conn)

    def deactivate_all_for_tag(self, tag_id: int, *, conn: Optional[PgConnection] = None) -> None:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_active = FALSE, is_deleted = TRUE, updated_at = NOW()
            WHERE product_tag_id = %s AND is_deleted = FALSE
        """
        execute(sql, [tag_id], conn=conn)

    def product_count_for_tag(self, tag_id: int) -> int:
        sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table}
            WHERE product_tag_id = %s
              AND is_deleted = FALSE
              AND is_active = TRUE
        """
        from core.database import select_one

        row = select_one(sql, [tag_id])
        return int(row["total"]) if row else 0


product_tag_map_repository = ProductTagMapRepository()
