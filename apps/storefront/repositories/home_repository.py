from __future__ import annotations

from typing import Any, Optional

from core.database import select_one, select_query


class StorefrontHomeRepository:
    schema = "royal"

    def list_featured_categories(self, *, limit: int = 12) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                category_id,
                name,
                slug,
                image_url,
                icon_url,
                display_order
            FROM {self.schema}.categorytbl
            WHERE is_deleted = FALSE
              AND is_visible = TRUE
              AND is_active = TRUE
              AND is_featured = TRUE
            ORDER BY display_order ASC, category_id ASC
            LIMIT %s
        """
        rows = select_query(sql, [limit])
        if rows:
            return rows
        sql_fallback = f"""
            SELECT
                category_id,
                name,
                slug,
                image_url,
                icon_url,
                display_order
            FROM {self.schema}.categorytbl
            WHERE is_deleted = FALSE
              AND is_visible = TRUE
              AND is_active = TRUE
            ORDER BY display_order ASC, category_id ASC
            LIMIT %s
        """
        return select_query(sql_fallback, [limit])

    def list_decor_sub_categories(self, *, limit: int = 8) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                sc.sub_category_id,
                sc.name,
                sc.slug,
                sc.image_url,
                c.slug AS category_slug
            FROM {self.schema}.sub_categorytbl sc
            INNER JOIN {self.schema}.categorytbl c
                ON c.category_id = sc.category_id
            WHERE sc.is_deleted = FALSE
              AND sc.is_visible = TRUE
              AND sc.is_active = TRUE
              AND c.is_deleted = FALSE
              AND c.is_visible = TRUE
              AND c.is_active = TRUE
              AND (LOWER(c.slug) = 'decor' OR LOWER(c.name) = 'decor')
            ORDER BY sc.display_order ASC, sc.sub_category_id ASC
            LIMIT %s
        """
        return select_query(sql, [limit])

    def list_storefront_products(
        self,
        *,
        limit: int = 8,
        is_featured: Optional[bool] = None,
        is_best_seller: Optional[bool] = None,
        is_new_arrival: Optional[bool] = None,
        is_trending: Optional[bool] = None,
        on_sale: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        where = """
            p.is_deleted = FALSE
            AND p.is_active = TRUE
            AND c.is_deleted = FALSE
        """
        if is_featured is True:
            where += " AND p.is_featured = TRUE"
        if is_best_seller is True:
            where += " AND p.is_best_seller = TRUE"
        if is_new_arrival is True:
            where += " AND p.is_new_arrival = TRUE"
        if is_trending is True:
            where += " AND p.is_trending = TRUE"
        if on_sale is True:
            where += " AND p.sale_price > 0 AND p.mrp > p.sale_price"

        sql = f"""
            SELECT
                p.product_id,
                p.name,
                p.slug,
                p.sale_price,
                p.base_price,
                p.mrp,
                p.is_featured,
                p.is_new_arrival,
                p.is_best_seller,
                p.is_trending,
                b.name AS brand_name,
                (
                    SELECT pi.image_url
                    FROM {self.schema}.product_imagestbl pi
                    WHERE pi.product_id = p.product_id
                      AND pi.is_deleted = FALSE
                      AND pi.is_active = TRUE
                    ORDER BY pi.is_primary DESC, pi.display_order ASC
                    LIMIT 1
                ) AS primary_image_url
            FROM {self.schema}.producttbl p
            INNER JOIN {self.schema}.categorytbl c ON c.category_id = p.category_id
            LEFT JOIN {self.schema}.brandtbl b ON b.brand_id = p.brand_id
            WHERE {where}
            ORDER BY p.updated_at DESC, p.product_id DESC
            LIMIT %s
        """
        return select_query(sql, [limit])

    def list_featured_testimonials(self, *, limit: int = 10) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                t.testimonial_id,
                t.customer_name,
                t.customer_image,
                t.location,
                t.rating,
                t.testimonial_text,
                t.display_order
            FROM {self.schema}.testimonialtbl t
            WHERE t.is_deleted = FALSE
              AND t.is_active = TRUE
              AND t.is_featured = TRUE
            ORDER BY t.display_order ASC, t.testimonial_id ASC
            LIMIT %s
        """
        rows = select_query(sql, [limit])
        if rows:
            return rows
        sql_fallback = f"""
            SELECT
                t.testimonial_id,
                t.customer_name,
                t.customer_image,
                t.location,
                t.rating,
                t.testimonial_text,
                t.display_order
            FROM {self.schema}.testimonialtbl t
            WHERE t.is_deleted = FALSE
              AND t.is_active = TRUE
            ORDER BY t.display_order ASC, t.testimonial_id ASC
            LIMIT %s
        """
        return select_query(sql_fallback, [limit])

    def list_settings_by_group(self, group: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT setting_key, setting_value, value_type, description
            FROM {self.schema}.settingstbl
            WHERE is_deleted = FALSE
              AND is_active = TRUE
              AND setting_group = %s
            ORDER BY setting_key ASC
        """
        return select_query(sql, [group])

    def fetch_cms_page_by_code(self, page_code: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT cms_page_id, page_code, title, slug, content, seo_title, seo_description
            FROM {self.schema}.cms_pagetbl
            WHERE is_deleted = FALSE
              AND is_active = TRUE
              AND page_code = %s
            LIMIT 1
        """
        return select_one(sql, [page_code])

    def fetch_home_version_epoch(self) -> str:
        sql = f"""
            SELECT COALESCE(MAX(epoch), 0) AS version_epoch
            FROM (
                SELECT epoch FROM {self.schema}.producttbl WHERE is_deleted = FALSE
                UNION ALL
                SELECT epoch FROM {self.schema}.categorytbl WHERE is_deleted = FALSE
                UNION ALL
                SELECT epoch FROM {self.schema}.bannertbl WHERE is_deleted = FALSE
                UNION ALL
                SELECT epoch FROM {self.schema}.testimonialtbl WHERE is_deleted = FALSE
                UNION ALL
                SELECT epoch FROM {self.schema}.settingstbl WHERE is_deleted = FALSE
            ) versions
        """
        row = select_one(sql, [])
        epoch = float(row["version_epoch"]) if row else 0.0
        return f"{epoch:.6f}"


storefront_home_repository = StorefrontHomeRepository()
