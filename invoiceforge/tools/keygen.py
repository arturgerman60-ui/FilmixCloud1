"""Генерация новой пары ключей Ed25519 для лицензий.

Запустите ОДИН РАЗ, когда хотите использовать собственные ключи:

    python tools/keygen.py

Скрипт напечатает:
- PUBLIC_KEY_HEX  → вставьте в app/licensing.py (константа PUBLIC_KEY_HEX)
- PRIVATE_KEY_HEX → сохраните в tools/seller_private_key.txt (держите В СЕКРЕТЕ!)

Публичный ключ можно отдавать/зашивать в приложение. Приватный ключ —
только у вас: им подписываются лицензии, и без него их невозможно подделать.
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_hex = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ).hex()
    public_hex = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    ).hex()

    print("=" * 60)
    print("СОХРАНИТЕ ЭТИ КЛЮЧИ")
    print("=" * 60)
    print(f"PUBLIC_KEY_HEX  = {public_hex}")
    print(f"PRIVATE_KEY_HEX = {private_hex}")
    print("=" * 60)
    print("1) Вставьте PUBLIC_KEY_HEX в app/licensing.py")
    print("2) Запишите PRIVATE_KEY_HEX в tools/seller_private_key.txt")
    print("   и НИКОГДА не отдавайте покупателям.")


if __name__ == "__main__":
    main()
