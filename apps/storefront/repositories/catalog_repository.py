from __future__ import annotations

from typing import Any, Optional

from core.database import select_query


class StorefrontCatalogRepository:
    schema = "royal"

    def list_under_sub_categories(self, sub_category_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                us.under_sub_category_id,
                us.name,
                us.slug,
                us.image_url,
                c.slug AS category_slug,
                sc.slug AS sub_category_slug
            FROM {self.schema}.under_sub_categorytbl us
            INNER JOIN {self.schema}.sub_categorytbl sc
                ON sc.sub_category_id = us.sub_category_id
            INNER JOIN {self.schema}.categorytbl c
                ON c.category_id = us.category_id
            WHERE us.sub_category_id = %s
              AND us.is_deleted = FALSE
              AND us.is_visible = TRUE
              AND us.is_active = TRUE
            ORDER BY us.display_order ASC, us.under_sub_category_id ASC
        """
        return select_query(sql, [sub_category_id])

    def fetch_available_stock(self, product_id: int) -> int:
        from core.database import select_one

        row = select_one(
            f"""
            SELECT COALESCE(SUM(available_stock), 0) AS stock
            FROM {self.schema}.inventorytbl
            WHERE product_id = %s AND is_deleted = FALSE AND is_active = TRUE
            """,
            [product_id],
        )
        return int(row["stock"]) if row else 0


storefront_catalog_repository = StorefrontCatalogRepository()
