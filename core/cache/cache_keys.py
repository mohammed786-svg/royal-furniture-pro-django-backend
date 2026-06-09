"""Redis cache key registry — align with frontend cache strategy."""
from __future__ import annotations


class CacheKeys:
    PREFIX = "royal"

    @staticmethod
    def navbar() -> str:
        return f"{CacheKeys.PREFIX}:navbar:tree"

    @staticmethod
    def category(slug: str) -> str:
        return f"{CacheKeys.PREFIX}:category:{slug}"

    @staticmethod
    def product(slug: str) -> str:
        return f"{CacheKeys.PREFIX}:product:{slug}"

    @staticmethod
    def product_inventory(product_id: int | str) -> str:
        return f"{CacheKeys.PREFIX}:product:inventory:{product_id}"

    @staticmethod
    def cart_guest(session_id: str) -> str:
        return f"{CacheKeys.PREFIX}:cart:session:{session_id}"

    @staticmethod
    def cart_customer(customer_id: int | str) -> str:
        return f"{CacheKeys.PREFIX}:cart:customer:{customer_id}"

    @staticmethod
    def wishlist_guest(session_id: str) -> str:
        return f"{CacheKeys.PREFIX}:wishlist:session:{session_id}"

    @staticmethod
    def wishlist_customer(customer_id: int | str) -> str:
        return f"{CacheKeys.PREFIX}:wishlist:customer:{customer_id}"

    @staticmethod
    def inventory(product_id: int | str, variant_id: int | str | None = None) -> str:
        suffix = f"{product_id}:{variant_id or 0}"
        return f"{CacheKeys.PREFIX}:inventory:{suffix}"

    @staticmethod
    def otp(phone: str, purpose: str) -> str:
        return f"{CacheKeys.PREFIX}:otp:{phone}:{purpose}"

    @staticmethod
    def session(user_id: int | str) -> str:
        return f"{CacheKeys.PREFIX}:admin:session:{user_id}"

    @staticmethod
    def admin_user(user_id: int | str) -> str:
        return f"{CacheKeys.PREFIX}:admin:user:{user_id}"

    @staticmethod
    def admin_permissions(role_code: str) -> str:
        return f"{CacheKeys.PREFIX}:admin:permissions:{role_code}"

    @staticmethod
    def search(query: str) -> str:
        return f"{CacheKeys.PREFIX}:search:{query}"

    @staticmethod
    def notification(customer_id: int | str) -> str:
        return f"{CacheKeys.PREFIX}:notification:{customer_id}"
