"""Система лицензирования на базе Ed25519 (защита от бесплатного копирования).

Как это работает:
- Продавец один раз генерирует пару ключей (см. tools/keygen.py).
- ПУБЛИЧНЫЙ ключ зашит в приложение (константа PUBLIC_KEY_HEX ниже).
- ПРИВАТНЫЙ ключ остаётся только у продавца и НИКОГДА не отдаётся покупателю.
- Продавец выпускает лицензию каждому клиенту (см. tools/issue_license.py):
  подписывает JSON-данные приватным ключом.
- Приложение проверяет подпись публичным ключом. Подделать лицензию без
  приватного ключа невозможно, поэтому «крякнуть» ключ нельзя.

Формат лицензионного ключа (одна строка):
    IFG1.<base64url(payload_json)>.<base64url(signature)>

payload_json содержит:
    {
      "name":    "Имя клиента",
      "plan":    "pro",
      "issued":  "2026-01-01",
      "expires": "2027-01-01" | null,     # null = бессрочно
      "machine": "abc123" | null          # null = без привязки к ПК
    }
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import uuid
from datetime import date
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# =========================================================================
#  ПУБЛИЧНЫЙ КЛЮЧ ПРОДАВЦА.
#  Замените на свой (tools/keygen.py напечатает новый), чтобы никто другой
#  не мог выпускать лицензии к вашей копии продукта.
# =========================================================================
PUBLIC_KEY_HEX = "3eb38e8dd6037bd00d193e087c9a848b224145bc8d1253aa7a603ec7ee544f91"

LICENSE_PREFIX = "IFG1"


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def machine_id() -> str:
    """Стабильный идентификатор машины (для необязательной привязки лицензии)."""
    raw = f"{platform.node()}|{platform.machine()}|{uuid.getnode()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class LicenseInfo:
    """Результат проверки лицензии."""

    def __init__(self, valid: bool, plan: str = "demo", data: dict[str, Any] | None = None,
                 error: str | None = None) -> None:
        self.valid = valid
        self.plan = plan
        self.data = data or {}
        self.error = error

    @property
    def is_pro(self) -> bool:
        return self.valid and self.plan == "pro"


def verify_license(license_key: str | None) -> LicenseInfo:
    """Проверяет подпись и срок действия лицензии.

    Возвращает LicenseInfo. Если ключа нет или он неверный — plan="demo".
    """
    if not license_key:
        return LicenseInfo(False, "demo", error="Лицензия не активирована")

    try:
        parts = license_key.strip().split(".")
        if len(parts) != 3 or parts[0] != LICENSE_PREFIX:
            return LicenseInfo(False, "demo", error="Неверный формат ключа")

        payload_bytes = _b64url_decode(parts[1])
        signature = _b64url_decode(parts[2])

        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX))
        public_key.verify(signature, payload_bytes)  # бросит исключение, если подпись неверна

        payload = json.loads(payload_bytes.decode("utf-8"))
    except InvalidSignature:
        return LicenseInfo(False, "demo", error="Подпись лицензии недействительна")
    except Exception:  # noqa: BLE001 — любой сбой разбора = невалидная лицензия
        return LicenseInfo(False, "demo", error="Не удалось прочитать лицензию")

    # Проверка срока действия.
    expires = payload.get("expires")
    if expires:
        try:
            if date.fromisoformat(expires) < date.today():
                return LicenseInfo(False, "demo", data=payload, error="Срок лицензии истёк")
        except ValueError:
            return LicenseInfo(False, "demo", error="Неверная дата в лицензии")

    # Необязательная привязка к машине.
    machine = payload.get("machine")
    if machine and machine != machine_id():
        return LicenseInfo(False, "demo", data=payload,
                           error="Лицензия выдана для другого компьютера")

    return LicenseInfo(True, payload.get("plan", "pro"), data=payload)
