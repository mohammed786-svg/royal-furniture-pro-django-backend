from __future__ import annotations

from typing import Any

from core.database import select_one, select_query


class NavbarRepository:
    schema = "royal"

    @staticmethod
    def _visible(alias: str) -> str:
        return (
            f"{alias}.is_deleted = FALSE "
            f"AND {alias}.is_visible = TRUE "
            f"AND {alias}.is_active = TRUE"
        )

    def fetch_categories(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                category_id,
                name,
                slug,
                image_url,
                icon_url,
                display_order,
                updated_at,
                epoch
            FROM {self.schema}.categorytbl c
            WHERE {self._visible("c")}
            ORDER BY display_order ASC, category_id ASC
        """
        return select_query(sql, [])

    def fetch_sub_categories(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                sc.sub_category_id,
                sc.category_id,
                sc.name,
                sc.slug,
                sc.display_order,
                sc.updated_at,
                sc.epoch
            FROM {self.schema}.sub_categorytbl sc
            INNER JOIN {self.schema}.categorytbl c
                ON c.category_id = sc.category_id
            WHERE {self._visible("sc")}
              AND {self._visible("c")}
            ORDER BY sc.category_id ASC, sc.display_order ASC, sc.sub_category_id ASC
        """
        return select_query(sql, [])

    def fetch_under_sub_categories(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                us.under_sub_category_id,
                us.sub_category_id,
                us.category_id,
                us.name,
                us.slug,
                us.display_order,
                us.updated_at,
                us.epoch
            FROM {self.schema}.under_sub_categorytbl us
            INNER JOIN {self.schema}.sub_categorytbl sc
                ON sc.sub_category_id = us.sub_category_id
            INNER JOIN {self.schema}.categorytbl c
                ON c.category_id = us.category_id
            WHERE {self._visible("us")}
              AND {self._visible("sc")}
              AND {self._visible("c")}
            ORDER BY us.sub_category_id ASC, us.display_order ASC, us.under_sub_category_id ASC
        """
        return select_query(sql, [])

    def fetch_version_stamp(self) -> str:
        sql = f"""
            SELECT COALESCE(
                MAX(GREATEST(
                    COALESCE(c.epoch, 0),
                    COALESCE(sc.epoch, 0),
                    COALESCE(us.epoch, 0)
                )),
                0
            ) AS version_epoch
            FROM {self.schema}.categorytbl c
            LEFT JOIN {self.schema}.sub_categorytbl sc
                ON sc.category_id = c.category_id
               AND sc.is_deleted = FALSE
            LEFT JOIN {self.schema}.under_sub_categorytbl us
                ON us.category_id = c.category_id
               AND us.is_deleted = FALSE
            WHERE c.is_deleted = FALSE
        """
        row = select_one(sql, [])
        epoch = float(row["version_epoch"]) if row else 0.0
        return f"{epoch:.6f}"


navbar_repository = NavbarRepository()
