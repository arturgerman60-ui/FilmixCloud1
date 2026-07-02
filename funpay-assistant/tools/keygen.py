"""Генерация пары ключей Ed25519 для лицензий (запустить один раз).

    python tools/keygen.py

- PUBLIC_KEY_HEX  → вставьте в src/funpay_assistant/licensing.py
- PRIVATE_KEY_HEX → сохраните в tools/seller_private_key.txt (СЕКРЕТ!)
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_hex = priv.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    ).hex()
    pub_hex = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    print("PUBLIC_KEY_HEX  =", pub_hex)
    print("PRIVATE_KEY_HEX =", priv_hex)


if __name__ == "__main__":
    main()
