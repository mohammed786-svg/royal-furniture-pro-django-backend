from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from apps.marketing.services.storefront_banner_service import storefront_banner_service
from apps.storefront.repositories.home_repository import storefront_home_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.exceptions.base import NotFoundException
from core.helpers.text import from_db_text

HOME_CACHE_TTL = 3600
PROMO_POSITION = "HOME_PROMO"
OFFER_POSITION = "HOME_OFFER"
SEO_PAGE_CODE = "HOME_SEO"
SETTINGS_GROUP = "homepage"


def _calc_discount(sale_price: float, mrp: float) -> Optional[str]:
    if mrp <= 0 or sale_price <= 0 or sale_price >= mrp:
        return None
    pct = int(round((1 - sale_price / mrp) * 100))
    if pct <= 0:
        return None
    return f"{pct}% off"


def _product_badge(row: dict[str, Any]) -> Optional[str]:
    if row.get("is_new_arrival"):
        return "New Arrival"
    if row.get("is_featured"):
        return "Online Exclusive"
    if row.get("is_best_seller"):
        return "Best Seller"
    if row.get("is_trending"):
        return "Trending"
    return None


def _serialize_product(row: dict[str, Any]) -> dict[str, Any]:
    sale_price = float(row.get("sale_price") or 0)
    base_price = float(row.get("base_price") or 0)
    mrp = float(row.get("mrp") or 0)
    price = sale_price if sale_price > 0 else base_price
    slug = from_db_text(row.get("slug")) or ""
    category_slug = from_db_text(row.get("category_slug")) or ""
    sub_slug = from_db_text(row.get("sub_category_slug")) or ""
    payload = {
        "id": str(row["product_id"]),
        "name": from_db_text(row.get("name")) or "",
        "slug": slug,
        "href": f"/product/{slug}" if slug else "#",
        "imageUrl": from_db_text(row.get("primary_image_url")),
        "price": price,
        "mrp": mrp,
        "collection": from_db_text(row.get("brand_name")),
        "badge": _product_badge(row),
        "discount": _calc_discount(price, mrp),
    }
    if category_slug or row.get("category_name"):
        payload["categoryId"] = str(row["category_id"]) if row.get("category_id") else None
        payload["categoryName"] = from_db_text(row.get("category_name")) or "Furniture"
        payload["categorySlug"] = category_slug
        payload["categoryHref"] = f"/{category_slug}" if category_slug else "#"
        payload["subCategoryName"] = from_db_text(row.get("sub_category_name")) or ""
        payload["subCategorySlug"] = sub_slug
    return payload


def _serialize_category(row: dict[str, Any], *, sub: bool = False) -> dict[str, Any]:
    slug = from_db_text(row.get("slug")) or ""
    if sub:
        category_slug = from_db_text(row.get("category_slug")) or "decor"
        href = f"/{category_slug}/{slug}" if slug else "#"
        image = from_db_text(row.get("image_url"))
        return {
            "id": str(row["sub_category_id"]),
            "name": from_db_text(row.get("name")) or "",
            "slug": slug,
            "href": href,
            "imageUrl": image,
        }
    image = from_db_text(row.get("image_url")) or from_db_text(row.get("icon_url"))
    return {
        "id": str(row["category_id"]),
        "name": from_db_text(row.get("name")) or "",
        "slug": slug,
        "href": f"/{slug}" if slug else "#",
        "imageUrl": image,
    }


def _serialize_deal_product(row: dict[str, Any]) -> dict[str, Any]:
    product = _serialize_product(row)
    return {
        **product,
        "label": product["name"],
    }


def _serialize_testimonial(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["testimonial_id"]),
        "name": from_db_text(row.get("customer_name")) or "",
        "city": from_db_text(row.get("location")) or "",
        "text": from_db_text(row.get("testimonial_text")) or "",
        "imageUrl": from_db_text(row.get("customer_image")),
        "rating": float(row.get("rating") or 0),
    }


