from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx
try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on optional runtime package
    BeautifulSoup = Any  # type: ignore[assignment,misc]
    BS4_AVAILABLE = False

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
        self._http: httpx.AsyncClient | None = None
        self._stop_event = asyncio.Event()
        self._last_seen_message_id: dict[str, int] = {}
        self._bot_offset = 0

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "configured": self.settings.is_configured,
            "bot_configured": self.settings.is_bot_configured,
            "telethon_configured": self.settings.is_telethon_configured,
            "web_configured": self.settings.is_web_configured,
            "mode": self._mode(),
            "telethon_available": TELETHON_AVAILABLE,
            "bs4_available": BS4_AVAILABLE,
            "running": self.running,
            "sources": self.settings.sources,
            "ingested_count": self.ingested_count,
            "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
            "last_error": self.last_error,
        }

    def _mode(self) -> str:
        if self.settings.is_bot_configured:
            return "bot_api"
        if self.settings.is_telethon_configured:
            return "telethon"
        if self.settings.is_web_configured:
            return "web_public"
        return "none"

    async def stop(self) -> None:
        self._stop_event.set()
        if self._client:
            await self._client.disconnect()
        if self._http:
            await self._http.aclose()

    async def run_forever(self) -> None:
        if not self.settings.enabled:
            return
        if not self.settings.is_configured:
            self.last_error = "telegram settings are incomplete"
            return

        self.running = True
        try:
            if self.settings.is_bot_configured:
                await self._run_bot_api_forever()
            elif self.settings.is_telethon_configured:
                await self._run_telethon_forever()
            elif self.settings.is_web_configured:
                await self._run_web_public_forever()
            else:
                self.last_error = "telegram settings are incomplete"
        except Exception as exc:  # pragma: no cover - depends on external Telegram I/O
            self.last_error = str(exc)
        finally:
            self.running = False
            if self._client:
                await self._client.disconnect()
            if self._http:
                await self._http.aclose()

    async def _run_bot_api_forever(self) -> None:
        self._http = httpx.AsyncClient(timeout=60.0)
        if self._bot_offset == 0:
            bootstrap_updates = await self._bot_get_updates(timeout=1)
            if bootstrap_updates:
                self._bot_offset = max(int(update["update_id"]) for update in bootstrap_updates) + 1
        while not self._stop_event.is_set():
            updates = await self._bot_get_updates(timeout=max(self.settings.poll_seconds, 10))
            for update in updates:
                update_id = int(update["update_id"])
                self._bot_offset = max(self._bot_offset, update_id + 1)
                await self._ingest_bot_update(update)
            self.last_poll_at = datetime.now(UTC)

    async def _bot_get_updates(self, timeout: int) -> list[dict[str, Any]]:
        if not self._http or not self.settings.bot_token:
            return []
        response = await self._http.get(
            f"https://api.telegram.org/bot{self.settings.bot_token}/getUpdates",
            params={
                "timeout": timeout,
                "offset": self._bot_offset if self._bot_offset else None,
                "allowed_updates": json.dumps(
                    ["message", "edited_message", "channel_post", "edited_channel_post"]
                ),
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"telegram bot api error: {payload}")
        return payload.get("result", [])

    def _chat_allowed(self, chat: dict[str, Any]) -> bool:
        allowed = set(self.settings.sources)
        if not allowed:
            return True
        chat_id = str(chat.get("id", ""))
        username = str(chat.get("username", "")).lower()
        title = str(chat.get("title", "")).lower()
        return bool(
            chat_id in allowed
            or username in allowed
            or title in allowed
            or f"@{username}" in allowed
        )

    async def _ingest_bot_update(self, update: dict[str, Any]) -> None:
        message = (
            update.get("channel_post")
            or update.get("edited_channel_post")
            or update.get("message")
            or update.get("edited_message")
        )
        if not message:
            return
        chat = message.get("chat") or {}
        if not self._chat_allowed(chat):
            return
        text = str(message.get("text") or message.get("caption") or "").strip()
        if not text:
            return
        chat_id = str(chat.get("id", "unknown"))
        message_id = int(message.get("message_id", 0))
        observed_at_raw = message.get("date")
        observed_at = (
            datetime.fromtimestamp(observed_at_raw, tz=UTC)
            if isinstance(observed_at_raw, int)
            else None
        )
        source_label = str(chat.get("title") or chat.get("username") or chat_id)
        report = ReportIn(
            text=text,
            source=f"tg:{source_label}",
            source_message_id=f"{chat_id}:{message_id}",
            observed_at=observed_at,
        )
        self.store.create_from_report(report)
        self.ingested_count += 1
        self.last_poll_at = datetime.now(UTC)

    async def _run_telethon_forever(self) -> None:
        if not TELETHON_AVAILABLE:
            self.last_error = "telethon is not installed"
            return
        self._client = TelegramClient(
            StringSession(self.settings.session_string),
            self.settings.api_id,
            self.settings.api_hash,
        )
        await self._client.connect()
        entities = [await self._client.get_entity(source) for source in self.settings.sources]

        while not self._stop_event.is_set():
            for entity in entities:
                await self._sync_entity(entity, bootstrap_on_first_seen=True)
            self.last_poll_at = datetime.now(UTC)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.settings.poll_seconds)
            except asyncio.TimeoutError:
                continue

    async def _run_web_public_forever(self) -> None:
        if not BS4_AVAILABLE:
            self.last_error = "beautifulsoup4 is not installed"
            return
        self._http = httpx.AsyncClient(timeout=30.0)
        while not self._stop_event.is_set():
            for source in self.settings.web_sources:
                await self._sync_web_source(source)
            self.last_poll_at = datetime.now(UTC)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.settings.poll_seconds)
            except asyncio.TimeoutError:
                continue

    async def _sync_web_source(self, source: str) -> None:
        if not self._http:
            return
        response = await self._http.get(f"https://t.me/s/{source}")
        response.raise_for_status()
        messages = self._extract_web_messages(response.text, fallback_source=source)
        if not messages:
            return
        source_key = f"web:{source}"
        if source_key not in self._last_seen_message_id:
            ordered = sorted(messages, key=lambda item: item["message_id"])
            if self.settings.bootstrap_limit > 0:
                for message in ordered[-self.settings.bootstrap_limit :]:
                    self._ingest_web_message(message)
            self._last_seen_message_id[source_key] = max(message["message_id"] for message in ordered)
            return
        last_seen = self._last_seen_message_id[source_key]
        incoming = sorted(
            (message for message in messages if message["message_id"] > last_seen),
            key=lambda item: item["message_id"],
        )
        for message in incoming:
            self._ingest_web_message(message)
            self._last_seen_message_id[source_key] = max(
                self._last_seen_message_id[source_key],
                int(message["message_id"]),
            )

    def _extract_web_messages(self, html: str, fallback_source: str) -> list[dict[str, Any]]:
        if not BS4_AVAILABLE:
            return []
        soup = BeautifulSoup(html, "html.parser")
        messages: list[dict[str, Any]] = []
        for widget in soup.select("div.tgme_widget_message"):
            data_post = str(widget.get("data-post", ""))
            if "/" not in data_post:
                continue
            source, message_id_raw = data_post.rsplit("/", 1)
            if not message_id_raw.isdigit():
                continue
            text_node = widget.select_one("div.tgme_widget_message_text")
            if not text_node:
                continue
            text = text_node.get_text(" ", strip=True)
            if not text:
                continue
            timestamp_raw = str(widget.get("data-time", ""))
            observed_at = (
                datetime.fromtimestamp(int(timestamp_raw), tz=UTC)
                if timestamp_raw.isdigit()
                else None
            )
            messages.append(
                {
                    "source": str(source or fallback_source).lower(),
                    "message_id": int(message_id_raw),
                    "text": text,
                    "observed_at": observed_at,
                }
            )
        return messages

    def _ingest_web_message(self, message: dict[str, Any]) -> None:
        source = str(message.get("source", "unknown"))
        message_id = int(message.get("message_id", 0))
        text = str(message.get("text", "")).strip()
        if not text:
            return
        report = ReportIn(
            text=text,
            source=f"tg-web:{source}",
            source_message_id=f"{source}:{message_id}",
            observed_at=message.get("observed_at"),
        )
        self.store.create_from_report(report)
        self.ingested_count += 1

    async def _sync_entity(self, entity: Any, bootstrap_on_first_seen: bool = False) -> None:
        if not self._client:
            return
        entity_key = _entity_key(entity)
        messages = await self._client.get_messages(entity, limit=25)
        if not messages:
            return
        if entity_key not in self._last_seen_message_id:
            ordered = sorted(messages, key=lambda message: getattr(message, "id", 0))
            if bootstrap_on_first_seen and self.settings.bootstrap_limit > 0:
                for message in ordered[-self.settings.bootstrap_limit :]:
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
            self._last_seen_message_id[entity_key] = max(getattr(message, "id", 0) for message in ordered)
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
