"""Dashboard tab: live status, key metrics and recent activity feed."""
from __future__ import annotations

import customtkinter as ctk

from ..core.engine import EngineStatus
from ..utils.i18n import t
from . import theme
from .widgets import AccentButton, Card, SectionTitle, StatCard, attach_tooltip


class DashboardTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()
        self.refresh_stats()

    # -- layout -----------------------------------------------------------
    def _build(self) -> None:
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._title = SectionTitle(self, text=t("nav_dashboard"))
        self._title.grid(row=0, column=0, columnspan=4, sticky="w",
                         padx=4, pady=(4, 16))

        pal = theme.palette()
        self.card_processed = StatCard(self, icon="💬",
                                       label=t("dash_processed"),
                                       accent=pal["accent"])
        self.card_replies = StatCard(self, icon="✉️", label=t("dash_replies"),
                                     accent=pal["success"])
        self.card_earned = StatCard(self, icon="💰", label=t("dash_earned"),
                                    accent=pal["warning"])
        self.card_uptime = StatCard(self, icon="⏱️", label=t("dash_uptime"),
                                    accent=pal["accent"])
        for i, card in enumerate((self.card_processed, self.card_replies,
                                  self.card_earned, self.card_uptime)):
            card.grid(row=1, column=i, sticky="nsew", padx=8, pady=8)

        # Control / status card
        self.control = Card(self)
        self.control.grid(row=2, column=0, columnspan=4, sticky="nsew",
                          padx=8, pady=8)
        self.control.grid_columnconfigure(1, weight=1)

        self._status_dot = ctk.CTkLabel(self.control, text="●",
                                        font=theme.font(30),
                                        text_color=pal["danger"])
        self._status_dot.grid(row=0, column=0, padx=(20, 8), pady=18)

        self._status_text = ctk.CTkLabel(self.control, text=t("stopped"),
                                         font=theme.font(18, "bold"), anchor="w")
        self._status_text.grid(row=0, column=1, sticky="w", pady=(14, 0))

        self._account_text = ctk.CTkLabel(self.control,
                                          text=t("dash_no_account"),
                                          font=theme.font(12),
                                          text_color=pal["text_muted"],
                                          anchor="w")
        self._account_text.grid(row=1, column=1, sticky="w", pady=(0, 14))

        self.btn_toggle = AccentButton(self.control, text=t("start"),
                                       width=160, command=self.app.toggle_engine)
        self.btn_toggle.grid(row=0, column=2, rowspan=2, padx=20, pady=18)
        attach_tooltip(self.btn_toggle, "Start / stop the auto-responder")

        # Recent activity
        self.activity_card = Card(self)
        self.activity_card.grid(row=3, column=0, columnspan=4, sticky="nsew",
                                padx=8, pady=8)
        self.activity_card.grid_columnconfigure(0, weight=1)
        self.activity_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.activity_card, text=t("dash_recent"),
                     font=theme.font(15, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        self.activity = ctk.CTkScrollableFrame(self.activity_card,
                                               fg_color="transparent")
        self.activity.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))
        self.activity.grid_columnconfigure(0, weight=1)
        self._activity_rows = 0

    # -- updates ----------------------------------------------------------
    def refresh_texts(self) -> None:
        self._title.configure(text=t("nav_dashboard"))
        self.card_processed.set_label(t("dash_processed"))
        self.card_replies.set_label(t("dash_replies"))
        self.card_earned.set_label(t("dash_earned"))
        self.card_uptime.set_label(t("dash_uptime"))
        self.update_status(self.app.engine.status)

    def refresh_stats(self) -> None:
        stats = self.app.repo.stats
        self.card_processed.set_value(str(stats.messages_processed))
        self.card_replies.set_value(str(stats.replies_sent))
        self.card_earned.set_value(f"{stats.earned:.0f} ₽")
        self.card_uptime.set_value(self._fmt_uptime(self.app.engine.uptime_seconds))
        acc = self.app.repo.active_account()
        self._account_text.configure(
            text=f"{t('dash_account')}: {acc.label}" if acc
            else t("dash_no_account"))

    def _fmt_uptime(self, seconds: int) -> str:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def update_status(self, status: EngineStatus) -> None:
        pal = theme.palette()
        running = status in (EngineStatus.RUNNING, EngineStatus.STARTING)
        color = pal["success"] if running else (
            pal["warning"] if status == EngineStatus.ERROR else pal["danger"])
        self._status_dot.configure(text_color=color)
        text_map = {
            EngineStatus.RUNNING: t("running"),
            EngineStatus.STARTING: t("start") + "…",
            EngineStatus.STOPPING: t("stop") + "…",
            EngineStatus.ERROR: t("error"),
            EngineStatus.STOPPED: t("stopped"),
        }
        self._status_text.configure(text=text_map.get(status, t("stopped")))
        self.btn_toggle.configure(text=t("stop") if running else t("start"))

    def add_activity(self, text: str, kind: str = "in") -> None:
        pal = theme.palette()
        icon = {"in": "📩", "out": "✅", "err": "⚠️"}.get(kind, "•")
        color = {"in": pal["text_muted"], "out": pal["success"],
                 "err": pal["danger"]}.get(kind, pal["text_muted"])
        row = ctk.CTkLabel(self.activity, text=f"{icon}  {text}",
                           font=theme.font(12), text_color=color, anchor="w",
                           justify="left")
        row.grid(row=self._activity_rows, column=0, sticky="ew", padx=8, pady=2)
        self._activity_rows += 1
        # Keep the feed light.
        if self._activity_rows > 60:
            for child in self.activity.winfo_children()[:20]:
                child.destroy()

    def on_show(self) -> None:
        self.refresh_stats()
