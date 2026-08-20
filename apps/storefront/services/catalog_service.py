from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from apps.categories.repositories.category_repository import category_repository
from apps.categories.repositories.sub_category_repository import sub_category_repository
from apps.categories.repositories.under_sub_category_repository import under_sub_category_repository
from apps.products.repositories.product_child_repository import product_child_repository
from apps.products.repositories.product_repository import product_repository
from apps.storefront.repositories.catalog_repository import storefront_catalog_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.exceptions.base import NotFoundException
from core.helpers.text import from_db_text

CATALOG_CACHE_TTL = 1800
SORT_OPTIONS = [
    "Recommended",
    "Price: Low to High",
    "Price: High to Low",
    "Newest",
    "Discount",
]

_SORT_PARAM = {
    "recommended": "recommended",
    "price: low to high": "price-low",
    "price-low": "price-low",
    "price: high to low": "price-high",
    "price-high": "price-high",
    "newest": "newest",
    "discount": "discount",
}


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


def _serialize_plp_product(row: dict[str, Any], *, category_slug: str, sub_slug: str) -> dict[str, Any]:
    sale_price = float(row.get("sale_price") or 0)
    base_price = float(row.get("base_price") or 0)
    mrp = float(row.get("mrp") or 0)
    price = sale_price if sale_price > 0 else base_price
    slug = from_db_text(row.get("slug")) or ""
    return {
        "id": str(row["product_id"]),
        "name": from_db_text(row.get("name")) or "",
        "slug": slug,
        "href": f"/product/{slug}" if slug else "#",
        "imageUrl": from_db_text(row.get("primary_image_url")),
        "price": price,
        "mrp": mrp,
        "badge": _product_badge(row),
        "discount": _calc_discount(price, mrp),
        "collection": from_db_text(row.get("brand_name")),
        "categorySlug": category_slug,
        "subCategorySlug": sub_slug,
    }


