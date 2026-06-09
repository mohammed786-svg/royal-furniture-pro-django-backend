#!/usr/bin/env python
"""Seed super admin and admin manager users with menu permissions."""
from __future__ import annotations

import os
import sys

import django
from django.contrib.auth.hashers import make_password

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.database import execute, select_one  # noqa: E402

SCHEMA = "royal"
PASSWORD = "royal@2026"

ADMIN_MENU_KEYS = [
    "dashboard",
    "products",
    "categories",
    "brands",
    "reviews",
    "tags",
    "warehouses",
    "stock",
    "adjustments",
    "transfers",
    "alerts",
    "orders",
    "order-status",
    "returns",
    "tracking",
    "customers",
    "addresses",
    "wishlists",
    "wallet",
    "coupons",
    "banners",
    "cms",
    "testimonials",
    "faqs",
    "payments",
    "payment-verification",
    "shipments",
    "shipment-tracking",
    "sales-analytics",
    "page-views",
    "search-reports",
    "notifications",
    "settings",
    "audit-logs",
]

ADMIN_MANAGER_KEYS = [
    "dashboard",
    "products",
    "categories",
    "orders",
    "customers",
    "stock",
    "payments",
    "notifications",
]


def get_role_id(role_code: str) -> int:
    row = select_one(
        f"SELECT role_id FROM {SCHEMA}.roletbl WHERE role_code = %s AND is_deleted = FALSE",
        [role_code],
    )
    if not row:
        raise RuntimeError(f"Role {role_code} not found. Apply royal_furniture.sql first.")
    return row["role_id"]


def seed_permissions() -> dict[str, int]:
    permission_ids: dict[str, int] = {}
    for key in ADMIN_MENU_KEYS:
        existing = select_one(
            f"""
            SELECT permission_id FROM {SCHEMA}.permissiontbl
            WHERE permission_code = %s AND module_name = 'admin_menu'
            """,
            [key],
        )
        if existing:
            permission_ids[key] = existing["permission_id"]
            continue

        row = execute(
            f"""
            INSERT INTO {SCHEMA}.permissiontbl
                (permission_code, permission_name, module_name, description)
            VALUES (%s, %s, 'admin_menu', %s)
            ON CONFLICT (permission_code) DO UPDATE
                SET permission_name = EXCLUDED.permission_name
            RETURNING permission_id
            """,
            [key, key.replace("-", " ").title(), f"Admin menu: {key}"],
            fetch=True,
        )
        permission_ids[key] = row[0]["permission_id"]
    return permission_ids


def seed_role_permissions(role_code: str, menu_keys: list[str], permission_ids: dict[str, int]) -> None:
    role_id = get_role_id(role_code)
    for key in menu_keys:
        permission_id = permission_ids[key]
        exists = select_one(
            f"""
            SELECT role_permission_id FROM {SCHEMA}.role_permissiontbl
            WHERE role_id = %s AND permission_id = %s
            """,
            [role_id, permission_id],
        )
        if exists:
            continue
        execute(
            f"""
            INSERT INTO {SCHEMA}.role_permissiontbl (role_id, permission_id)
            VALUES (%s, %s)
            """,
            [role_id, permission_id],
        )


def upsert_user(email: str, full_name: str, role_code: str) -> None:
    role_id = get_role_id(role_code)
    password_hash = make_password(PASSWORD)
    existing = select_one(
        f"SELECT user_id FROM {SCHEMA}.usertbl WHERE LOWER(email) = LOWER(%s)",
        [email],
    )
    if existing:
        execute(
            f"""
            UPDATE {SCHEMA}.usertbl
            SET role_id = %s,
                password_hash = %s,
                full_name = %s,
                is_active = TRUE,
                is_deleted = FALSE,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            [role_id, password_hash, full_name, existing["user_id"]],
        )
        print(f"Updated user: {email}")
        return

    execute(
        f"""
        INSERT INTO {SCHEMA}.usertbl
            (role_id, email, password_hash, full_name, phone, email_verified, is_active)
        VALUES (%s, %s, %s, %s, 'NA', TRUE, TRUE)
        """,
        [role_id, email, password_hash, full_name],
    )
    print(f"Created user: {email}")


def main() -> None:
    print("Seeding admin menu permissions...")
    permission_ids = seed_permissions()

    print("Seeding role permissions...")
    seed_role_permissions("SUPER_ADMIN", ADMIN_MENU_KEYS, permission_ids)
    seed_role_permissions("ADMIN_MANAGER", ADMIN_MANAGER_KEYS, permission_ids)

    print("Seeding admin users...")
    upsert_user("super@royal.com", "Mr. Herald", "SUPER_ADMIN")
    upsert_user("admin@royal.com", "Sarah Mitchell", "ADMIN_MANAGER")

    print("Done.")
    print("Super Admin: super@royal.com / royal@2026")
    print("Admin Manager: admin@royal.com / royal@2026")


if __name__ == "__main__":
    main()
