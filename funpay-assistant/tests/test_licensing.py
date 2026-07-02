import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from funpay_assistant import licensing  # noqa: E402

# Приватный ключ, парный к PUBLIC_KEY_HEX в licensing.py (тестовая пара).
PRIVATE_HEX = "ca49b6e060014da953fdb0dd244136b7b65c3ded1fca89daf72e8c095ccc807f"


def _issue(payload: dict) -> str:
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(PRIVATE_HEX))
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    sig = key.sign(payload_bytes)
    b = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=").decode()  # noqa: E731
    return f"FPA1.{b(payload_bytes)}.{b(sig)}"


def test_valid_license():
    key = _issue({"name": "Buyer", "plan": "pro", "expires": None, "machine": None})
    info = licensing.verify_license(key)
    assert info.valid and info.is_pro


def test_expired_license():
    key = _issue({"name": "Buyer", "plan": "pro", "expires": "2000-01-01", "machine": None})
    info = licensing.verify_license(key)
    assert not info.valid


def test_tampered_license():
    key = _issue({"name": "Buyer", "plan": "pro", "expires": None, "machine": None})
    tampered = key[:-4] + ("AAAA" if not key.endswith("AAAA") else "BBBB")
    assert not licensing.verify_license(tampered).valid


def test_empty_license_is_demo():
    info = licensing.verify_license("")
    assert not info.valid and info.plan == "demo"
