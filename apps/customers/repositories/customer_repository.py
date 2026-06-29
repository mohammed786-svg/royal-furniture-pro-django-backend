from __future__ import annotations

import json
from typing import Any, Optional

from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json

from core.database import insert_query_returning, select_one, select_query, update_query
from core.database.raw_queries import execute


class CustomerRepository:
    schema = "royal"
    table = "customertbl"

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        search: str = "",
        is_guest: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        offset = (page - 1) * page_size
        params: list[Any] = []
        where = "c.is_deleted = FALSE"
        if search:
            where += " AND (c.full_name ILIKE %s OR c.email ILIKE %s OR c.phone ILIKE %s)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if is_guest is not None:
            where += " AND c.is_guest = %s"
            params.append(is_guest)

        allowed_sort = {
            "full_name": "c.full_name",
            "email": "c.email",
            "phone": "c.phone",
            "created_at": "c.created_at",
        }
        order_col = allowed_sort.get(sort_by, "c.created_at")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {self.schema}.{self.table} c
            WHERE {where}
        """
        count_row = select_one(count_sql, params)
        total = int(count_row["total"]) if count_row else 0

        sql = f"""
            SELECT
                c.*,
                cp.customer_profile_id,
                cp.date_of_birth,
                cp.gender,
                cp.profile_image,
                cp.preferences,
                cp.newsletter_subscribed
            FROM {self.schema}.{self.table} c
            LEFT JOIN {self.schema}.customer_profiletbl cp
                ON cp.customer_id = c.customer_id AND cp.is_deleted = FALSE
            WHERE {where}
            ORDER BY {order_col} {direction}, c.customer_id DESC
            LIMIT %s OFFSET %s
        """
        rows = select_query(sql, [*params, page_size, offset])
        return rows, total

    def fetch_by_phone(self, phone: str) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                c.*,
                cp.customer_profile_id,
                cp.date_of_birth,
                cp.gender,
                cp.profile_image,
                cp.preferences,
                cp.newsletter_subscribed
            FROM {self.schema}.{self.table} c
            LEFT JOIN {self.schema}.customer_profiletbl cp
                ON cp.customer_id = c.customer_id AND cp.is_deleted = FALSE
            WHERE c.phone = %s AND c.is_deleted = FALSE AND c.is_active = TRUE
            ORDER BY c.customer_id ASC
            LIMIT 1
        """
        return select_one(sql, [phone])

    def fetch_by_email(self, email: str) -> Optional[dict[str, Any]]:
        normalized = (email or "").strip().lower()
        if not normalized or normalized == "na":
            return None
        sql = f"""
            SELECT
                c.*,
                cp.customer_profile_id,
                cp.date_of_birth,
                cp.gender,
                cp.profile_image,
                cp.preferences,
                cp.newsletter_subscribed
            FROM {self.schema}.{self.table} c
            LEFT JOIN {self.schema}.customer_profiletbl cp
                ON cp.customer_id = c.customer_id AND cp.is_deleted = FALSE
            WHERE LOWER(c.email) = %s AND c.is_deleted = FALSE AND c.is_active = TRUE
            ORDER BY c.customer_id ASC
            LIMIT 1
        """
        return select_one(sql, [normalized])

    def phone_exists(self, phone: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT customer_id
            FROM {self.schema}.{self.table}
            WHERE phone = %s AND is_deleted = FALSE
        """
        params: list[Any] = [phone]
        if exclude_id:
            sql += " AND customer_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def fetch_by_id(self, customer_id: int) -> Optional[dict[str, Any]]:
        sql = f"""
            SELECT
                c.*,
                cp.customer_profile_id,
                cp.date_of_birth,
                cp.gender,
                cp.profile_image,
                cp.preferences,
                cp.newsletter_subscribed
            FROM {self.schema}.{self.table} c
            LEFT JOIN {self.schema}.customer_profiletbl cp
                ON cp.customer_id = c.customer_id AND cp.is_deleted = FALSE
            WHERE c.customer_id = %s AND c.is_deleted = FALSE
        """
        return select_one(sql, [customer_id])

    def email_exists(self, email: str, *, exclude_id: Optional[int] = None) -> bool:
        sql = f"""
            SELECT customer_id
            FROM {self.schema}.{self.table}
            WHERE email = %s AND is_deleted = FALSE
        """
        params: list[Any] = [email]
        if exclude_id:
            sql += " AND customer_id <> %s"
            params.append(exclude_id)
        return select_one(sql, params) is not None

    def create(self, data: dict[str, Any], *, conn: Optional[PgConnection] = None) -> dict[str, Any]:
        sql = f"""
            INSERT INTO {self.schema}.{self.table}
                (user_id, guest_token, email, phone, full_name, is_guest, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING customer_id
        """
        values = list(data.values())
        if conn is not None:
            rows = execute(sql, values, conn=conn, fetch=True)
            customer_id = int(rows[0]["customer_id"])
            return self.fetch_by_id(customer_id) or rows[0]
        row = insert_query_returning(sql, values)
        if row:
            return self.fetch_by_id(int(row["customer_id"])) or row
        return {}

    def update(
        self,
        customer_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> Optional[dict[str, Any]]:
        if not data:
            return self.fetch_by_id(customer_id)
        sets = ", ".join(f"{key} = %s" for key in data)
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
            WHERE customer_id = %s AND is_deleted = FALSE
            RETURNING customer_id
        """
        params = [*data.values(), customer_id]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return self.fetch_by_id(customer_id) if rows else None
        rows = execute(sql, params, fetch=True)
        return self.fetch_by_id(customer_id) if rows else None

    def soft_delete(self, customer_id: int) -> bool:
        sql = f"""
            UPDATE {self.schema}.{self.table}
            SET is_deleted = TRUE, is_active = FALSE, updated_at = NOW()
            WHERE customer_id = %s AND is_deleted = FALSE
        """
        return update_query(sql, [customer_id]) > 0

    def _normalize_profile_data(self, data: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(data)
        if "date_of_birth" in normalized and normalized["date_of_birth"] in ("", "NA", None):
            normalized["date_of_birth"] = None
        if "preferences" in normalized:
            prefs = normalized["preferences"]
            if isinstance(prefs, str):
                try:
                    prefs = json.loads(prefs) if prefs else {}
                except json.JSONDecodeError:
                    prefs = {}
            normalized["preferences"] = Json(prefs or {})
        return normalized

    def upsert_profile(
        self,
        customer_id: int,
        data: dict[str, Any],
        *,
        conn: Optional[PgConnection] = None,
    ) -> dict[str, Any]:
        existing_sql = f"""
            SELECT customer_profile_id
            FROM {self.schema}.customer_profiletbl
            WHERE customer_id = %s AND is_deleted = FALSE
        """
        existing = select_one(existing_sql, [customer_id], conn=conn)
        data = self._normalize_profile_data(data)
        if existing:
            sets = ", ".join(f"{key} = %s" for key in data)
            sql = f"""
                UPDATE {self.schema}.customer_profiletbl
                SET {sets}, updated_at = NOW(), epoch = EXTRACT(EPOCH FROM NOW())
                WHERE customer_profile_id = %s AND is_deleted = FALSE
                RETURNING *
            """
            params = [*data.values(), existing["customer_profile_id"]]
            if conn is not None:
                rows = execute(sql, params, conn=conn, fetch=True)
                return rows[0] if rows else {}
            rows = execute(sql, params, fetch=True)
            return rows[0] if rows else {}

        dob = data.get("date_of_birth")
        prefs = data.get("preferences", Json({}))
        if not isinstance(prefs, Json):
            prefs = Json(prefs or {})

        sql = f"""
            INSERT INTO {self.schema}.customer_profiletbl
                (customer_id, date_of_birth, gender, profile_image, preferences, newsletter_subscribed)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        params = [
            customer_id,
            dob,
            data.get("gender", "NA"),
            data.get("profile_image", "NA"),
            prefs,
            bool(data.get("newsletter_subscribed", False)),
        ]
        if conn is not None:
            rows = execute(sql, params, conn=conn, fetch=True)
            return rows[0] if rows else {}
        row = insert_query_returning(sql, params)
        return row or {}

    def list_options(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT customer_id, full_name, email, phone
            FROM {self.schema}.{self.table}
            WHERE is_deleted = FALSE AND is_active = TRUE
            ORDER BY full_name
        """
        return select_query(sql)


customer_repository = CustomerRepository()
