"""Лицензирование Ed25519 (защита от бесплатного копирования).

Приватный ключ — только у продавца (tools/). Публичный зашит здесь.
Подделать лицензию без приватного ключа невозможно.
Подробности — в SELLING.md.
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import uuid
from datetime import date

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Замените на свой публичный ключ (tools/keygen.py) перед реальными продажами.
PUBLIC_KEY_HEX = "3eb38e8dd6037bd00d193e087c9a848b224145bc8d1253aa7a603ec7ee544f91"
LICENSE_PREFIX = "FPA1"


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def machine_id() -> str:
    raw = f"{platform.node()}|{platform.machine()}|{uuid.getnode()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class LicenseInfo:
    def __init__(self, valid: bool, plan: str = "demo", data: dict | None = None,
                 error: str | None = None) -> None:
        self.valid = valid
        self.plan = plan
        self.data = data or {}
        self.error = error

    @property
    def is_pro(self) -> bool:
        return self.valid and self.plan == "pro"


def verify_license(license_key: str | None) -> LicenseInfo:
    if not license_key:
        return LicenseInfo(False, "demo", error="Лицензия не активирована")
    try:
        parts = license_key.strip().split(".")
        if len(parts) != 3 or parts[0] != LICENSE_PREFIX:
            return LicenseInfo(False, "demo", error="Неверный формат ключа")
        payload_bytes = _b64url_decode(parts[1])
        signature = _b64url_decode(parts[2])
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX)).verify(
            signature, payload_bytes
        )
        payload = json.loads(payload_bytes.decode("utf-8"))
    except InvalidSignature:
        return LicenseInfo(False, "demo", error="Подпись лицензии недействительна")
    except Exception:  # noqa: BLE001
        return LicenseInfo(False, "demo", error="Не удалось прочитать лицензию")

    expires = payload.get("expires")
    if expires:
        try:
            if date.fromisoformat(expires) < date.today():
                return LicenseInfo(False, "demo", data=payload, error="Срок лицензии истёк")
        except ValueError:
            return LicenseInfo(False, "demo", error="Неверная дата в лицензии")

    machine = payload.get("machine")
    if machine and machine != machine_id():
        return LicenseInfo(False, "demo", data=payload, error="Лицензия для другого ПК")

    return LicenseInfo(True, payload.get("plan", "pro"), data=payload)
