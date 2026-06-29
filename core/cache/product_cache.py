"""Invalidate storefront product cache when catalog or inventory changes."""
from __future__ import annotations

from apps.products.repositories.product_repository import product_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.helpers.text import from_db_text


def invalidate_product_cache_by_id(product_id: int) -> None:
    row = product_repository.fetch_by_id(product_id)
    if not row:
        return
    slug = from_db_text(row.get("slug"))
    if slug:
        cache_manager.delete(CacheKeys.product(slug))
