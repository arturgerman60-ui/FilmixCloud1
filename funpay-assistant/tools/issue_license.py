"""Выпуск лицензии покупателю (инструмент продавца).

    python tools/issue_license.py --name "Иван"                 # бессрочно
    python tools/issue_license.py --name "Иван" --expires 2027-01-01   # подписка
    python tools/issue_license.py --name "Иван" --machine <ID_ПК>      # привязка

Строку FPA1.xxx.yyy отправляете покупателю → он вставляет во вкладке «Лицензия».
Приватный ключ (seller_private_key.txt) НИКОГДА не отдаём покупателю.
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
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex))
    payload = {"name": name, "plan": plan, "issued": date.today().isoformat(),
               "expires": expires, "machine": machine}
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f"FPA1.{_b64url(payload_bytes)}.{_b64url(key.sign(payload_bytes))}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Выпуск лицензии FunPay Assistant")
    parser.add_argument("--name", required=True)
    parser.add_argument("--plan", default="pro")
    parser.add_argument("--expires", default=None)
    parser.add_argument("--machine", default=None)
    args = parser.parse_args()
    print("\nКлюч для покупателя:\n")
    print(issue(args.name, args.plan, args.expires, args.machine))
    print()


if __name__ == "__main__":
    main()
