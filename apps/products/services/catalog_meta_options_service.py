from __future__ import annotations

from core.database import select_query
from core.helpers.text import from_db_text


class CatalogMetaOptionsService:
    schema = "royal"

    def get_options(self) -> dict[str, object]:
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

        customers_sql = f"""
            SELECT customer_id, full_name, email, phone
            FROM {self.schema}.customertbl
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY full_name, customer_id
        """
        customers = [
            {
                "id": str(c["customer_id"]),
                "fullName": from_db_text(c.get("full_name")) or "",
                "email": from_db_text(c.get("email")),
                "phone": from_db_text(c.get("phone")),
            }
            for c in select_query(customers_sql)
        ]

        return {
            "products": products,
            "customers": customers,
        }


catalog_meta_options_service = CatalogMetaOptionsService()
