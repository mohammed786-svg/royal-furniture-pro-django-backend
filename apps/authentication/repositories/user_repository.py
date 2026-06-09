from __future__ import annotations

from typing import Any, Optional

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class UserRepository:
    schema = "royal"

    def fetch_admin_by_email(self, email: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                u.user_id,
                u.email,
                u.password_hash,
                u.full_name,
                u.phone,
                u.avatar_url,
                u.is_active,
                r.role_id,
                r.role_code,
                r.role_name
            FROM {self.schema}.usertbl u
            INNER JOIN {self.schema}.roletbl r ON r.role_id = u.role_id
            WHERE LOWER(u.email) = LOWER(%s)
              AND u.is_deleted = FALSE
              AND u.is_active = TRUE
              AND r.is_deleted = FALSE
              AND r.is_active = TRUE
              AND r.role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        return select_one(sql, [email])

    def fetch_admin_auth_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                u.user_id,
                u.email,
                u.password_hash,
                u.full_name,
                u.phone,
                u.avatar_url,
                u.is_active,
                r.role_id,
                r.role_code,
                r.role_name
            FROM {self.schema}.usertbl u
            INNER JOIN {self.schema}.roletbl r ON r.role_id = u.role_id
            WHERE u.user_id = %s
              AND u.is_deleted = FALSE
              AND u.is_active = TRUE
              AND r.is_deleted = FALSE
              AND r.role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        return select_one(sql, [user_id])

    def fetch_admin_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                u.user_id,
                u.email,
                u.full_name,
                u.phone,
                u.avatar_url,
                u.is_active,
                r.role_id,
                r.role_code,
                r.role_name
            FROM {self.schema}.usertbl u
            INNER JOIN {self.schema}.roletbl r ON r.role_id = u.role_id
            WHERE u.user_id = %s
              AND u.is_deleted = FALSE
              AND u.is_active = TRUE
              AND r.is_deleted = FALSE
              AND r.role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        return select_one(sql, [user_id])

    def record_login(self, user_id: int) -> None:
        sql = f"""
            UPDATE {self.schema}.usertbl
            SET last_login_at = NOW(),
                login_count = COALESCE(login_count, 0) + 1,
                updated_at = NOW()
            WHERE user_id = %s
        """
        update_query(sql, [user_id])

    def update_password(self, user_id: int, password_hash: str) -> None:
        sql = f"""
            UPDATE {self.schema}.usertbl
            SET password_hash = %s, updated_at = NOW()
            WHERE user_id = %s
        """
        update_query(sql, [password_hash, user_id])

    def update_profile(
        self,
        user_id: int,
        *,
        full_name: str,
        phone: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> None:
        sql = f"""
            UPDATE {self.schema}.usertbl
            SET full_name = %s,
                phone = %s,
                avatar_url = %s,
                updated_at = NOW()
            WHERE user_id = %s
        """
        update_query(sql, [full_name, phone or "NA", avatar_url or "NA", user_id])

    def list_admin_users_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = """
            u.is_deleted = FALSE
            AND r.is_deleted = FALSE
            AND r.role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        if search:
            where += " AND (u.email ILIKE %s OR u.full_name ILIKE %s OR u.phone ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])

        allowed_sort = {
            "email": "u.email",
            "full_name": "u.full_name",
            "created_at": "u.created_at",
            "last_login_at": "u.last_login_at",
        }
        order_col = allowed_sort.get(sort_by, "u.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.usertbl u
            INNER JOIN {self.schema}.roletbl r ON r.role_id = u.role_id
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                u.user_id,
                u.email,
                u.full_name,
                u.phone,
                u.avatar_url,
                u.is_active,
                u.last_login_at,
                u.login_count,
                u.created_at,
                u.updated_at,
                r.role_id,
                r.role_code,
                r.role_name
            FROM {self.schema}.usertbl u
            INNER JOIN {self.schema}.roletbl r ON r.role_id = u.role_id
            WHERE {where}
            ORDER BY {order_col} {direction}, u.user_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_admin_user_for_management(self, user_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                u.user_id,
                u.email,
                u.full_name,
                u.phone,
                u.avatar_url,
                u.is_active,
                u.last_login_at,
                u.login_count,
                u.created_at,
                u.updated_at,
                r.role_id,
                r.role_code,
                r.role_name
            FROM {self.schema}.usertbl u
            INNER JOIN {self.schema}.roletbl r ON r.role_id = u.role_id
            WHERE u.user_id = %s
              AND u.is_deleted = FALSE
              AND r.is_deleted = FALSE
              AND r.role_code IN ('SUPER_ADMIN', 'ADMIN_MANAGER')
        """
        return select_one(sql, [user_id])

    def admin_email_exists(self, email: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT user_id
            FROM {self.schema}.usertbl
            WHERE LOWER(email) = LOWER(%s) AND is_deleted = FALSE
        """
        params: list[Any] = [email]
        if exclude_id:
            sql += " AND user_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create_admin_user(self, data: dict[str, Any]) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.usertbl
                (role_id, email, password_hash, full_name, phone, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING user_id
        """
        row = insert_query_returning(
            sql,
            [
                data["role_id"],
                data["email"],
                data["password_hash"],
                data["full_name"],
                data["phone"],
                data["is_active"],
            ],
        )
        if not row:
            return {}
        return self.fetch_admin_user_for_management(int(row["user_id"])) or {}

    def update_admin_user(self, user_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_admin_user_for_management(user_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.usertbl
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE user_id = %s AND is_deleted = FALSE
            RETURNING user_id
        """
        rows = execute(sql, [*data.values(), user_id], fetch=True)
        if not rows:
            return None
        return self.fetch_admin_user_for_management(user_id)

    def soft_delete_admin_user(self, user_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.usertbl
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE user_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [user_id]) > 0


user_repository = UserRepository()
