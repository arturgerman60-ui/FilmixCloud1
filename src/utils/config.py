"""Application configuration store.

Thin, thread-safe wrapper around TinyDB that exposes a dictionary-like API for
settings plus dedicated tables for rules, templates, accounts, statistics and
message history. Falls back to a pure-JSON implementation if TinyDB is missing.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Dict

from .logger import get_logger
from .paths import db_path

log = get_logger(__name__)

DEFAULT_SETTINGS: Dict[str, Any] = {
    # General
    "language": "ru",              # ru | en
    "theme": "dark",               # dark | light | system + custom names
    "color_theme": "funpay-blue",
    "minimize_to_tray": True,
    "close_to_tray": True,
    "autostart_windows": False,
    "start_minimized": False,

    # Engine timing (anti-spam / anti-ban)
    "poll_min_seconds": 3,
    "poll_max_seconds": 8,
    "reply_delay_min": 8,
    "reply_delay_max": 25,
    "typing_simulation": True,
    "human_jitter": True,

    # Work mode
    "work_mode": "all_chats",      # new_dialogs | all_chats | specific_games
    "specific_games": [],
    "auto_status_online": True,

    # Filters
    "whitelist": [],
    "blacklist": [],

    # Network
    "headless": True,
    "proxy_enabled": False,
    "proxy_type": "http",          # http | socks5
    "proxy_host": "",
    "proxy_port": 0,
    "proxy_user": "",

    # Notifications
    "notifications_enabled": True,
    "sound_enabled": True,
    "sound_file": "notify.wav",

    # AI
    "ai_backend": "none",          # none | ollama | lmstudio
    "ai_base_url": "http://localhost:11434",
    "ai_model": "llama3.1",
    "ai_system_prompt": "You are a helpful, concise marketplace seller assistant.",
    "ai_fallback_only": True,      # only use AI when no rule matches

    # Updates
    "auto_update_check": True,
    "update_manifest_url": "",

    # Hotkeys
    "hotkey_toggle": "<Control-space>",
    "hotkey_show": "<Control-Shift-F>",

    "active_account_id": None,
}


class ConfigStore:
    """Persistent config + data tables."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._path = db_path()
        self._use_tinydb = False
        self._data: Dict[str, Any] = {}
        self._init_backend()

    # -- backend ----------------------------------------------------------
    def _init_backend(self) -> None:
        try:
            from tinydb import TinyDB  # noqa: F401

            self._use_tinydb = True
            from tinydb import TinyDB as _TinyDB

            self._db = _TinyDB(self._path, indent=2, ensure_ascii=False)
            self._settings_table = self._db.table("settings")
            log.debug("Config backend: TinyDB (%s)", self._path)
        except Exception as exc:
            log.warning("TinyDB unavailable (%s); using JSON fallback.", exc)
            self._use_tinydb = False
            self._load_json()
        self._ensure_defaults()

    def _load_json(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}
        self._data.setdefault("settings", {})
        for table in ("rules", "templates", "accounts", "stats", "history"):
            self._data.setdefault(table, [])

    def _save_json(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _ensure_defaults(self) -> None:
        with self._lock:
            current = self.all_settings()
            merged = {**DEFAULT_SETTINGS, **current}
            if merged != current:
                self._write_settings(merged)

    # -- settings ---------------------------------------------------------
    def all_settings(self) -> Dict[str, Any]:
        with self._lock:
            if self._use_tinydb:
                rows = self._settings_table.all()
                return dict(rows[0]) if rows else {}
            return dict(self._data.get("settings", {}))

    def _write_settings(self, settings: Dict[str, Any]) -> None:
        if self._use_tinydb:
            self._settings_table.truncate()
            self._settings_table.insert(settings)
        else:
            self._data["settings"] = settings
            self._save_json()

    def get(self, key: str, default: Any = None) -> Any:
        return self.all_settings().get(key, DEFAULT_SETTINGS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            settings = self.all_settings()
            settings[key] = value
            self._write_settings(settings)

    def update(self, values: Dict[str, Any]) -> None:
        with self._lock:
            settings = self.all_settings()
            settings.update(values)
            self._write_settings(settings)

    # -- generic tables ---------------------------------------------------
    def table_all(self, name: str) -> list[dict]:
        with self._lock:
            if self._use_tinydb:
                return [dict(r) for r in self._db.table(name).all()]
            return list(self._data.get(name, []))

    def table_replace(self, name: str, rows: list[dict]) -> None:
        with self._lock:
            if self._use_tinydb:
                tbl = self._db.table(name)
                tbl.truncate()
                if rows:
                    tbl.insert_multiple(rows)
            else:
                self._data[name] = rows
                self._save_json()

    def close(self) -> None:
        with self._lock:
            if self._use_tinydb:
                try:
                    self._db.close()
                except Exception:
                    pass


# Singleton accessor --------------------------------------------------------
_instance: ConfigStore | None = None
_instance_lock = threading.Lock()


def get_config() -> ConfigStore:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ConfigStore()
    return _instance
