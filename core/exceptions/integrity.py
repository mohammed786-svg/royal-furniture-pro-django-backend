"""Map database integrity violations to API-friendly validation errors."""
from __future__ import annotations

_CONSTRAINT_FIELD_MESSAGES: dict[str, tuple[str, str]] = {
    "uq_categorytbl_slug": ("slug", "Category slug already exists"),
    "uq_sub_categorytbl_slug": ("slug", "Sub-category slug already exists for this category"),
    "uq_under_sub_categorytbl_slug": ("slug", "Under sub-category slug already exists"),
    "uq_producttbl_slug": ("slug", "Product slug already exists"),
    "uq_producttbl_sku": ("sku", "SKU already exists"),
    "uq_product_varianttbl_sku": ("sku", "Variant SKU already exists"),
    "uq_brandtbl_slug": ("slug", "Brand slug already exists"),
    "uq_product_tagtbl_slug": ("slug", "Tag slug already exists"),
    "uq_cms_pagetbl_slug": ("slug", "Page slug already exists"),
    "uq_cms_pagetbl_code": ("pageCode", "Page code already exists"),
    "uq_coupontbl_code": ("couponCode", "Coupon code already exists"),
    "uq_warehousetbl_code": ("warehouseCode", "Warehouse code already exists"),
    "uq_order_statustbl_code": ("statusCode", "Status code already exists"),
    "uq_settingstbl_key": ("settingKey", "Setting key already exists"),
}


def parse_integrity_error(exc: Exception) -> tuple[str, list[dict[str, str]]]:
    raw = str(getattr(exc, "__cause__", None) or exc)
    for constraint, (field, message) in _CONSTRAINT_FIELD_MESSAGES.items():
        if constraint in raw:
            return message, [{"field": field, "message": message}]
    if "duplicate key" in raw.lower() or "unique constraint" in raw.lower():
        return "This value already exists", [{"message": "Already exists"}]
    return "Database constraint violation", []
