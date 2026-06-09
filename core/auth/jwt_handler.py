"""JWT access + refresh token architecture (no auth APIs yet)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from django.conf import settings


class JWTHandler:
    def __init__(self) -> None:
        self.secret = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_minutes = settings.JWT_ACCESS_TOKEN_MINUTES
        self.refresh_days = settings.JWT_REFRESH_TOKEN_DAYS
        self.admin_hours = settings.ADMIN_SESSION_HOURS

    def create_access_token(self, payload: dict[str, Any], *, admin: bool = False) -> str:
        exp_delta = (
            timedelta(hours=self.admin_hours)
            if admin
            else timedelta(minutes=self.access_minutes)
        )
        data = {
            **payload,
            "type": "access",
            "exp": datetime.now(timezone.utc) + exp_delta,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(data, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, payload: dict[str, Any]) -> str:
        data = {
            **payload,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=self.refresh_days),
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(data, self.secret, algorithm=self.algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self.secret, algorithms=[self.algorithm])

    def verify(self, token: str, token_type: str = "access") -> Optional[dict[str, Any]]:
        try:
            payload = self.decode(token)
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.PyJWTError:
            return None


jwt_handler = JWTHandler()
