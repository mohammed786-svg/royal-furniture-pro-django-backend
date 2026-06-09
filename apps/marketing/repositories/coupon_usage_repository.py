from __future__ import annotations

from typing import Any

from core.database import select_query


class CouponUsageRepository:
    schema = "royal"
    table = "coupon_usagetbl"

    def list_by_coupon(self, coupon_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT
                cu.*,
                c.full_name AS customer_name,
                c.email AS customer_email
            FROM {self.schema}.{self.table} cu
            LEFT JOIN {self.schema}.customertbl c ON c.customer_id = cu.customer_id
            WHERE cu.coupon_id = %s AND cu.is_deleted = FALSE
            ORDER BY cu.used_at DESC, cu.coupon_usage_id DESC
        """
        return select_query(sql, [coupon_id])


coupon_usage_repository = CouponUsageRepository()
