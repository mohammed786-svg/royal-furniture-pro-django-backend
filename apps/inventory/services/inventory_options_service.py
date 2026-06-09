from __future__ import annotations

from apps.inventory.repositories.warehouse_repository import warehouse_repository
from core.database import select_query
from core.helpers.text import from_db_text


class InventoryOptionsService:
    schema = "royal"

    def get_options(self) -> dict[str, object]:
        warehouses = [
            {
                "id": str(w["warehouse_id"]),
                "code": from_db_text(w.get("warehouse_code")) or "",
                "name": from_db_text(w.get("name")) or "",
                "isPrimary": bool(w.get("is_primary")),
            }
            for w in warehouse_repository.list_options()
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

        variants_sql = f"""
            SELECT
                pv.product_variant_id,
                pv.product_id,
                pv.variant_name,
                pv.sku,
                p.name AS product_name
            FROM {self.schema}.product_varianttbl pv
            INNER JOIN {self.schema}.producttbl p ON p.product_id = pv.product_id
            WHERE pv.is_deleted = FALSE
              AND pv.is_active = TRUE
              AND p.is_deleted = FALSE
            ORDER BY p.name, pv.variant_name
        """
        variants = [
            {
                "id": str(v["product_variant_id"]),
                "productId": str(v["product_id"]),
                "productName": from_db_text(v.get("product_name")) or "",
                "variantName": from_db_text(v.get("variant_name")) or "",
                "sku": from_db_text(v.get("sku")) or "",
            }
            for v in select_query(variants_sql)
        ]

        return {
            "warehouses": warehouses,
            "products": products,
            "variants": variants,
            "adjustmentTypes": ["INCREASE", "DECREASE", "DAMAGE", "RETURN", "CORRECTION"],
            "adjustmentStatuses": ["PENDING", "APPROVED", "REJECTED"],
            "transferStatuses": ["PENDING", "IN_TRANSIT", "COMPLETED", "CANCELLED"],
        }


inventory_options_service = InventoryOptionsService()
