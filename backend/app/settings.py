from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional at import time
    load_dotenv = None  # type: ignore[assignment]


if load_dotenv:
    backend_env = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(backend_env)
    load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_source(raw_source: str) -> str:
    source = raw_source.strip()
    if not source:
        return source
    if source.startswith("https://") or source.startswith("http://"):
        parsed = urlparse(source)
        path = parsed.path.strip("/")
        if path:
            source = path.split("/")[0]
    if source.startswith("@"):
        source = source[1:]
    return source.lower()


@dataclass(slots=True)
class TelegramSettings:
    enabled: bool
    bot_token: str | None
    api_id: int | None
    api_hash: str | None
    session_string: str | None
    sources: list[str]
    poll_seconds: int

    @property
    def is_configured(self) -> bool:
        return self.is_bot_configured or self.is_telethon_configured or self.is_web_configured

    @property
    def is_bot_configured(self) -> bool:
        return bool(self.enabled and self.bot_token and self.sources)

    @property
    def is_telethon_configured(self) -> bool:
        return bool(
            self.enabled
            and self.api_id
            and self.api_hash
            and self.session_string
            and self.sources
        )

    @property
    def web_sources(self) -> list[str]:
        # Web fallback can ingest only public channel usernames (not numeric IDs).
        return [source for source in self.sources if source and not source.startswith("-")]

    @property
    def is_web_configured(self) -> bool:
        return bool(self.enabled and self.web_sources)


def load_telegram_settings() -> TelegramSettings:
    api_id_raw = os.getenv("TELEGRAM_API_ID")
    api_id = int(api_id_raw) if api_id_raw and api_id_raw.isdigit() else None
    return TelegramSettings(
        enabled=_env_bool("TELEGRAM_ENABLED", default=False),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        api_id=api_id,
        api_hash=os.getenv("TELEGRAM_API_HASH"),
        session_string=os.getenv("TELEGRAM_SESSION_STRING"),
        sources=[_normalize_source(item) for item in _split_csv("TELEGRAM_SOURCES")],
        poll_seconds=max(10, int(os.getenv("TELEGRAM_POLL_SECONDS", "20"))),
    )
