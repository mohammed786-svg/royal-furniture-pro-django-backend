from __future__ import annotations

from apps.customers.repositories.customer_repository import customer_repository
from core.helpers.text import from_db_text


class NotificationOptionsService:
    def get_options(self) -> dict[str, object]:
        customers = [
            {
                "id": str(row["customer_id"]),
                "fullName": from_db_text(row.get("full_name")) or "",
                "email": from_db_text(row.get("email")),
                "phone": from_db_text(row.get("phone")),
            }
            for row in customer_repository.list_options()
        ]
        return {
            "customers": customers,
            "channels": ["EMAIL", "SMS", "WHATSAPP", "PUSH", "IN_APP"],
            "targetTypes": ["ALL", "CUSTOMER", "SEGMENT", "ADMIN"],
            "statuses": ["PENDING", "SENT", "FAILED", "DELIVERED", "READ"],
        }


notification_options_service = NotificationOptionsService()
