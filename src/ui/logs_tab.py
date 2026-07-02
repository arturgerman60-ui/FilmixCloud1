"""Real-time logs tab bound to the application logger."""
from __future__ import annotations

import customtkinter as ctk

from ..utils import logger as applog
from ..utils.i18n import t
from . import theme
from .widgets import GhostButton, SectionTitle

_LEVEL_COLORS = {
    "DEBUG": "#8B93A1",
    "INFO": "#6BA4F8",
    "WARNING": "#F59E0B",
    "ERROR": "#EF4444",
    "CRITICAL": "#EF4444",
}


class LogsTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._autoscroll = True
        self._build()
        self._backfill()
        applog.add_ui_listener(self._on_record)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 12))
        header.grid_columnconfigure(0, weight=1)
        self._title = SectionTitle(header, text=t("logs_title"))
        self._title.grid(row=0, column=0, sticky="w")

        self.chk_scroll = ctk.CTkSwitch(header, text=t("logs_autoscroll"),
                                        command=self._toggle_scroll)
        self.chk_scroll.select()
        self.chk_scroll.grid(row=0, column=1, padx=(0, 12))

        self.btn_clear = GhostButton(header, text="🧹 " + t("logs_clear"),
                                     width=130, command=self._clear)
        self.btn_clear.grid(row=0, column=2)

        self.box = ctk.CTkTextbox(self, corner_radius=12,
                                  font=("Cascadia Code", 12))
        self.box.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        for level, color in _LEVEL_COLORS.items():
            self.box.tag_config(level, foreground=color)
        self.box.configure(state="disabled")

    def _backfill(self) -> None:
        for entry in applog.recent_records()[-400:]:
            self._append(entry)

    def _on_record(self, entry: dict) -> None:
        # Logger fires from worker threads; marshal to the UI thread.
        try:
            self.after(0, lambda e=entry: self._append(e))
        except Exception:
            pass

    def _append(self, entry: dict) -> None:
        try:
            self.box.configure(state="normal")
            line = f"{entry['time']} │ {entry['level']:<7} │ {entry['message']}\n"
            self.box.insert("end", line, entry.get("level", "INFO"))
            if self._autoscroll:
                self.box.see("end")
            self.box.configure(state="disabled")
        except Exception:
            pass

    def _toggle_scroll(self) -> None:
        self._autoscroll = bool(self.chk_scroll.get())

    def _clear(self) -> None:
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        self.box.configure(state="disabled")

    def refresh_texts(self) -> None:
        self._title.configure(text=t("logs_title"))
        self.chk_scroll.configure(text=t("logs_autoscroll"))
        self.btn_clear.configure(text="🧹 " + t("logs_clear"))

    def on_show(self) -> None:
        pass

    def destroy(self) -> None:  # noqa: D401
        applog.remove_ui_listener(self._on_record)
        super().destroy()