def _parse_json_setting(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


class StorefrontHomeService:
    def _build_features(self) -> list[dict[str, Any]]:
        rows = storefront_home_repository.list_settings_by_group(SETTINGS_GROUP)
        features: list[dict[str, Any]] = []
        for row in rows:
            key = from_db_text(row.get("setting_key")) or ""
            if not key.startswith("feature."):
                continue
            payload = _parse_json_setting(from_db_text(row.get("setting_value")))
            if isinstance(payload, dict) and payload.get("label"):
                features.append({
                    "label": str(payload.get("label")),
                    "imageUrl": payload.get("imageUrl"),
                })
        return features

    def _build_offer_bar(self) -> Optional[dict[str, Any]]:
        rows = storefront_home_repository.list_settings_by_group(SETTINGS_GROUP)
        for row in rows:
            key = from_db_text(row.get("setting_key")) or ""
            if key != "offer_bar":
                continue
            payload = _parse_json_setting(from_db_text(row.get("setting_value")))
            if isinstance(payload, dict):
                return payload
        banners = storefront_banner_service.get_banners_for_position(OFFER_POSITION).get("items", [])
        if not banners:
            return None
        return {"banners": banners}

    def _build_seo_content(self) -> Optional[dict[str, Any]]:
        page = storefront_home_repository.fetch_cms_page_by_code(SEO_PAGE_CODE)
        if not page:
            return None
        return {
            "title": from_db_text(page.get("title")) or "",
            "content": from_db_text(page.get("content")) or "",
            "seoTitle": from_db_text(page.get("seo_title")),
            "seoDescription": from_db_text(page.get("seo_description")),
        }

    def _build_payload(self) -> dict[str, Any]:
        promo = storefront_banner_service.get_banners_for_position(PROMO_POSITION)
        return {
            "promoBanners": promo.get("items", []),
            "offerBar": self._build_offer_bar(),
            "features": self._build_features(),
            "popularCategories": [
                _serialize_category(row)
                for row in storefront_home_repository.list_featured_categories(limit=12)
            ],
            "onlineExclusive": [
                _serialize_product(row)
                for row in storefront_home_repository.list_storefront_products(
                    limit=8, is_featured=True
                )
            ],
            "spotlight": [
                _serialize_product(row)
                for row in storefront_home_repository.list_storefront_products(
                    limit=6, is_trending=True
                )
            ],
            "bestSellers": [
                _serialize_product(row)
                for row in storefront_home_repository.list_storefront_products(
                    limit=8, is_best_seller=True
                )
            ],
            "newArrivals": [
                _serialize_product(row)
                for row in storefront_home_repository.list_storefront_products(
                    limit=8, is_new_arrival=True
                )
            ],
            "decorCategories": [
                _serialize_category(row, sub=True)
                for row in storefront_home_repository.list_decor_sub_categories(limit=8)
            ],
            "limitedDeals": [
                _serialize_deal_product(row)
                for row in storefront_home_repository.list_storefront_products(
                    limit=6, on_sale=True
                )
            ],
            "testimonials": [
                _serialize_testimonial(row)
                for row in storefront_home_repository.list_featured_testimonials(limit=10)
            ],
            "seoContent": self._build_seo_content(),
            "version": storefront_home_repository.fetch_home_version_epoch(),
            "cachedAt": datetime.now(timezone.utc).isoformat(),
        }

    def get_homepage(self, *, use_cache: bool = True) -> dict[str, Any]:
        fresh = self._build_payload()
        if not use_cache:
            return fresh

        cached = cache_manager.get(CacheKeys.storefront_home())
        if cached and cached.get("version") == fresh.get("version"):
            return cached
        cache_manager.set(CacheKeys.storefront_home(), fresh, ttl=HOME_CACHE_TTL)
        return fresh

    def get_collection(self, kind: str) -> dict[str, Any]:
        """Full New Arrivals / Online Exclusive listing, grouped by category."""
        kind = (kind or "").strip().lower().replace("_", "-")
        configs = {
            "new-arrivals": {
                "title": "New Arrivals",
                "description": "Browse all new arrival furniture, organised by category.",
                "filters": {"is_new_arrival": True},
            },
            "online-exclusive": {
                "title": "Online Exclusive",
                "description": "Shop online-exclusive furniture, organised by category.",
                "filters": {"is_featured": True},
            },
        }
        config = configs.get(kind)
        if not config:
            raise NotFoundException("Collection not found")

        rows = storefront_home_repository.list_storefront_products(
            limit=240,
            **config["filters"],
        )
        groups_map: dict[str, dict[str, Any]] = {}
        for row in rows:
            product = _serialize_product(row)
            cat_key = product.get("categorySlug") or product.get("categoryName") or "other"
            if cat_key not in groups_map:
                groups_map[cat_key] = {
                    "categoryId": product.get("categoryId"),
                    "categoryName": product.get("categoryName") or "Furniture",
                    "categorySlug": product.get("categorySlug") or "",
                    "categoryHref": product.get("categoryHref") or "#",
                    "products": [],
                }
            groups_map[cat_key]["products"].append(product)

        groups = list(groups_map.values())
        total = sum(len(g["products"]) for g in groups)
        return {
            "kind": kind,
            "title": config["title"],
            "description": config["description"],
            "totalProducts": total,
            "groups": groups,
        }

    def invalidate_homepage_cache(self) -> None:
        cache_manager.delete(CacheKeys.storefront_home())


storefront_home_service = StorefrontHomeService()
