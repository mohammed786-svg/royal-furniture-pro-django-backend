from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection

from core.database import select_one
from core.database.raw_queries import execute


class OtpRepository:
    schema = "royal"
    table = "otptbl"

    def invalidate_phone_otps(self, phone: str, *, conn: Optional[PgConnection] = None) -> None:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_active = FALSE, updated_at = NOW()
            WHERE phone = %s AND is_verified = FALSE AND is_deleted = FALSE
        """
        if conn is not None:
            execute(sql, [phone], conn=conn, fetch=False)
        else:
            execute(sql, [phone], fetch=False)

    def create_otp(
        self,
        *,
        phone: str,
        otp_code: str,
        purpose: str = "LOGIN",
        expires_minutes: int = 10,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (phone, otp_code, otp_type, purpose, expires_at, is_active)
            VALUES (%s, %s, 'SMS', %s, %s, TRUE)
            RETURNING otp_id, phone, expires_at
        """
        params = [phone, otp_code, purpose, expires_at]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return rows[0] if rows else {}
        rows = execute(sql, params, fetch=True)
        return rows[0] if rows else {}

    def fetch_valid_otp(self, phone: str, otp_code: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT *
            FROM {self.schema}.{self.table}
            WHERE phone = %s
              AND otp_code = %s
              AND is_verified = FALSE
              AND is_active = TRUE
              AND is_deleted = FALSE
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
        """
        return select_one(sql, [phone, otp_code])

    def mark_verified(self, otp_id: int, *, conn: Optional[PgConnection] = None) -> None:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_verified = TRUE, verified_at = NOW(), updated_at = NOW()
            WHERE otp_id = %s
        """
        if conn is not None:
            execute(sql, [otp_id], conn=conn, fetch=False)
        else:
            execute(sql, [otp_id], fetch=False)


otp_repository = OtpRepository()
