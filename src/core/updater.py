"""Lightweight auto-update checker.

Fetches a JSON manifest (URL configurable in settings) of the shape::

    {"version": "1.1.0", "url": "https://.../setup.exe", "notes": "..."}

and compares it with the running version. Downloading/applying the update is
left to the user (the URL is surfaced in the UI) to keep the app store-safe and
avoid silent code execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .. import __version__
from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class UpdateInfo:
    version: str
    url: str
    notes: str = ""


def _parse_version(text: str) -> tuple:
    parts = []
    for chunk in str(text).strip().lstrip("v").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_update() -> Optional[UpdateInfo]:
    cfg = get_config()
    if not cfg.get("auto_update_check", True):
        return None
    url = cfg.get("update_manifest_url", "")
    if not url:
        return None
    try:
        import requests

        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        latest = data.get("version", "0.0.0")
        if _parse_version(latest) > _parse_version(__version__):
            log.info("Update available: %s (current %s)", latest, __version__)
            return UpdateInfo(version=latest, url=data.get("url", ""),
                              notes=data.get("notes", ""))
        log.debug("Application is up to date (%s).", __version__)
    except Exception as exc:
        log.debug("Update check failed: %s", exc)
    return None
