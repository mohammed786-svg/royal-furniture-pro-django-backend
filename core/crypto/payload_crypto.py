"""AES-256-GCM payload encryption for API transport."""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

logger = logging.getLogger(__name__)


def get_crypto_key() -> bytes | None:
    raw = getattr(settings, "API_CRYPTO_KEY", "") or ""
    raw = raw.strip()
    if not raw:
        return None
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        logger.warning(
            "API_CRYPTO_KEY is not valid hex; encryption disabled. "
            "Use 64 hex characters (openssl rand -hex 32)."
        )
        return None
    if len(key) != 32:
        logger.warning(
            "API_CRYPTO_KEY must be 32 bytes (64 hex characters); encryption disabled."
        )
        return None
    return key


def encrypt_payload(data: dict[str, Any]) -> str:
    key = get_crypto_key()
    if key is None:
        raise RuntimeError("API_CRYPTO_KEY is not configured")
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    plaintext = json.dumps(data, separators=(",", ":"), default=str).encode("utf-8")
    ciphertext = aesgcm.encrypt(iv, plaintext, None)
    return base64.b64encode(iv + ciphertext).decode("ascii")


def decrypt_payload(payload_b64: str) -> dict[str, Any]:
    key = get_crypto_key()
    if key is None:
        raise RuntimeError("API_CRYPTO_KEY is not configured")
    raw = base64.b64decode(payload_b64)
    if len(raw) < 13:
        raise ValueError("Invalid encrypted payload")
    iv, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    parsed = json.loads(plaintext.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Decrypted payload must be a JSON object")
    return parsed
