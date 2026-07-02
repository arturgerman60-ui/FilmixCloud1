"""System tray integration via pystray.

The tray icon runs on its own thread. All menu callbacks marshal work back to
the Tk main thread through ``app.run_on_ui`` so we never touch widgets off the
main thread.
"""
from __future__ import annotations

import threading
from typing import Optional

from ..core import notifier
from ..core.engine import EngineStatus
from ..utils.i18n import t
from ..utils.logger import get_logger
from ..utils.paths import asset_path

log = get_logger(__name__)


class TrayManager:
    def __init__(self, app) -> None:
        self.app = app
        self._icon = None
        self._thread: Optional[threading.Thread] = None

    # -- icon image -------------------------------------------------------
    def _load_image(self):
        from PIL import Image

        ico = asset_path("icons", "tray.png")
        if ico.exists():
            try:
                return Image.open(ico)
            except Exception:
                pass
        # Fallback: draw a simple badge if the asset is missing.
        from PIL import ImageDraw

        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 60, 60), fill=(59, 130, 246, 255))
        draw.text((22, 18), "F", fill="white")
        return img

    # -- lifecycle --------------------------------------------------------
    def start(self) -> None:
        try:
            import pystray
        except Exception as exc:
            log.warning("pystray unavailable (%s); tray disabled.", exc)
            return

        menu = pystray.Menu(
            pystray.MenuItem(t("tray_show"), self._on_show, default=True),
            pystray.MenuItem(t("tray_start"), self._on_start),
            pystray.MenuItem(t("tray_stop"), self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_settings"), self._on_settings),
            pystray.MenuItem(t("tray_stats"), self._on_stats),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray_exit"), self._on_exit),
        )
        self._icon = pystray.Icon("fpar", self._load_image(),
                                  "FunPay AutoResponder", menu)
        notifier.set_tray_icon(self._icon)
        self._thread = threading.Thread(target=self._icon.run, daemon=True,
                                        name="fpar-tray")
        self._thread.start()
        log.info("System tray icon started.")

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def update_status(self, status: EngineStatus) -> None:
        if self._icon:
            try:
                self._icon.title = f"FunPay AutoResponder — {status.value}"
            except Exception:
                pass

    # -- callbacks (run on UI thread) -------------------------------------
    def _on_show(self, *_):
        self.app.run_on_ui(self.app.show_window)

    def _on_settings(self, *_):
        self.app.run_on_ui(lambda: self.app.show_window("settings"))

    def _on_stats(self, *_):
        self.app.run_on_ui(lambda: self.app.show_window("stats"))

    def _on_start(self, *_):
        self.app.run_on_ui(self.app.start_engine)

    def _on_stop(self, *_):
        self.app.run_on_ui(self.app.stop_engine)

    def _on_exit(self, *_):
        self.app.run_on_ui(self.app.quit_app)
