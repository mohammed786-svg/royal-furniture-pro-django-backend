from __future__ import annotations

from typing import Any, Optional

from core.database import select_one, select_query


class SalesRepository:
    schema = "royal"

    def _period_days(self, period: str) -> int:
        return {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)

    def summary_stats(self, *, period: str = "30d") -> dict[str, Any]:
        days = self._period_days(period)
        sql = f"""
            SELECT
                COALESCE(SUM(CASE WHEN o.created_at >= NOW() - INTERVAL '{days} days'
                    THEN o.total_amount ELSE 0 END), 0) AS current_revenue,
                COUNT(CASE WHEN o.created_at >= NOW() - INTERVAL '{days} days'
                    THEN 1 END) AS current_orders,
                COALESCE(SUM(CASE WHEN o.created_at >= NOW() - INTERVAL '{days * 2} days'
                    AND o.created_at < NOW() - INTERVAL '{days} days'
                    THEN o.total_amount ELSE 0 END), 0) AS previous_revenue,
                COUNT(CASE WHEN o.created_at >= NOW() - INTERVAL '{days * 2} days'
                    AND o.created_at < NOW() - INTERVAL '{days} days'
                    THEN 1 END) AS previous_orders
            FROM {self.schema}.ordertbl o
            WHERE o.is_deleted = FALSE
        """
        row = select_one(sql) or {}
        return row

    def revenue_trend(self, *, period: str = "30d") -> list[dict[str, Any]]:
        days = self._period_days(period)
        if days <= 7:
            group_expr = "TO_CHAR(o.created_at, 'Dy')"
            order_expr = "DATE(o.created_at)"
        elif days <= 30:
            group_expr = "TO_CHAR(o.created_at, 'Mon DD')"
            order_expr = "DATE(o.created_at)"
        else:
            group_expr = "TO_CHAR(o.created_at, 'Mon DD')"
            order_expr = "DATE(o.created_at)"

        sql = f"""
            SELECT
                {group_expr} AS label,
                COALESCE(SUM(o.total_amount), 0) AS value
            FROM {self.schema}.ordertbl o
            WHERE o.is_deleted = FALSE
              AND o.created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY {order_expr}, {group_expr}
            ORDER BY {order_expr}
        """
        return select_query(sql)

    def orders_by_status(self, *, period: str = "30d") -> list[dict[str, Any]]:
        days = self._period_days(period)
        sql = f"""
            SELECT
                COALESCE(os.status_name, o.current_status, 'Unknown') AS label,
                COUNT(*) AS value
            FROM {self.schema}.ordertbl o
            LEFT JOIN {self.schema}.order_statustbl os ON os.order_status_id = o.order_status_id
            WHERE o.is_deleted = FALSE
              AND o.created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY os.status_name, o.current_status
            ORDER BY value DESC
        """
        return select_query(sql)

    def top_products(self, *, period: str = "30d", limit: int = 10) -> list[dict[str, Any]]:
        days = self._period_days(period)
        sql = f"""
            SELECT
                oi.product_id,
                COALESCE(oi.product_name, p.name, 'Unknown') AS name,
                COALESCE(oi.sku, p.sku, 'NA') AS sku,
                SUM(oi.quantity) AS quantity,
                COALESCE(SUM(oi.line_total), 0) AS revenue
            FROM {self.schema}.order_itemtbl oi
            INNER JOIN {self.schema}.ordertbl o ON o.order_id = oi.order_id
            LEFT JOIN {self.schema}.producttbl p ON p.product_id = oi.product_id
            WHERE oi.is_deleted = FALSE
              AND o.is_deleted = FALSE
              AND o.created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY oi.product_id, oi.product_name, oi.sku, p.name, p.sku
            ORDER BY revenue DESC
            LIMIT %s
        """
        return select_query(sql, [limit])

    def payment_breakdown(self, *, period: str = "30d") -> list[dict[str, Any]]:
        days = self._period_days(period)
        sql = f"""
            SELECT
                COALESCE(NULLIF(o.payment_method, 'NA'), 'Unknown') AS label,
                COUNT(*) AS value
            FROM {self.schema}.ordertbl o
            WHERE o.is_deleted = FALSE
              AND o.created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY o.payment_method
            ORDER BY value DESC
        """
        return select_query(sql)

    def recent_orders(self, *, limit: int = 10) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                o.order_id,
                o.order_number,
                COALESCE(c.full_name, 'Guest') AS customer_name,
                o.total_amount,
                COALESCE(os.status_name, o.current_status, 'Unknown') AS status,
                o.created_at
            FROM {self.schema}.ordertbl o
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = o.customer_id
            LEFT JOIN {self.schema}.order_statustbl os ON os.order_status_id = o.order_status_id
            WHERE o.is_deleted = FALSE
            ORDER BY o.created_at DESC
            LIMIT %s
        """
        return select_query(sql, [limit])

    def catalog_counts(self) -> dict[str, Any]:
        sql = f"""
            SELECT
                (SELECT COUNT(*)
                 FROM {self.schema}.customertbl
                 WHERE is_deleted = FALSE) AS total_customers,
                (SELECT COUNT(*)
                 FROM {self.schema}.customertbl
                 WHERE is_deleted = FALSE AND is_active = TRUE) AS active_customers,
                (SELECT COUNT(*)
                 FROM {self.schema}.producttbl
                 WHERE is_deleted = FALSE) AS total_products,
                (SELECT COUNT(*)
                 FROM {self.schema}.producttbl
                 WHERE is_deleted = FALSE AND is_active = TRUE) AS active_products
        """
        return select_one(sql) or {}

    def all_time_order_counts(self) -> dict[str, Any]:
        sql = f"""
            SELECT
                COUNT(*) AS total_orders,
                COUNT(
                    CASE
                        WHEN LOWER(COALESCE(os.status_name, o.current_status, ''))
                            NOT IN ('cancelled', 'returned', 'refunded')
                        THEN 1
                    END
                ) AS active_orders,
                COUNT(
                    CASE
                        WHEN LOWER(COALESCE(os.status_name, o.current_status, ''))
                            IN ('cancelled', 'returned', 'refunded')
                        THEN 1
                    END
                ) AS inactive_orders
            FROM {self.schema}.ordertbl o
            LEFT JOIN {self.schema}.order_statustbl os
                ON os.order_status_id = o.order_status_id
            WHERE o.is_deleted = FALSE
        """
        return select_one(sql) or {}

    def growth_counts(self, *, period: str = "30d") -> dict[str, Any]:
        days = self._period_days(period)
        sql = f"""
            SELECT
                COUNT(CASE WHEN c.created_at >= NOW() - INTERVAL '{days} days'
                    THEN 1 END) AS current_customers,
                COUNT(CASE WHEN c.created_at >= NOW() - INTERVAL '{days * 2} days'
                    AND c.created_at < NOW() - INTERVAL '{days} days'
                    THEN 1 END) AS previous_customers,
                (SELECT COUNT(*)
                 FROM {self.schema}.producttbl p
                 WHERE p.is_deleted = FALSE
                   AND p.created_at >= NOW() - INTERVAL '{days} days') AS current_products,
                (SELECT COUNT(*)
                 FROM {self.schema}.producttbl p
                 WHERE p.is_deleted = FALSE
                   AND p.created_at >= NOW() - INTERVAL '{days * 2} days'
                   AND p.created_at < NOW() - INTERVAL '{days} days') AS previous_products
            FROM {self.schema}.customertbl c
            WHERE c.is_deleted = FALSE
        """
        return select_one(sql) or {}

    def pending_payment_alert(self) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                o.order_id,
                o.order_number,
                COALESCE(c.full_name, 'Guest') AS customer_name,
                pv.payment_verification_id
            FROM {self.schema}.payment_verificationtbl pv
            INNER JOIN {self.schema}.ordertbl o ON o.order_id = pv.order_id
            INNER JOIN {self.schema}.customertbl c ON c.customer_id = o.customer_id
            WHERE pv.is_deleted = FALSE
              AND o.is_deleted = FALSE
              AND pv.verification_status = 'PENDING'
            ORDER BY pv.created_at DESC
            LIMIT 1
        """
        return select_one(sql)


sales_repository = SalesRepository()
