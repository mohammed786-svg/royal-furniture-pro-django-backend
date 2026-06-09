from __future__ import annotations

from typing import Any

from core.database import select_one, select_query


class RoleRepository:
    schema = "royal"
    table = "roletbl"
    ADMIN_ROLE_CODES = ("SUPER_ADMIN", "ADMIN_MANAGER")

    def list_admin_roles(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT role_id, role_name, role_code, description, display_order
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE
              AND is_active = TRUE
              AND role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
            ORDER BY display_order, role_name
        """
        return select_query(sql)

    def fetch_admin_role_by_id(self, role_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT role_id, role_name, role_code, description
            FROM {self.schema}.{self.table}
            WHERE role_id = %s
              AND is_deleted = FALSE
              AND is_active = TRUE
              AND role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        return select_one(sql, [role_id])

    def fetch_admin_role_by_code(self, role_code: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT role_id, role_name, role_code, description
            FROM {self.schema}.{self.table}
            WHERE role_code = %s
              AND is_deleted = FALSE
              AND is_active = TRUE
              AND role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        return select_one(sql, [role_code])


role_repository = RoleRepository()
