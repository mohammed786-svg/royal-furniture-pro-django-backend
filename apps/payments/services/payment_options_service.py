from __future__ import annotations

from apps.customers.repositories.customer_repository import customer_repository
from core.database import select_query
from core.helpers.text import from_db_text


class PaymentOptionsService:
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

        orders_sql = f"""
            SELECT
                o.order_id,
                o.order_number,
                o.customer_id,
                o.total_amount,
                o.payment_method,
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
                "paymentMethod": from_db_text(o.get("payment_method")) or "",
                "currentStatus": from_db_text(o.get("current_status")) or "",
            }
            for o in select_query(orders_sql)
        ]

        return {
            "orders": orders,
            "customers": customers,
            "paymentMethods": ["QR", "UPI", "CARD", "COD", "WALLET", "BANK_TRANSFER"],
            "paymentStatuses": ["PENDING", "PAID", "VERIFIED", "FAILED", "REFUNDED", "PARTIAL"],
            "verificationStatuses": ["PENDING", "APPROVED", "REJECTED"],
        }


payment_options_service = PaymentOptionsService()
