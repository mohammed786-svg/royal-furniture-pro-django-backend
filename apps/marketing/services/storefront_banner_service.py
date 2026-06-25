from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.marketing.repositories.banner_repository import banner_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.helpers.text import from_db_text

HERO_POSITION_CODE = "HOME_HERO"
BANNERS_CACHE_TTL = 3600


def _normalize_href(value: Any) -> str:
    link = from_db_text(value)
    if not link or link in {"#", "/"}:
        return "#"
    return link


class StorefrontBannerService:
    def _serialize_storefront(self, row: dict[str, Any]) -> dict[str, Any]:
        image_url = from_db_text(row.get("image_url"))
        mobile_image_url = from_db_text(row.get("mobile_image_url"))
        return {
            "id": str(row["banner_id"]),
            "title": from_db_text(row.get("title")) or "",
            "subtitle": from_db_text(row.get("subtitle")),
            "imageUrl": image_url,
            "mobileImageUrl": mobile_image_url or image_url,
            "href": _normalize_href(row.get("link_url")),
            "displayOrder": int(row.get("display_order") or 0),
        }

    def _build_payload(self, position_code: str) -> dict[str, Any]:
        rows = banner_repository.list_active_by_position_code(position_code)
        return {
            "positionCode": position_code,
            "items": [self._serialize_storefront(row) for row in rows],
            "version": banner_repository.fetch_version_for_position(position_code),
            "cachedAt": datetime.now(timezone.utc).isoformat(),
        }

    def get_banners_for_position(self, position_code: str) -> dict[str, Any]:
        cache_key = CacheKeys.banners(position_code)
        return cache_manager.get_or_set(
            cache_key,
            lambda: self._build_payload(position_code),
            ttl=BANNERS_CACHE_TTL,
        )

    def get_hero_banners(self) -> dict[str, Any]:
        return self.get_banners_for_position(HERO_POSITION_CODE)

    def invalidate_position_cache(self, position_code: str | None = None) -> None:
        if position_code:
            cache_manager.delete(CacheKeys.banners(position_code))
            return
        cache_manager.delete(CacheKeys.banners(HERO_POSITION_CODE))


storefront_banner_service = StorefrontBannerService()
