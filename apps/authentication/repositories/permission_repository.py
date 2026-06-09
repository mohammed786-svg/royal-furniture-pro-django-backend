from __future__ import annotations

from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.database import select_query


class PermissionRepository:
    schema = "royal"

    def fetch_menu_permissions_for_role(self, role_code: str) -> list[str]:
        cache_key = CacheKeys.admin_permissions(role_code)

        def _load() -> list[str]:
            if role_code == "SUPER_ADMIN":
                sql = f"""
                    SELECT permission_code
                    FROM {self.schema}.permissiontbl
                    WHERE module_name = 'admin_menu'
                      AND is_deleted = FALSE
                      AND is_active = TRUE
                    ORDER BY permission_code
                """
                rows = select_query(sql)
                return [row["permission_code"] for row in rows]

            sql = f"""
                SELECT p.permission_code
                FROM {self.schema}.role_permissiontbl rp
                INNER JOIN {self.schema}.roletbl r ON r.role_id = rp.role_id
                INNER JOIN {self.schema}.permissiontbl p ON p.permission_id = rp.permission_id
                WHERE r.role_code = %s
                  AND p.module_name = 'admin_menu'
                  AND rp.is_deleted = FALSE
                  AND rp.is_active = TRUE
                  AND p.is_deleted = FALSE
                  AND p.is_active = TRUE
                ORDER BY p.permission_code
            """
            rows = select_query(sql, [role_code])
            return [row["permission_code"] for row in rows]

        return cache_manager.get_or_set(cache_key, _load, ttl=300)

    def invalidate_role_permissions(self, role_code: str) -> None:
        cache_manager.delete(CacheKeys.admin_permissions(role_code))


permission_repository = PermissionRepository()
