from __future__ import annotations

from apps.shiprocket.repositories.shipment_repository import shipment_repository
from core.database import select_query
from core.helpers.text import from_db_text


class ShippingOptionsService:
    schema = "royal"

    def get_options(self) -> dict[str, object]:
        orders_sql = f"""
            SELECT
                o.order_id,
                o.order_number,
                o.customer_id,
                o.total_amount,
                o.current_status,
                c.full_name AS customer_name
            FROM {self.schema}.ordertbl o
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = o.customer_id
            WHERE o.is_deleted = FALSE
            ORDER BY o.created_at DESC
            LIMIT 500
        """
        orders = [
            {
                "id": str(o["order_id"]),
                "orderNumber": from_db_text(o.get("order_number")) or "",
                "customerId": str(o["customer_id"]),
                "customerName": from_db_text(o.get("customer_name")) or "",
                "totalAmount": float(o.get("total_amount") or 0),
                "currentStatus": from_db_text(o.get("current_status")) or "",
            }
            for o in select_query(orders_sql)
        ]

        shipments = [
            {
                "id": str(s["shipment_id"]),
                "orderId": str(s["order_id"]),
                "orderNumber": from_db_text(s.get("order_number")) or "",
                "awbNumber": from_db_text(s.get("awb_number")),
                "trackingNumber": from_db_text(s.get("tracking_number")),
                "deliveryStatus": from_db_text(s.get("delivery_status")),
            }
            for s in shipment_repository.list_options()
        ]

        return {
            "orders": orders,
            "shipments": shipments,
            "pickupStatuses": ["NA", "SCHEDULED", "PICKED", "FAILED"],
            "deliveryStatuses": ["NA", "PENDING", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "RTO", "CANCELLED"],
            "trackingSources": ["SHIPROCKET", "MANUAL", "WEBHOOK"],
        }


shipping_options_service = ShippingOptionsService()
