from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.categories.repositories.navbar_repository import navbar_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.helpers.text import from_db_text

NAVBAR_CACHE_TTL = 3600


def _category_href(category_slug: str, sub_slug: str | None = None, under_slug: str | None = None) -> str:
    if under_slug:
        return f"/{category_slug}/{sub_slug}/{under_slug}"
    if sub_slug:
        return f"/{category_slug}/{sub_slug}"
    return f"/{category_slug}"


class NavbarService:
    def _build_tree(self) -> dict[str, Any]:
        categories = navbar_repository.fetch_categories()
        sub_categories = navbar_repository.fetch_sub_categories()
        under_sub_categories = navbar_repository.fetch_under_sub_categories()

        subs_by_category: dict[int, list[dict[str, Any]]] = {}
        for row in sub_categories:
            category_id = int(row["category_id"])
            subs_by_category.setdefault(category_id, []).append(row)

        unders_by_sub: dict[int, list[dict[str, Any]]] = {}
        for row in under_sub_categories:
            sub_id = int(row["sub_category_id"])
            unders_by_sub.setdefault(sub_id, []).append(row)

        items: list[dict[str, Any]] = []
        for category in categories:
            category_id = int(category["category_id"])
            category_slug = from_db_text(category.get("slug")) or ""
            category_name = from_db_text(category.get("name")) or ""
            subs = subs_by_category.get(category_id, [])

            columns: list[dict[str, Any]] = []
            for sub in subs:
                sub_id = int(sub["sub_category_id"])
                sub_slug = from_db_text(sub.get("slug")) or ""
                sub_name = from_db_text(sub.get("name")) or ""
                unders = unders_by_sub.get(sub_id, [])

                column_items = [
                    {
                        "id": str(under["under_sub_category_id"]),
                        "label": from_db_text(under.get("name")) or "",
                        "slug": from_db_text(under.get("slug")) or "",
                        "href": _category_href(category_slug, sub_slug, from_db_text(under.get("slug")) or ""),
                    }
                    for under in unders
                ]

                columns.append(
                    {
                        "id": str(sub["sub_category_id"]),
                        "title": sub_name,
                        "slug": sub_slug,
                        "href": _category_href(category_slug, sub_slug),
                        "items": column_items,
                    }
                )

            first_sub_slug = columns[0]["slug"] if columns else None
            items.append(
                {
                    "id": str(category["category_id"]),
                    "name": category_name,
                    "slug": category_slug,
                    "href": _category_href(category_slug, first_sub_slug),
                    "iconUrl": from_db_text(category.get("icon_url")),
                    "columns": columns,
                }
            )

        return {
            "items": items,
            "version": navbar_repository.fetch_version_stamp(),
            "cachedAt": datetime.now(timezone.utc).isoformat(),
        }

    def get_navbar_tree(self) -> dict[str, Any]:
        fresh = self._build_tree()
        cached = cache_manager.get(CacheKeys.navbar())
        if (
            cached
            and cached.get("version") == fresh.get("version")
            and len(cached.get("items") or []) == len(fresh.get("items") or [])
        ):
            return cached
        cache_manager.set(CacheKeys.navbar(), fresh, ttl=NAVBAR_CACHE_TTL)
        return fresh


navbar_service = NavbarService()
