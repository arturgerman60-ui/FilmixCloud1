from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(slots=True)
class TelegramSettings:
    enabled: bool
    api_id: int | None
    api_hash: str | None
    session_string: str | None
    sources: list[str]
    poll_seconds: int

    @property
    def is_configured(self) -> bool:
        return bool(
            self.enabled
            and self.api_id
            and self.api_hash
            and self.session_string
            and self.sources
        )


def load_telegram_settings() -> TelegramSettings:
    api_id_raw = os.getenv("TELEGRAM_API_ID")
    api_id = int(api_id_raw) if api_id_raw and api_id_raw.isdigit() else None
    return TelegramSettings(
        enabled=_env_bool("TELEGRAM_ENABLED", default=False),
        api_id=api_id,
        api_hash=os.getenv("TELEGRAM_API_HASH"),
        session_string=os.getenv("TELEGRAM_SESSION_STRING"),
        sources=_split_csv("TELEGRAM_SOURCES"),
        poll_seconds=max(10, int(os.getenv("TELEGRAM_POLL_SECONDS", "20"))),
    )
