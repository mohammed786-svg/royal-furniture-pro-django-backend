from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.categories.repositories.category_repository import category_repository
from apps.categories.repositories.sub_category_repository import sub_category_repository
from apps.categories.repositories.under_sub_category_repository import under_sub_category_repository
from apps.products.repositories.brand_repository import brand_repository
from apps.products.repositories.product_child_repository import product_child_repository
from apps.products.repositories.product_repository import product_repository
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, make_slug, save_base64_image, to_db_text, unique_slug


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _maybe_image_field(value: Any, *, prefix: str) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, str) and value.startswith("data:image"):
        return save_base64_image(value, subdir="products", prefix=prefix)
    return str(value)


class ProductService:
    def _validate_category_tree(
        self,
        category_id: int,
        sub_category_id: Optional[int],
        under_sub_category_id: Optional[int],
    ) -> None:
        if not category_repository.fetch_by_id(category_id):
            raise ValidationException(details=[{"field": "categoryId", "message": "Category not found"}])

        if sub_category_id:
            sub = sub_category_repository.fetch_by_id(sub_category_id)
            if not sub or int(sub["category_id"]) != category_id:
                raise ValidationException(
                    details=[{"field": "subCategoryId", "message": "Invalid sub-category for category"}],
                )

        if under_sub_category_id:
            if not sub_category_id:
                raise ValidationException(
                    details=[{"field": "underSubCategoryId", "message": "Sub-category is required"}],
                )
            under = under_sub_category_repository.fetch_by_id(under_sub_category_id)
            if (
                not under
                or int(under["category_id"]) != category_id
                or int(under["sub_category_id"]) != sub_category_id
            ):
                raise ValidationException(
                    details=[{"field": "underSubCategoryId", "message": "Invalid under sub-category"}],
                )

    def _serialize_list_item(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["product_id"]),
            "name": from_db_text(row.get("name")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "sku": from_db_text(row.get("sku")) or "",
            "shortDescription": from_db_text(row.get("short_description")),
            "basePrice": float(row.get("base_price") or 0),
            "salePrice": float(row.get("sale_price") or 0),
            "mrp": float(row.get("mrp") or 0),
            "categoryId": str(row["category_id"]),
            "categoryName": from_db_text(row.get("category_name")) or "",
            "subCategoryId": str(row["sub_category_id"]) if row.get("sub_category_id") else None,
            "subCategoryName": from_db_text(row.get("sub_category_name")),
            "underSubCategoryId": (
                str(row["under_sub_category_id"]) if row.get("under_sub_category_id") else None
            ),
            "underSubCategoryName": from_db_text(row.get("under_sub_category_name")),
            "brandId": str(row["brand_id"]) if row.get("brand_id") else None,
            "brandName": from_db_text(row.get("brand_name")),
            "primaryImageUrl": from_db_text(row.get("primary_image_url")),
            "isFeatured": bool(row.get("is_featured")),
            "isNewArrival": bool(row.get("is_new_arrival")),
            "isBestSeller": bool(row.get("is_best_seller")),
            "isTrending": bool(row.get("is_trending")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _serialize_image(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["product_image_id"]),
            "imageUrl": from_db_text(row.get("image_url")),
            "altText": from_db_text(row.get("alt_text")),
            "imageType": from_db_text(row.get("image_type")),
            "isPrimary": bool(row.get("is_primary")),
            "is360": bool(row.get("is_360")),
            "displayOrder": int(row.get("display_order") or 0),
        }

    def _serialize_variant(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["product_variant_id"]),
            "variantName": from_db_text(row.get("variant_name")) or "",
            "sku": from_db_text(row.get("sku")) or "",
            "barcode": from_db_text(row.get("barcode")),
            "color": from_db_text(row.get("color")),
            "fabric": from_db_text(row.get("fabric")),
            "size": from_db_text(row.get("size")),
            "material": from_db_text(row.get("material")),
            "price": float(row.get("price") or 0),
            "salePrice": float(row.get("sale_price") or 0),
            "mrp": float(row.get("mrp") or 0),
            "weight": float(row.get("weight") or 0),
            "dimensions": from_db_text(row.get("dimensions")),
            "isDefault": bool(row.get("is_default")),
            "isActive": bool(row.get("is_active")),
        }

    def _serialize_spec(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["product_specification_id"]),
            "specGroup": from_db_text(row.get("spec_group")) or "",
            "specKey": from_db_text(row.get("spec_key")) or "",
            "specValue": from_db_text(row.get("spec_value")) or "",
            "displayOrder": int(row.get("display_order") or 0),
        }

    def _serialize_feature(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["product_feature_id"]),
            "featureTitle": from_db_text(row.get("feature_title")) or "",
            "featureDescription": from_db_text(row.get("feature_description")) or "",
            "iconUrl": from_db_text(row.get("icon_url")),
            "displayOrder": int(row.get("display_order") or 0),
        }

    def _serialize_detail(self, row: dict[str, Any]) -> dict[str, Any]:
        product_id = int(row["product_id"])
        base = self._serialize_list_item(row)
        base.update({
            "hsnCode": from_db_text(row.get("hsn_code")),
            "barcode": from_db_text(row.get("barcode")),
            "longDescription": from_db_text(row.get("long_description")),
            "material": from_db_text(row.get("material")),
            "fabric": from_db_text(row.get("fabric")),
            "color": from_db_text(row.get("color")),
            "dimensions": from_db_text(row.get("dimensions")),
            "weight": float(row.get("weight") or 0),
            "assemblyRequired": bool(row.get("assembly_required")),
            "warranty": from_db_text(row.get("warranty")),
            "countryOfOrigin": from_db_text(row.get("country_of_origin")),
            "gstPercent": float(row.get("gst_percent") or 0),
            "seoTitle": from_db_text(row.get("seo_title")),
            "seoDescription": from_db_text(row.get("seo_description")),
            "seoKeywords": from_db_text(row.get("seo_keywords")),
            "images": [
                self._serialize_image(r) for r in product_child_repository.list_images(product_id)
            ],
            "variants": [
                self._serialize_variant(r) for r in product_child_repository.list_variants(product_id)
            ],
            "specifications": [
                self._serialize_spec(r)
                for r in product_child_repository.list_specifications(product_id)
            ],
            "features": [
                self._serialize_feature(r) for r in product_child_repository.list_features(product_id)
            ],
        })
        return base

    def list_products(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        for key in ("category_id", "sub_category_id", "under_sub_category_id", "brand_id"):
            if kwargs.get(key) is not None:
                params[key] = kwargs[key]
        rows, total = product_repository.list_paginated(**params)
        page = params["page"]
        page_size = params["page_size"]
        return {
            "items": [self._serialize_list_item(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_product(self, product_id: int) -> dict[str, Any]:
        row = product_repository.fetch_by_id(product_id)
        if not row:
            raise NotFoundException("Product not found")
        return self._serialize_detail(row)

    def get_form_options(self) -> dict[str, Any]:
        from apps.categories.services.category_service import category_service

        return {
            "brands": [
                {
                    "id": str(b["brand_id"]),
                    "name": from_db_text(b.get("name")) or "",
                    "slug": from_db_text(b.get("slug")) or "",
                }
                for b in brand_repository.list_options()
            ],
            **category_service.get_options(),
            **category_service.get_sub_category_options(),
            "underSubCategories": [
                {
                    "id": str(row["under_sub_category_id"]),
                    "categoryId": str(row["category_id"]),
                    "subCategoryId": str(row["sub_category_id"]),
                    "categoryName": from_db_text(row.get("category_name")) or "",
                    "subCategoryName": from_db_text(row.get("sub_category_name")) or "",
                    "name": from_db_text(row.get("name")) or "",
                    "slug": from_db_text(row.get("slug")) or "",
                }
                for row in under_sub_category_repository.list_options()
            ],
        }

    def _build_product_row(self, payload: dict[str, Any], *, product_id: Optional[int] = None) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        sku = (payload.get("sku") or "").strip()
        if not name:
            raise ValidationException(details=[{"field": "name", "message": "Product name is required"}])
        if not sku:
            raise ValidationException(details=[{"field": "sku", "message": "SKU is required"}])

        category_id = _optional_int(payload.get("categoryId"))
        if not category_id:
            raise ValidationException(details=[{"field": "categoryId", "message": "Category is required"}])

        sub_category_id = _optional_int(payload.get("subCategoryId"))
        under_sub_category_id = _optional_int(payload.get("underSubCategoryId"))
        self._validate_category_tree(category_id, sub_category_id, under_sub_category_id)

        brand_id = _optional_int(payload.get("brandId"))
        if brand_id and not any(b["brand_id"] == brand_id for b in brand_repository.list_options()):
            raise ValidationException(details=[{"field": "brandId", "message": "Brand not found"}])

        base_slug = make_slug((payload.get("slug") or "").strip() or name)
        slug = unique_slug(
            base_slug,
            lambda s: product_repository.slug_exists(s, exclude_id=product_id),
        )
        if product_repository.sku_exists(sku, exclude_id=product_id):
            raise ValidationException(details=[{"field": "sku", "message": "SKU already exists"}])

        return {
            "brand_id": brand_id,
            "category_id": category_id,
            "sub_category_id": sub_category_id,
            "under_sub_category_id": under_sub_category_id,
            "name": to_db_text(name),
            "slug": slug,
            "sku": to_db_text(sku),
            "hsn_code": to_db_text(payload.get("hsnCode")),
            "barcode": to_db_text(payload.get("barcode")),
            "short_description": to_db_text(payload.get("shortDescription")),
            "long_description": to_db_text(payload.get("longDescription")),
            "material": to_db_text(payload.get("material")),
            "fabric": to_db_text(payload.get("fabric")),
            "color": to_db_text(payload.get("color")),
            "dimensions": to_db_text(payload.get("dimensions")),
            "weight": _optional_float(payload.get("weight")),
            "assembly_required": bool(payload.get("assemblyRequired", False)),
            "warranty": to_db_text(payload.get("warranty")),
            "country_of_origin": to_db_text(payload.get("countryOfOrigin")),
            "base_price": _optional_float(payload.get("basePrice")),
            "sale_price": _optional_float(payload.get("salePrice")),
            "mrp": _optional_float(payload.get("mrp")),
            "gst_percent": _optional_float(payload.get("gstPercent")),
            "seo_title": to_db_text(payload.get("seoTitle")),
            "seo_description": to_db_text(payload.get("seoDescription")),
            "seo_keywords": to_db_text(payload.get("seoKeywords")),
            "is_featured": bool(payload.get("isFeatured", False)),
            "is_new_arrival": bool(payload.get("isNewArrival", False)),
            "is_best_seller": bool(payload.get("isBestSeller", False)),
            "is_trending": bool(payload.get("isTrending", False)),
            "is_active": bool(payload.get("isActive", True)),
        }

    def _save_children(self, product_id: int, payload: dict[str, Any], *, conn) -> None:
        product_child_repository.soft_delete_images(product_id, conn=conn)
        product_child_repository.soft_delete_variants(product_id, conn=conn)
        product_child_repository.soft_delete_specifications(product_id, conn=conn)
        product_child_repository.soft_delete_features(product_id, conn=conn)

        images = payload.get("images") or []
        for idx, image in enumerate(images):
            url = image.get("imageUrl")
            if not url:
                continue
            product_child_repository.insert_image(
                {
                    "product_id": product_id,
                    "product_variant_id": None,
                    "image_url": _maybe_image_field(url, prefix=f"product-{product_id}"),
                    "alt_text": to_db_text(image.get("altText") or payload.get("name")),
                    "image_type": to_db_text(image.get("imageType") or "gallery"),
                    "is_360": bool(image.get("is360", False)),
                    "is_primary": bool(image.get("isPrimary", idx == 0)),
                    "display_order": int(image.get("displayOrder", idx)),
                    "is_active": True,
                },
                conn=conn,
            )

        variants = payload.get("variants") or []
        if not variants:
            variants = [{
                "variantName": "Default",
                "sku": f"{payload.get('sku')}-DEFAULT",
                "price": payload.get("basePrice", 0),
                "salePrice": payload.get("salePrice", 0),
                "mrp": payload.get("mrp", 0),
                "isDefault": True,
            }]
        for variant in variants:
            variant_sku = (variant.get("sku") or "").strip() or f"{payload.get('sku')}-V"
            product_child_repository.insert_variant(
                {
                    "product_id": product_id,
                    "variant_name": to_db_text(variant.get("variantName") or "Default"),
                    "sku": to_db_text(variant_sku),
                    "barcode": to_db_text(variant.get("barcode")),
                    "color": to_db_text(variant.get("color") or payload.get("color")),
                    "fabric": to_db_text(variant.get("fabric") or payload.get("fabric")),
                    "size": to_db_text(variant.get("size")),
                    "material": to_db_text(variant.get("material") or payload.get("material")),
                    "price": _optional_float(variant.get("price"), _optional_float(payload.get("basePrice"))),
                    "sale_price": _optional_float(variant.get("salePrice"), _optional_float(payload.get("salePrice"))),
                    "mrp": _optional_float(variant.get("mrp"), _optional_float(payload.get("mrp"))),
                    "weight": _optional_float(variant.get("weight"), _optional_float(payload.get("weight"))),
                    "dimensions": to_db_text(variant.get("dimensions") or payload.get("dimensions")),
                    "is_default": bool(variant.get("isDefault", False)),
                    "is_active": bool(variant.get("isActive", True)),
                },
                conn=conn,
            )

        for idx, spec in enumerate(payload.get("specifications") or []):
            key = (spec.get("specKey") or "").strip()
            if not key:
                continue
            product_child_repository.insert_specification(
                {
                    "product_id": product_id,
                    "spec_group": to_db_text(spec.get("specGroup") or "General"),
                    "spec_key": to_db_text(key),
                    "spec_value": to_db_text(spec.get("specValue")),
                    "display_order": int(spec.get("displayOrder", idx)),
                    "is_active": True,
                },
                conn=conn,
            )

        for idx, feature in enumerate(payload.get("features") or []):
            title = (feature.get("featureTitle") or "").strip()
            if not title:
                continue
            icon_url = feature.get("iconUrl")
            product_child_repository.insert_feature(
                {
                    "product_id": product_id,
                    "feature_title": to_db_text(title),
                    "feature_description": to_db_text(feature.get("featureDescription")),
                    "icon_url": (
                        _maybe_image_field(icon_url, prefix=f"feature-{product_id}")
                        if icon_url and str(icon_url).startswith("data:image")
                        else to_db_text(icon_url)
                    ),
                    "display_order": int(feature.get("displayOrder", idx)),
                    "is_active": True,
                },
                conn=conn,
            )

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_row = self._build_product_row(payload)
        with atomic() as conn:
            created = product_repository.create(product_row, conn=conn)
            product_id = int(created["product_id"])
            self._save_children(product_id, payload, conn=conn)
        return self.get_product(product_id)

    def update_product(self, product_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not product_repository.fetch_by_id(product_id):
            raise NotFoundException("Product not found")
        product_row = self._build_product_row(payload, product_id=product_id)
        with atomic() as conn:
            product_repository.update(product_id, product_row, conn=conn)
            self._save_children(product_id, payload, conn=conn)
        return self.get_product(product_id)

    def delete_product(self, product_id: int) -> None:
        if not product_repository.soft_delete(product_id):
            raise NotFoundException("Product not found")


product_service = ProductService()