class StorefrontCatalogService:
    def _normalize_sort(self, sort: Optional[str]) -> str:
        if not sort:
            return "recommended"
        key = sort.strip().lower()
        return _SORT_PARAM.get(key, "recommended")

    def _resolve_category(
        self,
        *,
        category_slug: str,
        category_id: Optional[int],
    ) -> dict[str, Any]:
        if category_id:
            row = category_repository.fetch_by_id(category_id)
        elif category_slug:
            row = category_repository.fetch_by_slug(category_slug)
        else:
            row = None
        if not row:
            raise NotFoundException("Category not found")
        return row

    def _resolve_sub_category(
        self,
        *,
        category_id: int,
        sub_category_slug: str,
        sub_category_id: Optional[int],
    ) -> dict[str, Any]:
        if sub_category_id:
            row = sub_category_repository.fetch_by_id(sub_category_id)
            if row and int(row["category_id"]) != category_id:
                row = None
        elif sub_category_slug:
            row = sub_category_repository.fetch_by_slug(category_id, sub_category_slug)
        else:
            row = None
        if not row:
            raise NotFoundException("Sub-category not found")
        return row

    def _humanize_slug(self, slug: str) -> str:
        return " ".join(part.capitalize() for part in slug.split("-") if part)

    def _build_listing(
        self,
        *,
        category_slug: str,
        sub_category_slug: str,
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
        under_sub_category_id: Optional[int] = None,
        under_sub_category_slug: Optional[str] = None,
        page: int,
        page_size: int,
        sort: str,
    ) -> dict[str, Any]:
        category = self._resolve_category(
            category_slug=category_slug,
            category_id=category_id,
        )
        resolved_category_id = int(category["category_id"])

        sub = self._resolve_sub_category(
            category_id=resolved_category_id,
            sub_category_slug=sub_category_slug,
            sub_category_id=sub_category_id,
        )
        resolved_sub_category_id = int(sub["sub_category_id"])

        under_filter_id: Optional[int] = None
        under_name: Optional[str] = None
        under_slug_value: Optional[str] = None

        if under_sub_category_id:
            under = under_sub_category_repository.fetch_by_id(under_sub_category_id)
            if (
                not under
                or int(under["sub_category_id"]) != resolved_sub_category_id
            ):
                raise NotFoundException("Sub-category item not found")
            under_filter_id = int(under["under_sub_category_id"])
            under_name = from_db_text(under.get("name")) or ""
            under_slug_value = from_db_text(under.get("slug")) or ""
        elif under_sub_category_slug:
            under = under_sub_category_repository.resolve_for_listing(
                resolved_sub_category_id,
                under_sub_category_slug,
            )
            if under:
                under_filter_id = int(under["under_sub_category_id"])
                under_name = from_db_text(under.get("name")) or ""
                under_slug_value = from_db_text(under.get("slug")) or under_sub_category_slug
            else:
                under_slug_value = under_sub_category_slug
                under_name = self._humanize_slug(under_sub_category_slug)

        sort_key = self._normalize_sort(sort)
        rows, total = product_repository.list_storefront_paginated(
            page=page,
            page_size=page_size,
            category_id=resolved_category_id,
            sub_category_id=resolved_sub_category_id,
            under_sub_category_id=under_filter_id,
            sort_by=sort_key,
        )

        cat_slug = from_db_text(category.get("slug")) or category_slug
        sub_slug = from_db_text(sub.get("slug")) or sub_category_slug
        under_rows = storefront_catalog_repository.list_under_sub_categories(resolved_sub_category_id)

        subcategories = [
            {
                "label": from_db_text(row.get("name")) or "",
                "imageUrl": from_db_text(row.get("image_url")),
                "href": f"/{cat_slug}/{sub_slug}/{from_db_text(row.get('slug')) or ''}",
            }
            for row in under_rows
        ]

        if not subcategories:
            sub_image = from_db_text(sub.get("image_url")) or from_db_text(sub.get("icon_url"))
            subcategories = [
                {
                    "label": from_db_text(sub.get("name")) or "",
                    "imageUrl": sub_image,
                    "href": f"/{cat_slug}/{sub_slug}",
                }
            ]

        title = under_name or from_db_text(sub.get("name")) or ""
        version = (
            f"{float(category.get('epoch') or 0):.6f}-"
            f"{float(sub.get('epoch') or 0):.6f}-"
            f"{under_filter_id or 0}-{total}"
        )

        return {
            "categoryId": str(resolved_category_id),
            "subCategoryId": str(resolved_sub_category_id),
            "underSubCategoryId": str(under_filter_id) if under_filter_id else None,
            "department": from_db_text(category.get("name")) or "",
            "category": from_db_text(sub.get("name")) or "",
            "underSubCategory": under_name,
            "title": title,
            "categorySlug": cat_slug,
            "subCategorySlug": sub_slug,
            "underSubCategorySlug": under_slug_value,
            "subcategories": subcategories,
            "products": [
                _serialize_plp_product(row, category_slug=cat_slug, sub_slug=sub_slug)
                for row in rows
            ],
            "sortOptions": SORT_OPTIONS,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
            "version": version,
            "cachedAt": datetime.now(timezone.utc).isoformat(),
        }

    def get_category_listing(
        self,
        category_slug: str,
        sub_category_slug: str,
        *,
        category_id: Optional[int] = None,
        sub_category_id: Optional[int] = None,
        under_sub_category_id: Optional[int] = None,
        under_sub_category_slug: Optional[str] = None,
        page: int = 1,
        page_size: int = 24,
        sort: Optional[str] = None,
    ) -> dict[str, Any]:
        sort_key = self._normalize_sort(sort)
        under_cache_key = (
            str(under_sub_category_id)
            if under_sub_category_id
            else (under_sub_category_slug or "").strip()
        )

        def loader() -> dict[str, Any]:
            listing = self._build_listing(
                category_slug=category_slug,
                sub_category_slug=sub_category_slug,
                category_id=category_id,
                sub_category_id=sub_category_id,
                under_sub_category_id=under_sub_category_id,
                under_sub_category_slug=under_sub_category_slug,
                page=page,
                page_size=page_size,
                sort=sort_key,
            )
            cache_manager.set(
                CacheKeys.storefront_plp_ids(
                    int(listing["categoryId"]),
                    int(listing["subCategoryId"]),
                    int(listing["underSubCategoryId"] or 0),
                    page,
                    sort_key,
                ),
                listing,
                ttl=CATALOG_CACHE_TTL,
            )
            return listing

        id_cache_key = None
        if category_id and sub_category_id:
            id_cache_key = CacheKeys.storefront_plp_ids(
                category_id,
                sub_category_id,
                under_sub_category_id or 0,
                page,
                sort_key,
            )
            cached = cache_manager.get(id_cache_key)
            if cached:
                return cached

        return cache_manager.get_or_set(
            CacheKeys.storefront_plp(
                category_slug,
                sub_category_slug,
                page,
                sort_key,
                under_cache_key,
            ),
            loader,
            ttl=CATALOG_CACHE_TTL,
        )


