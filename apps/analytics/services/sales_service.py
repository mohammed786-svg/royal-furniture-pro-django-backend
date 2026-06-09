from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.analytics.repositories.sales_repository import sales_repository
from core.helpers.text import from_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _change_percent(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


_STATUS_COLORS = {
    "Delivered": "#1CBEAA",
    "Shipped": "#3D5EE1",
    "Processing": "#FFA726",
    "Pending": "#E74C3C",
    "Payment Pending": "#9C27B0",
    "Payment Verified": "#00BCD4",
    "Confirmed": "#4CAF50",
    "Packed": "#FF9800",
    "Cancelled": "#F44336",
    "Returned": "#795548",
    "Refunded": "#607D8B",
}


class SalesService:
    def get_dashboard(self, *, period: str = "30d") -> dict[str, Any]:
        if period not in {"7d", "30d", "90d"}:
            period = "30d"

        stats = sales_repository.summary_stats(period=period)
        current_revenue = float(stats.get("current_revenue") or 0)
        current_orders = int(stats.get("current_orders") or 0)
        previous_revenue = float(stats.get("previous_revenue") or 0)
        previous_orders = int(stats.get("previous_orders") or 0)
        avg_order_value = round(current_revenue / current_orders, 2) if current_orders else 0.0

        status_rows = sales_repository.orders_by_status(period=period)
        orders_by_status = [
            {
                "label": from_db_text(row.get("label")) or "Unknown",
                "value": int(row.get("value") or 0),
                "color": _STATUS_COLORS.get(
                    from_db_text(row.get("label")) or "",
                    "#9E9E9E",
                ),
            }
            for row in status_rows
        ]

        return {
            "summary": {
                "totalRevenue": round(current_revenue, 2),
                "totalOrders": current_orders,
                "avgOrderValue": avg_order_value,
                "revenueChangePercent": _change_percent(current_revenue, previous_revenue),
                "ordersChangePercent": _change_percent(float(current_orders), float(previous_orders)),
            },
            "revenueTrend": [
                {
                    "label": from_db_text(row.get("label")) or "",
                    "value": round(float(row.get("value") or 0), 2),
                }
                for row in sales_repository.revenue_trend(period=period)
            ],
            "ordersByStatus": orders_by_status,
            "topProducts": [
                {
                    "id": str(row["product_id"]),
                    "name": from_db_text(row.get("name")) or "",
                    "sku": from_db_text(row.get("sku")) or "",
                    "quantity": int(row.get("quantity") or 0),
                    "revenue": round(float(row.get("revenue") or 0), 2),
                }
                for row in sales_repository.top_products(period=period)
            ],
            "paymentBreakdown": [
                {
                    "label": from_db_text(row.get("label")) or "Unknown",
                    "value": int(row.get("value") or 0),
                }
                for row in sales_repository.payment_breakdown(period=period)
            ],
            "recentOrders": [
                {
                    "id": str(row["order_id"]),
                    "orderNumber": from_db_text(row.get("order_number")) or "",
                    "customerName": from_db_text(row.get("customer_name")) or "",
                    "totalAmount": round(float(row.get("total_amount") or 0), 2),
                    "status": from_db_text(row.get("status")) or "",
                    "createdAt": _format_dt(row.get("created_at")),
                }
                for row in sales_repository.recent_orders()
            ],
        }


sales_service = SalesService()
