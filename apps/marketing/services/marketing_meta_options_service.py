from __future__ import annotations

from apps.marketing.repositories.banner_position_repository import banner_position_repository
from core.database import select_query
from core.helpers.text import from_db_text


class MarketingMetaOptionsService:
    schema = "royal"

    def get_options(self) -> dict[str, object]:
        banner_positions = [
            {
                "id": str(bp["banner_position_id"]),
                "positionCode": from_db_text(bp.get("position_code")) or "",
                "positionName": from_db_text(bp.get("position_name")) or "",
            }
            for bp in banner_position_repository.list_active()
        ]

        categories_sql = f"""
            SELECT category_id, name, slug
            FROM {self.schema}.categorytbl
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY display_order, name
        """
        categories = [
            {
                "id": str(c["category_id"]),
                "name": from_db_text(c.get("name")) or "",
                "slug": from_db_text(c.get("slug")) or "",
            }
            for c in select_query(categories_sql)
        ]

        products_sql = f"""
            SELECT product_id, name, sku
            FROM {self.schema}.producttbl
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY name
        """
        products = [
            {
                "id": str(p["product_id"]),
                "name": from_db_text(p.get("name")) or "",
                "sku": from_db_text(p.get("sku")) or "",
            }
            for p in select_query(products_sql)
        ]

        return {
            "bannerPositions": banner_positions,
            "categories": categories,
            "products": products,
        }


marketing_meta_options_service = MarketingMetaOptionsService()
