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


def _initials(name: str) -> str:
    parts = [part for part in name.strip().split() if part and part != "NA"]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()


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
        current_revenue_orders = int(stats.get("current_revenue_orders") or 0)
        previous_revenue = float(stats.get("previous_revenue") or 0)
        previous_orders = int(stats.get("previous_orders") or 0)
        avg_order_value = (
            round(current_revenue / current_revenue_orders, 2) if current_revenue_orders else 0.0
        )

        catalog = sales_repository.catalog_counts()
        order_counts = sales_repository.all_time_order_counts()
        growth = sales_repository.growth_counts(period=period)
        alert_row = sales_repository.pending_payment_alert()

        total_customers = int(catalog.get("total_customers") or 0)
        active_customers = int(catalog.get("active_customers") or 0)
        total_products = int(catalog.get("total_products") or 0)
        active_products = int(catalog.get("active_products") or 0)

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

        alert: Optional[dict[str, Any]] = None
        if alert_row:
            customer_name = from_db_text(alert_row.get("customer_name")) or "Customer"
            order_number = from_db_text(alert_row.get("order_number")) or ""
            alert = {
                "orderId": str(alert_row["order_id"]),
                "orderNumber": order_number,
                "customerName": customer_name,
                "message": (
                    f"Payment verification pending for order {order_number} — {customer_name}."
                ),
                "avatar": _initials(customer_name),
            }

        return {
            "summary": {
                "totalRevenue": round(current_revenue, 2),
                "totalOrders": current_orders,
                "revenueOrders": current_revenue_orders,
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
            "catalogStats": {
                "totalCustomers": total_customers,
                "activeCustomers": active_customers,
                "inactiveCustomers": max(total_customers - active_customers, 0),
                "totalProducts": total_products,
                "activeProducts": active_products,
                "inactiveProducts": max(total_products - active_products, 0),
                "customersChangePercent": _change_percent(
                    float(growth.get("current_customers") or 0),
                    float(growth.get("previous_customers") or 0),
                ),
                "productsChangePercent": _change_percent(
                    float(growth.get("current_products") or 0),
                    float(growth.get("previous_products") or 0),
                ),
            },
            "orderStats": {
                "totalOrders": int(order_counts.get("total_orders") or 0),
                "activeOrders": int(order_counts.get("active_orders") or 0),
                "inactiveOrders": int(order_counts.get("inactive_orders") or 0),
            },
            "alert": alert,
        }


sales_service = SalesService()
