"""Desktop notifications + sound alerts.

Notifications are delivered through the system-tray icon when available (set by
the tray module via :func:`set_tray_icon`) and always mirrored to the log. Sound
playback is best-effort and non-blocking.
"""
from __future__ import annotations

import threading
from typing import Optional

from ..utils.config import get_config
from ..utils.helpers import truncate
from ..utils.logger import get_logger
from ..utils.paths import asset_path

log = get_logger(__name__)

_tray_icon = None  # set by the tray manager once created


def set_tray_icon(icon) -> None:
    global _tray_icon
    _tray_icon = icon


def notify(title: str, message: str, *, sound: bool = True) -> None:
    """Show a desktop notification with a short message preview."""
    cfg = get_config()
    if not cfg.get("notifications_enabled", True):
        return

    preview = truncate(message, 120)
    if _tray_icon is not None:
        try:
            _tray_icon.notify(preview, title)
        except Exception as exc:  # pragma: no cover
            log.debug("Tray notify failed: %s", exc)
    log.info("🔔 %s — %s", title, preview)

    if sound and cfg.get("sound_enabled", True):
        play_sound(cfg.get("sound_file", "notify.wav"))


def play_sound(filename: Optional[str] = None) -> None:
    """Play an alert sound without blocking the caller."""
    def _run() -> None:
        try:
            path = asset_path("sounds", filename or "notify.wav")
            if not path.exists():
                return
            import sys

            if sys.platform.startswith("win"):
                import winsound

                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["afplay", str(path)])
            else:
                import subprocess

                for player in ("paplay", "aplay", "ffplay"):
                    try:
                        subprocess.Popen(
                            [player, "-nodisp", "-autoexit", str(path)]
                            if player == "ffplay" else [player, str(path)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        break
                    except FileNotFoundError:
                        continue
        except Exception as exc:  # pragma: no cover
            log.debug("Sound playback failed: %s", exc)

    threading.Thread(target=_run, daemon=True).start()
