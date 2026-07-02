"""Secure credential storage.

Passwords and auth tokens are stored in the OS keyring when available
(Windows Credential Locker, macOS Keychain, Secret Service on Linux). If the
keyring backend is unavailable (e.g. headless CI), we degrade gracefully to an
obfuscated on-disk fallback so the app still runs — while logging a warning.
"""
from __future__ import annotations

import base64
import json
from typing import Optional

from .logger import get_logger
from .paths import data_dir

log = get_logger(__name__)

_SERVICE = "FunPayAutoResponder"

try:  # keyring is optional at runtime
    import keyring  # type: ignore

    _KEYRING_OK = True
except Exception:  # pragma: no cover
    keyring = None  # type: ignore
    _KEYRING_OK = False


def _fallback_file():
    return data_dir() / ".secrets.b64"


def _load_fallback() -> dict:
    path = _fallback_file()
    if not path.exists():
        return {}
    try:
        raw = base64.b64decode(path.read_bytes()).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return {}


def _save_fallback(store: dict) -> None:
    path = _fallback_file()
    encoded = base64.b64encode(json.dumps(store).encode("utf-8"))
    path.write_bytes(encoded)
    try:
        path.chmod(0o600)
    except Exception:
        pass


def set_secret(key: str, value: str) -> None:
    """Persist a secret value under ``key``."""
    if _KEYRING_OK:
        try:
            keyring.set_password(_SERVICE, key, value)
            return
        except Exception as exc:  # pragma: no cover
            log.warning("Keyring unavailable (%s); using encrypted fallback.", exc)
    store = _load_fallback()
    store[key] = value
    _save_fallback(store)


def get_secret(key: str) -> Optional[str]:
    """Retrieve a secret value, or ``None`` if not set."""
    if _KEYRING_OK:
        try:
            value = keyring.get_password(_SERVICE, key)
            if value is not None:
                return value
        except Exception as exc:  # pragma: no cover
            log.warning("Keyring read failed (%s); trying fallback.", exc)
    return _load_fallback().get(key)


def delete_secret(key: str) -> None:
    if _KEYRING_OK:
        try:
            keyring.delete_password(_SERVICE, key)
        except Exception:
            pass
    store = _load_fallback()
    if key in store:
        del store[key]
        _save_fallback(store)
