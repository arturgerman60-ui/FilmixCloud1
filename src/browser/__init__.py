"""Browser automation layer for FunPay.

Exposes a common :class:`BaseFunPayClient` interface with two implementations:

* :class:`PlaywrightFunPayClient` — real automation via Playwright.
* :class:`MockFunPayClient`      — offline simulator used for demos, first-run
  experience and environments without browser binaries/credentials.

Use :func:`create_client` to obtain the right implementation based on settings
and availability.
"""
from __future__ import annotations

from ..utils.config import get_config
from ..utils.logger import get_logger
from .base import BaseFunPayClient, ClientState
from .mock_client import MockFunPayClient

log = get_logger(__name__)


def create_client(account, *, force_mock: bool = False) -> BaseFunPayClient:
    """Factory that returns a usable client.

    Falls back to the mock client when Playwright (or its browser binaries) is
    unavailable, or when no account credentials are configured — so the app is
    always runnable.
    """
    cfg = get_config()
    if force_mock:
        log.info("Using MockFunPayClient (forced).")
        return MockFunPayClient(account)

    if account is None:
        log.warning("No account configured — using MockFunPayClient (demo mode).")
        return MockFunPayClient(account)

    try:
        from .funpay_client import PlaywrightFunPayClient  # lazy import

        if PlaywrightFunPayClient.is_available():
            return PlaywrightFunPayClient(
                account,
                headless=bool(cfg.get("headless", True)),
            )
        log.warning("Playwright not available — falling back to demo mode.")
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to init Playwright client (%s) — demo mode.", exc)

    return MockFunPayClient(account)


__all__ = [
    "BaseFunPayClient",
    "ClientState",
    "MockFunPayClient",
    "create_client",
]
