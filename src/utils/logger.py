"""Application logging.

Provides a rotating file logger plus an in-memory pub/sub bridge so the UI
"Logs" tab can display events in real time. Any module obtains a logger via
``get_logger(__name__)``; the UI subscribes through ``add_ui_listener``.
"""
from __future__ import annotations

import logging
import os
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Callable, Deque, List

from .paths import logs_dir

_CONFIGURED = False
_MAX_MEMORY_RECORDS = 2000

# Ring buffer of recent formatted records so a freshly opened UI can backfill.
_memory_buffer: Deque[dict] = deque(maxlen=_MAX_MEMORY_RECORDS)
_ui_listeners: List[Callable[[dict], None]] = []


class _UIBridgeHandler(logging.Handler):
    """Fan-out handler that pushes records to the in-memory buffer + UI."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            entry = {
                "time": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            }
        except Exception:  # pragma: no cover - never let logging crash the app
            return
        _memory_buffer.append(entry)
        for listener in list(_ui_listeners):
            try:
                listener(entry)
            except Exception:
                # A broken listener must never break logging.
                pass


def setup_logging(level: str | None = None) -> None:
    """Initialise the root application logger (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = (level or os.environ.get("FPAR_LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger("fpar")
    root.setLevel(log_level)
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        logs_dir() / "funpay_autoresponder.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(log_level)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(log_level)
    root.addHandler(console)

    root.addHandler(_UIBridgeHandler())

    _CONFIGURED = True


def get_logger(name: str = "fpar") -> logging.Logger:
    """Return a child logger under the app namespace."""
    if not name.startswith("fpar"):
        name = f"fpar.{name}"
    return logging.getLogger(name)


def add_ui_listener(callback: Callable[[dict], None]) -> None:
    """Register a UI callback invoked for every new log record."""
    if callback not in _ui_listeners:
        _ui_listeners.append(callback)


def remove_ui_listener(callback: Callable[[dict], None]) -> None:
    if callback in _ui_listeners:
        _ui_listeners.remove(callback)


def recent_records() -> list[dict]:
    """Snapshot of buffered records for UI backfill."""
    return list(_memory_buffer)