class StorefrontProductService:
    def _serialize_more_info(self, row: dict[str, Any], stock: int) -> list[dict[str, str]]:
        items: list[dict[str, str]] = [
            {"label": "Available Quantity", "value": str(stock)},
            {"label": "SKU", "value": from_db_text(row.get("sku")) or "—"},
        ]
        weight = float(row.get("weight") or 0)
        if weight > 0:
            items.append({"label": "Weight", "value": f"{weight:.2f} kg"})
        dimensions = from_db_text(row.get("dimensions"))
        if dimensions:
            items.append({"label": "Dimensions", "value": dimensions})
        warranty = from_db_text(row.get("warranty"))
        if warranty:
            items.append({"label": "Warranty", "value": warranty})
        material = from_db_text(row.get("material"))
        if material:
            items.append({"label": "Material", "value": material})
        items.append({
            "label": "Assembly Details",
            "value": "Installation provided by Royal Furniture Pro",
        })
        return items

    def _build_product(self, slug: str) -> dict[str, Any]:
        row = product_repository.fetch_by_slug(slug)
        if not row:
            raise NotFoundException("Product not found")

        product_id = int(row["product_id"])
        sale_price = float(row.get("sale_price") or 0)
        base_price = float(row.get("base_price") or 0)
        mrp = float(row.get("mrp") or 0)
        price = sale_price if sale_price > 0 else base_price
        stock = storefront_catalog_repository.fetch_available_stock(product_id)

        images = [
            from_db_text(img.get("image_url"))
            for img in product_child_repository.list_images(product_id)
            if from_db_text(img.get("image_url"))
        ]
        if not images:
            images = []

        features: list[dict[str, str]] = []
        for f in product_child_repository.list_features(product_id):
            label = from_db_text(f.get("feature_title")) or ""
            value = from_db_text(f.get("feature_description")) or ""
            if label or value:
                features.append({"label": label, "value": value})
        for spec in product_child_repository.list_specifications(product_id):
            group = from_db_text(spec.get("spec_group")) or ""
            key = from_db_text(spec.get("spec_key")) or ""
            value = from_db_text(spec.get("spec_value")) or ""
            if not key and not value:
                continue
            label = f"{group} - {key}" if group and group.lower() != "general" else key
            features.append({"label": label, "value": value})

        slug_value = from_db_text(row.get("slug")) or slug
        category_slug = from_db_text(row.get("category_slug")) or ""
        sub_slug = from_db_text(row.get("sub_category_slug")) or ""
        under_slug = from_db_text(row.get("under_sub_category_slug")) or ""

        return {
            "id": str(product_id),
            "slug": slug_value,
            "name": from_db_text(row.get("name")) or "",
            "images": images,
            "imageUrl": images[0] if images else None,
            "price": price,
            "mrp": mrp,
            "discount": _calc_discount(price, mrp),
            "badge": _product_badge(row),
            "inStock": stock > 0,
            "availableStock": stock,
            "sku": from_db_text(row.get("sku")) or "",
            "categoryId": str(row["category_id"]) if row.get("category_id") else None,
            "subCategoryId": str(row["sub_category_id"]) if row.get("sub_category_id") else None,
            "underSubCategoryId": (
                str(row["under_sub_category_id"]) if row.get("under_sub_category_id") else None
            ),
            "department": from_db_text(row.get("category_name")) or "",
            "category": from_db_text(row.get("sub_category_name")) or "",
            "categorySlug": category_slug,
            "subCategorySlug": sub_slug,
            "underSubCategorySlug": under_slug,
            "emiMonthly": int(round(price / 9)) if price > 0 else 0,
            "description": from_db_text(row.get("long_description"))
            or from_db_text(row.get("short_description"))
            or "",
            "features": features,
            "moreInfo": self._serialize_more_info(row, stock),
            "specifications": [
                {
                    "group": from_db_text(spec.get("spec_group")) or "General",
                    "key": from_db_text(spec.get("spec_key")) or "",
                    "value": from_db_text(spec.get("spec_value")) or "",
                }
                for spec in product_child_repository.list_specifications(product_id)
            ],
            "version": f"{float(row.get('epoch') or 0):.6f}",
            "cachedAt": datetime.now(timezone.utc).isoformat(),
        }

    def get_product_by_slug(self, slug: str) -> dict[str, Any]:
        return cache_manager.get_or_set(
            CacheKeys.product(slug),
            lambda: self._build_product(slug),
            ttl=CATALOG_CACHE_TTL,
        )


storefront_catalog_service = StorefrontCatalogService()
storefront_product_service = StorefrontProductService()
