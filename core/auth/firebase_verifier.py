"""Verify Firebase Google ID tokens for storefront login."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger("api")

_firebase_app = None


def _init_firebase() -> None:
    global _firebase_app
    if _firebase_app is not None:
        return
    import firebase_admin
    from firebase_admin import credentials

    cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or ""
    if cred_path:
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        return

    project_id = getattr(settings, "FIREBASE_PROJECT_ID", "") or ""
    if project_id:
        _firebase_app = firebase_admin.initialize_app(options={"projectId": project_id})
        return

    raise RuntimeError("Firebase is not configured")


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    if not id_token or not id_token.strip():
        raise ValueError("Missing ID token")

    try:
        _init_firebase()
        from firebase_admin import auth

        return auth.verify_id_token(id_token.strip(), check_revoked=True)
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise ValueError("Invalid or expired Google sign-in token") from exc
