from __future__ import annotations

from typing import Any

from core.database import select_query


class BannerPositionRepository:
    schema = "royal"
    table = "banner_positiontbl"

    def list_active(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY position_name, banner_position_id
        """
        return select_query(sql)


banner_position_repository = BannerPositionRepository()
