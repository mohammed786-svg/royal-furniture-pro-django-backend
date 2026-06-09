from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from django.conf import settings

from core.database import insert_query_returning, select_one, update_query


class AdminSessionRepository:
    schema = "royal"

    def create_session(
        self,
        *,
        user_id: int,
        access_token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
    ) -> dict[str, Any]:
        expiry = datetime.now(timezone.utc) + timedelta(hours=settings.ADMIN_SESSION_HOURS)
        sql = f"""
            INSERT INTO {self.schema}.admin_sessiontbl
                (user_id, jwt_token, refresh_token, expiry_time, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING admin_session_id, user_id, login_time, expiry_time
        """
        row = insert_query_returning(
            sql,
            [user_id, access_token, refresh_token, expiry, ip_address, user_agent],
        )
        return row or {}

    def fetch_active_by_refresh_token(self, refresh_token: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                s.admin_session_id,
                s.user_id,
                s.jwt_token,
                s.refresh_token,
                s.expiry_time,
                s.is_revoked
            FROM {self.schema}.admin_sessiontbl s
            WHERE s.refresh_token = %s
              AND s.is_deleted = FALSE
              AND s.is_active = TRUE
              AND s.is_revoked = FALSE
              AND s.expiry_time > NOW()
        """
        return select_one(sql, [refresh_token])

    def fetch_active_by_access_token(self, access_token: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                s.admin_session_id,
                s.user_id,
                s.jwt_token,
                s.refresh_token,
                s.expiry_time,
                s.is_revoked
            FROM {self.schema}.admin_sessiontbl s
            WHERE s.jwt_token = %s
              AND s.is_deleted = FALSE
              AND s.is_active = TRUE
              AND s.is_revoked = FALSE
              AND s.expiry_time > NOW()
        """
        return select_one(sql, [access_token])

    def revoke_session(self, session_id: int) -> None:
        sql = f"""
            UPDATE {self.schema}.admin_sessiontbl
            SET is_revoked = TRUE,
                revoked_at = NOW(),
                is_active = FALSE,
                updated_at = NOW()
            WHERE admin_session_id = %s
        """
        update_query(sql, [session_id])

    def revoke_all_for_user(self, user_id: int) -> None:
        sql = f"""
            UPDATE {self.schema}.admin_sessiontbl
            SET is_revoked = TRUE,
                revoked_at = NOW(),
                is_active = FALSE,
                updated_at = NOW()
            WHERE user_id = %s
              AND is_revoked = FALSE
              AND is_active = TRUE
        """
        update_query(sql, [user_id])

    def rotate_tokens(
        self,
        session_id: int,
        *,
        access_token: str,
        refresh_token: str,
    ) -> None:
        expiry = datetime.now(timezone.utc) + timedelta(hours=settings.ADMIN_SESSION_HOURS)
        sql = f"""
            UPDATE {self.schema}.admin_sessiontbl
            SET jwt_token = %s,
                refresh_token = %s,
                expiry_time = %s,
                updated_at = NOW()
            WHERE admin_session_id = %s
        """
        update_query(sql, [access_token, refresh_token, expiry, session_id])


admin_session_repository = AdminSessionRepository()
