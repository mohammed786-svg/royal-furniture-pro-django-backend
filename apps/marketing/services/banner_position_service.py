from __future__ import annotations

from typing import Any

from apps.marketing.repositories.banner_position_repository import banner_position_repository
from core.helpers.text import from_db_text


class BannerPositionService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["banner_position_id"]),
            "positionCode": from_db_text(row.get("position_code")) or "",
            "positionName": from_db_text(row.get("position_name")) or "",
            "description": from_db_text(row.get("description")),
            "maxBanners": int(row.get("max_banners") or 0),
            "isActive": bool(row.get("is_active")),
        }

    def list_positions(self) -> dict[str, Any]:
        rows = banner_position_repository.list_active()
        return {"items": [self._serialize(r) for r in rows]}


banner_position_service = BannerPositionService()
