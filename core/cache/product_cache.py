"""Invalidate storefront product + category listing caches when catalog changes."""
from __future__ import annotations

from typing import Any, Optional

from apps.products.repositories.product_repository import product_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.helpers.text import from_db_text


def invalidate_plp_cache_for_category(
    *,
    category_id: Optional[int] = None,
    sub_category_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    sub_category_slug: Optional[str] = None,
) -> None:
    """Clear all PLP Redis keys for a category / sub-category pair."""
    if category_id and sub_category_id:
        cache_manager.delete_pattern(
            f"{CacheKeys.PREFIX}:storefront:plp:id:{category_id}:{sub_category_id}:*"
        )
    if category_slug and sub_category_slug:
        cache_manager.delete_pattern(
            f"{CacheKeys.PREFIX}:storefront:plp:{category_slug}:{sub_category_slug}*"
        )


def invalidate_storefront_home_cache() -> None:
    cache_manager.delete(CacheKeys.storefront_home())


def invalidate_product_cache_by_id(
    product_id: int,
    *,
    previous_row: Optional[dict[str, Any]] = None,
) -> None:
    row = product_repository.fetch_by_id(product_id) or previous_row
    if not row:
        return

    slug = from_db_text(row.get("slug"))
    if slug:
        cache_manager.delete(CacheKeys.product(slug))

    category_id = int(row["category_id"]) if row.get("category_id") else None
    sub_category_id = int(row["sub_category_id"]) if row.get("sub_category_id") else None
    category_slug = from_db_text(row.get("category_slug")) or None
    sub_category_slug = from_db_text(row.get("sub_category_slug")) or None

    invalidate_plp_cache_for_category(
        category_id=category_id,
        sub_category_id=sub_category_id,
        category_slug=category_slug,
        sub_category_slug=sub_category_slug,
    )

    # If product moved categories, also clear the previous PLP keys.
    if previous_row:
        prev_category_id = (
            int(previous_row["category_id"]) if previous_row.get("category_id") else None
        )
        prev_sub_category_id = (
            int(previous_row["sub_category_id"])
            if previous_row.get("sub_category_id")
            else None
        )
        prev_category_slug = from_db_text(previous_row.get("category_slug")) or None
        prev_sub_category_slug = from_db_text(previous_row.get("sub_category_slug")) or None
        if (
            prev_category_id != category_id
            or prev_sub_category_id != sub_category_id
            or prev_category_slug != category_slug
            or prev_sub_category_slug != sub_category_slug
        ):
            invalidate_plp_cache_for_category(
                category_id=prev_category_id,
                sub_category_id=prev_sub_category_id,
                category_slug=prev_category_slug,
                sub_category_slug=prev_sub_category_slug,
            )

    invalidate_storefront_home_cache()
