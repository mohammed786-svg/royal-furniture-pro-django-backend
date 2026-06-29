from __future__ import annotations

import secrets
from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest

from apps.customers.repositories.customer_repository import customer_repository
from apps.storefront.helpers.commerce_context import normalize_phone
from apps.storefront.repositories.otp_repository import otp_repository
from core.auth.firebase_verifier import verify_firebase_id_token
from core.auth.jwt_handler import jwt_handler
from core.database import select_one
from core.database.transaction import atomic
from core.database.raw_queries import execute
from core.exceptions.base import AuthenticationException, ValidationException
from core.helpers.ip import get_client_ip


DEMO_OTP = "123456"
PHONE_ALIASES = {"8296565587": "9876543210"}


class CustomerAuthService:
    schema = "royal"

    def _resolve_phone(self, phone: str) -> str:
        normalized = normalize_phone(phone)
        if not normalized or len(normalized) != 10:
            raise ValidationException(
                details=[{"field": "phone", "message": "Enter a valid 10-digit mobile number"}]
            )
        return PHONE_ALIASES.get(normalized, normalized)

    def _serialize_customer(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "customerId": str(row["customer_id"]),
            "userId": str(row["user_id"]) if row.get("user_id") else None,
            "name": row.get("full_name") or "Customer",
            "mobile": row.get("phone") or "",
            "email": row.get("email") if row.get("email") not in (None, "NA", "") else None,
        }

    def send_otp(self, phone: str, *, purpose: str = "login") -> dict[str, Any]:
        resolved = self._resolve_phone(phone)
        purpose = (purpose or "login").strip().lower()
        customer = customer_repository.fetch_by_phone(resolved)

        if purpose == "login" and not customer:
            raise ValidationException(
                details=[
                    {
                        "field": "phone",
                        "message": "No account found with this mobile. Please register.",
                    }
                ]
            )
        if purpose == "register" and customer:
            raise ValidationException(
                details=[
                    {
                        "field": "phone",
                        "message": "This mobile is already registered. Please login.",
                    }
                ]
            )

        otp_code = DEMO_OTP if settings.DEBUG else f"{secrets.randbelow(900000) + 100000:06d}"

        with atomic() as conn:
            otp_repository.invalidate_phone_otps(resolved, conn=conn)
            otp_repository.create_otp(
                phone=resolved,
                otp_code=otp_code,
                purpose=purpose.upper(),
                conn=conn,
            )

        payload: dict[str, Any] = {
            "phone": resolved,
            "purpose": purpose,
            "expiresInMinutes": 10,
        }
        if settings.DEBUG:
            payload["devOtp"] = DEMO_OTP
        return payload

    def verify_otp(self, request: HttpRequest, phone: str, otp: str) -> dict[str, Any]:
        resolved = self._resolve_phone(phone)
        code = (otp or "").strip()
        if len(code) != 6:
            raise ValidationException(
                details=[{"field": "otp", "message": "Enter the 6-digit OTP"}]
            )

        otp_row = otp_repository.fetch_valid_otp(resolved, code)
        if not otp_row and not (settings.DEBUG and code == DEMO_OTP):
            raise AuthenticationException("Invalid or expired OTP")

        customer = customer_repository.fetch_by_phone(resolved)
        if not customer:
            raise AuthenticationException(
                "No account found with this mobile. Please register first."
            )

        return self._issue_session(request, customer, otp_row)

    def verify_register_otp(
        self,
        request: HttpRequest,
        phone: str,
        otp: str,
        *,
        full_name: str,
        email: Optional[str] = None,
    ) -> dict[str, Any]:
        resolved = self._resolve_phone(phone)
        name = (full_name or "").strip()
        if not name:
            raise ValidationException(
                details=[{"field": "fullName", "message": "Full name is required"}]
            )

        email_value = (email or "").strip().lower()
        if email_value and customer_repository.email_exists(email_value):
            raise ValidationException(
                details=[{"field": "email", "message": "This email is already registered"}]
            )

        code = (otp or "").strip()
        if len(code) != 6:
            raise ValidationException(
                details=[{"field": "otp", "message": "Enter the 6-digit OTP"}]
            )

        otp_row = otp_repository.fetch_valid_otp(resolved, code)
        if not otp_row and not (settings.DEBUG and code == DEMO_OTP):
            raise AuthenticationException("Invalid or expired OTP")

        if customer_repository.fetch_by_phone(resolved):
            raise ValidationException(
                details=[
                    {
                        "field": "phone",
                        "message": "This mobile is already registered. Please login.",
                    }
                ]
            )

        customer = self._create_customer_for_phone(
            resolved,
            full_name=name,
            email=email_value or None,
        )
        return self._issue_session(request, customer, otp_row)

    def verify_google_sign_in(self, request: HttpRequest, id_token: str) -> dict[str, Any]:
        try:
            claims = verify_firebase_id_token(id_token)
        except ValueError as exc:
            raise AuthenticationException(str(exc)) from exc

        email = (claims.get("email") or "").strip().lower()
        if not email or not claims.get("email_verified"):
            raise AuthenticationException("Google account email is not verified")

        name = (claims.get("name") or "").strip() or email.split("@")[0]
        customer = customer_repository.fetch_by_email(email)
        if not customer:
            customer = self._create_customer_for_google(email=email, full_name=name)

        return self._issue_session(request, customer, None, login_type="customer_google")

    def _issue_session(
        self,
        request: HttpRequest,
        customer: dict[str, Any],
        otp_row: Optional[dict[str, Any]],
        *,
        login_type: str = "customer_otp",
    ) -> dict[str, Any]:
        user_id = customer.get("user_id")
        resolved = customer.get("phone") or ""
        payload = {
            "user_id": int(user_id) if user_id else None,
            "customer_id": int(customer["customer_id"]),
            "role": "CUSTOMER",
            "phone": resolved,
        }
        access_token = jwt_handler.create_access_token(payload, admin=False)
        refresh_token = jwt_handler.create_refresh_token(payload)

        if otp_row:
            with atomic() as conn:
                otp_repository.mark_verified(int(otp_row["otp_id"]), conn=conn)

        self._record_login(request, user_id, login_type=login_type)

        return {
            "user": self._serialize_customer(customer),
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresInMinutes": settings.JWT_ACCESS_TOKEN_MINUTES,
        }

    def get_me(self, customer_id: int) -> dict[str, Any]:
        customer = customer_repository.fetch_by_id(customer_id)
        if not customer:
            raise AuthenticationException("Customer session expired")
        return self._serialize_customer(customer)

    def _get_customer_role_id(self, conn) -> int:
        row = select_one(
            f"""
            SELECT role_id FROM {self.schema}.roletbl
            WHERE role_code = 'CUSTOMER' AND is_deleted = FALSE
            LIMIT 1
            """,
            [],
            conn=conn,
        )
        if not row:
            raise ValidationException(message="Customer role is not configured")
        return int(row["role_id"])

    def _create_customer_for_phone(
        self,
        phone: str,
        *,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> dict[str, Any]:
        display_name = (full_name or "").strip() or f"Customer {phone[-4:]}"
        customer_email = (email or "").strip().lower() or f"{phone}@guest.royalfurniture.local"
        with atomic() as conn:
            role_id = self._get_customer_role_id(conn)
            user_rows = execute(
                f"""
                INSERT INTO {self.schema}.usertbl
                    (role_id, email, phone, password_hash, full_name, email_verified, is_active)
                VALUES (%s, %s, %s, %s, %s, FALSE, TRUE)
                RETURNING user_id
                """,
                [role_id, customer_email, phone, "!", display_name],
                conn=conn,
                fetch=True,
            )
            user_id = int(user_rows[0]["user_id"])
            cust_rows = execute(
                f"""
                INSERT INTO {self.schema}.customertbl
                    (user_id, email, phone, full_name, is_guest, is_active)
                VALUES (%s, %s, %s, %s, FALSE, TRUE)
                RETURNING customer_id
                """,
                [user_id, customer_email, phone, display_name],
                conn=conn,
                fetch=True,
            )
            customer_id = int(cust_rows[0]["customer_id"])
        customer = customer_repository.fetch_by_id(customer_id)
        return customer or {
            "customer_id": customer_id,
            "user_id": user_id,
            "phone": phone,
            "full_name": display_name,
            "email": customer_email,
        }

    def _create_customer_for_google(
        self,
        *,
        email: str,
        full_name: str,
    ) -> dict[str, Any]:
        display_name = full_name.strip() or email.split("@")[0]
        with atomic() as conn:
            role_id = self._get_customer_role_id(conn)
            user_rows = execute(
                f"""
                INSERT INTO {self.schema}.usertbl
                    (role_id, email, phone, password_hash, full_name, email_verified, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)
                RETURNING user_id
                """,
                [role_id, email, "NA", "!", display_name],
                conn=conn,
                fetch=True,
            )
            user_id = int(user_rows[0]["user_id"])
            cust_rows = execute(
                f"""
                INSERT INTO {self.schema}.customertbl
                    (user_id, email, phone, full_name, is_guest, is_active)
                VALUES (%s, %s, %s, %s, FALSE, TRUE)
                RETURNING customer_id
                """,
                [user_id, email, "NA", display_name],
                conn=conn,
                fetch=True,
            )
            customer_id = int(cust_rows[0]["customer_id"])
        customer = customer_repository.fetch_by_id(customer_id)
        return customer or {
            "customer_id": customer_id,
            "user_id": user_id,
            "phone": "NA",
            "full_name": display_name,
            "email": email,
        }

    def _record_login(
        self,
        request: HttpRequest,
        user_id: Optional[int],
        *,
        login_type: str = "customer_otp",
    ) -> None:
        if not user_id:
            return
        try:
            from apps.authentication.repositories.login_history_repository import login_history_repository

            login_history_repository.record(
                user_id=user_id,
                login_type=login_type,
                status="success",
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "unknown")[:500],
            )
        except Exception:
            pass


customer_auth_service = CustomerAuthService()
