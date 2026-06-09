from __future__ import annotations

from apps.customers.repositories.customer_repository import customer_repository
from apps.orders.repositories.order_status_repository import order_status_repository
from core.database import select_query
from core.helpers.text import from_db_text


class OrderOptionsService:
    schema = "royal"

    def get_options(self) -> dict[str, object]:
        customers = [
            {
                "id": str(c["customer_id"]),
                "fullName": from_db_text(c.get("full_name")) or "",
                "email": from_db_text(c.get("email")) or "",
                "phone": from_db_text(c.get("phone")) or "",
            }
            for c in customer_repository.list_options()
        ]

        statuses = [
            {
                "id": str(s["order_status_id"]),
                "statusCode": from_db_text(s.get("status_code")) or "",
                "statusName": from_db_text(s.get("status_name")) or "",
                "isTerminal": bool(s.get("is_terminal")),
            }
            for s in order_status_repository.list_all_active()
        ]

        products_sql = f"""
            SELECT product_id, name, sku, sale_price, hsn_code, gst_percent
            FROM {self.schema}.producttbl
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY name
        """
        products = [
            {
                "id": str(p["product_id"]),
                "name": from_db_text(p.get("name")) or "",
                "sku": from_db_text(p.get("sku")) or "",
                "salePrice": float(p.get("sale_price") or 0),
                "hsnCode": from_db_text(p.get("hsn_code")) or "",
                "gstPercent": float(p.get("gst_percent") or 0),
            }
            for p in select_query(products_sql)
        ]

        variants_sql = f"""
            SELECT
                pv.product_variant_id,
                pv.product_id,
                pv.variant_name,
                pv.sku,
                pv.sale_price,
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
                "salePrice": float(v.get("sale_price") or 0),
            }
            for v in select_query(variants_sql)
        ]

        addresses_sql = f"""
            SELECT
                a.address_id,
                a.customer_id,
                a.address_type,
                a.full_name,
                a.city,
                a.pincode,
                c.full_name AS customer_name
            FROM {self.schema}.addresstbl a
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = a.customer_id
            WHERE a.is_deleted = FALSE AND a.is_active = TRUE
            ORDER BY c.full_name, a.is_default DESC
        """
        addresses = [
            {
                "id": str(a["address_id"]),
                "customerId": str(a["customer_id"]),
                "customerName": from_db_text(a.get("customer_name")) or "",
                "addressType": from_db_text(a.get("address_type")) or "",
                "fullName": from_db_text(a.get("full_name")) or "",
                "city": from_db_text(a.get("city")) or "",
                "pincode": from_db_text(a.get("pincode")) or "",
            }
            for a in select_query(addresses_sql)
        ]

        return {
            "customers": customers,
            "products": products,
            "variants": variants,
            "addresses": addresses,
            "statuses": statuses,
            "paymentMethods": ["QR", "UPI", "CARD", "COD", "WALLET", "BANK_TRANSFER"],
        }


order_options_service = OrderOptionsService()
