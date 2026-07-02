"""Выпуск лицензионного ключа для покупателя (инструмент продавца).

Пример:
    # бессрочная PRO-лицензия
    python tools/issue_license.py --name "Иван Петров"

    # лицензия с окончанием срока (для подписки)
    python tools/issue_license.py --name "ООО Ромашка" --expires 2027-01-01

    # лицензия с привязкой к конкретному ПК (ID берётся на странице /activate)
    python tools/issue_license.py --name "Клиент" --machine 3f9a1b2c4d5e6f70

Полученный ключ (строка вида IFG1.xxx.yyy) отправляете покупателю. Он вставляет
его на странице «Активировать лицензию».

ВНИМАНИЕ: приватный ключ (tools/seller_private_key.txt) — ваша тайна.
Никогда не кладите его в сборку, которую отдаёте покупателю.
"""

from __future__ import annotations

import argparse
import base64
import json
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PRIVATE_KEY_FILE = Path(__file__).resolve().parent / "seller_private_key.txt"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def issue(name: str, plan: str, expires: str | None, machine: str | None) -> str:
    private_hex = PRIVATE_KEY_FILE.read_text(encoding="utf-8").strip()
    private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex))

    payload = {
        "name": name,
        "plan": plan,
        "issued": date.today().isoformat(),
        "expires": expires,
        "machine": machine,
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(payload_bytes)
    return f"IFG1.{_b64url(payload_bytes)}.{_b64url(signature)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Выпуск лицензии InvoiceForge")
    parser.add_argument("--name", required=True, help="Имя покупателя / название компании")
    parser.add_argument("--plan", default="pro", help="План (по умолчанию pro)")
    parser.add_argument("--expires", default=None, help="Дата окончания YYYY-MM-DD (для подписки)")
    parser.add_argument("--machine", default=None, help="Привязка к ID компьютера (необязательно)")
    args = parser.parse_args()

    key = issue(args.name, args.plan, args.expires, args.machine)
    print("\nЛицензионный ключ (отправьте покупателю):\n")
    print(key)
    print()


if __name__ == "__main__":
    main()
