from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.schemas import ReportIn
from app.settings import TelegramSettings
from app.store import EventStore

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    TELETHON_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on optional runtime package
    TELETHON_AVAILABLE = False
    TelegramClient = Any  # type: ignore[assignment,misc]
    StringSession = Any  # type: ignore[assignment,misc]


def _entity_key(entity: Any) -> str:
    username = getattr(entity, "username", None)
    if username:
        return str(username).lower()
    identifier = getattr(entity, "id", None)
    if identifier is not None:
        return str(identifier)
    title = getattr(entity, "title", None)
    return str(title or "unknown").strip().lower()


def _entity_label(entity: Any) -> str:
    return str(getattr(entity, "title", None) or getattr(entity, "username", None) or _entity_key(entity))


class TelegramIngestor:
    def __init__(self, store: EventStore, settings: TelegramSettings) -> None:
        self.store = store
        self.settings = settings
        self.running = False
        self.last_error: str | None = None
        self.last_poll_at: datetime | None = None
        self.ingested_count = 0
        self._client: TelegramClient | None = None
        self._stop_event = asyncio.Event()
        self._last_seen_message_id: dict[str, int] = {}

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "configured": self.settings.is_configured,
            "telethon_available": TELETHON_AVAILABLE,
            "running": self.running,
            "sources": self.settings.sources,
            "ingested_count": self.ingested_count,
            "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
            "last_error": self.last_error,
        }

    async def stop(self) -> None:
        self._stop_event.set()
        if self._client:
            await self._client.disconnect()

    async def run_forever(self) -> None:
        if not self.settings.enabled:
            return
        if not TELETHON_AVAILABLE:
            self.last_error = "telethon is not installed"
            return
        if not self.settings.is_configured:
            self.last_error = "telegram settings are incomplete"
            return

        self.running = True
        try:
            self._client = TelegramClient(
                StringSession(self.settings.session_string),
                self.settings.api_id,
                self.settings.api_hash,
            )
            await self._client.connect()
            entities = [await self._client.get_entity(source) for source in self.settings.sources]

            while not self._stop_event.is_set():
                for entity in entities:
                    await self._sync_entity(entity)
                self.last_poll_at = datetime.now(UTC)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.settings.poll_seconds)
                except asyncio.TimeoutError:
                    continue
        except Exception as exc:  # pragma: no cover - depends on external Telegram I/O
            self.last_error = str(exc)
        finally:
            self.running = False
            if self._client:
                await self._client.disconnect()

    async def _sync_entity(self, entity: Any) -> None:
        if not self._client:
            return
        entity_key = _entity_key(entity)
        messages = await self._client.get_messages(entity, limit=25)
        if not messages:
            return
        if entity_key not in self._last_seen_message_id:
            self._last_seen_message_id[entity_key] = max(getattr(message, "id", 0) for message in messages)
            return
        last_seen = self._last_seen_message_id[entity_key]
        incoming = sorted(
            (message for message in messages if getattr(message, "id", 0) > last_seen),
            key=lambda message: getattr(message, "id", 0),
        )
        for message in incoming:
            text = str(getattr(message, "message", "") or "").strip()
            if not text:
                continue
            source_message_id = f"{entity_key}:{message.id}"
            report = ReportIn(
                text=text,
                source=f"tg:{_entity_label(entity)}",
                source_message_id=source_message_id,
                observed_at=getattr(message, "date", None),
            )
            self.store.create_from_report(report)
            self.ingested_count += 1
            self._last_seen_message_id[entity_key] = max(
                self._last_seen_message_id[entity_key],
                int(message.id),
            )
