"""Main application window — sidebar navigation + stacked tab content.

Owns the :class:`AutoResponder` engine, wires engine events to the UI (always
marshalled onto the Tk main thread), manages the system tray and window
lifecycle (minimise/close to tray).
"""
from __future__ import annotations

from typing import Dict, Optional

import customtkinter as ctk

from .. import __version__
from ..core.engine import AutoResponder, EngineEvent, EngineStatus
from ..core.updater import check_for_update
from ..models.repository import get_repository
from ..utils.config import get_config
from ..utils.i18n import get_i18n, t
from ..utils.logger import get_logger
from . import theme
from .dashboard_tab import DashboardTab
from .logs_tab import LogsTab
from .rules_tab import RulesTab
from .settings_tab import SettingsTab
from .stats_tab import StatsTab
from .templates_tab import TemplatesTab
from .tray import TrayManager
from .widgets import confirm_box

log = get_logger(__name__)

_NAV = [
    ("dashboard", "🏠", "nav_dashboard"),
    ("rules", "⚡", "nav_rules"),
    ("templates", "📝", "nav_templates"),
    ("stats", "📊", "nav_stats"),
    ("logs", "📜", "nav_logs"),
    ("settings", "⚙️", "nav_settings"),
]


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.cfg = get_config()
        self.repo = get_repository()
        self.i18n = get_i18n()
        self.engine = AutoResponder(self.repo)
        self.engine.add_listener(self._on_engine_event)

        self.tabs: Dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._current = "dashboard"

        self._setup_window()
        self._build_layout()
        self.select_tab("dashboard")

        self.i18n.add_observer(self._on_language_changed)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.tray = TrayManager(self)
        self.tray.start()

        self._uptime_tick()
        self.after(1500, self._check_updates_async)

        if self.cfg.get("start_minimized"):
            self.after(300, self.hide_window)

    # -- window setup -----------------------------------------------------
    def _setup_window(self) -> None:
        self.title(f"{t('app_title')} v{__version__}")
        self.geometry("1120x720")
        self.minsize(940, 600)
        try:
            from ..utils.paths import asset_path

            ico = asset_path("icons", "app.ico")
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        pal = theme.palette()
        self.content = ctk.CTkFrame(self, fg_color=pal["surface"],
                                    corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.tabs["dashboard"] = DashboardTab(self.content, self)
        self.tabs["rules"] = RulesTab(self.content, self)
        self.tabs["templates"] = TemplatesTab(self.content, self)
        self.tabs["stats"] = StatsTab(self.content, self)
        self.tabs["logs"] = LogsTab(self.content, self)
        self.tabs["settings"] = SettingsTab(self.content, self)
        for tab in self.tabs.values():
            tab.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
            tab.grid_remove()

    def _build_sidebar(self) -> None:
        pal = theme.palette()
        sidebar = ctk.CTkFrame(self, width=232, corner_radius=0,
                               fg_color=pal["card"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(len(_NAV) + 2, weight=1)
        sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(sidebar, text="🎮  FunPay",
                            font=theme.font(22, "bold"))
        logo.grid(row=0, column=0, sticky="w", padx=22, pady=(24, 0))
        ctk.CTkLabel(sidebar, text="AutoResponder", font=theme.font(13),
                     text_color=pal["text_muted"]).grid(row=1, column=0,
                                                         sticky="w", padx=22,
                                                         pady=(0, 18))

        for i, (key, icon, label_key) in enumerate(_NAV):
            btn = ctk.CTkButton(
                sidebar, text=f"  {icon}   {t(label_key)}", anchor="w",
                height=44, corner_radius=12, fg_color="transparent",
                text_color=("#1F2937", "#E5E7EB"),
                hover_color=pal["card_hover"], font=theme.font(14),
                command=lambda k=key: self.select_tab(k))
            btn.grid(row=i + 2, column=0, sticky="ew", padx=14, pady=3)
            self.nav_buttons[key] = btn

        # Bottom control block: status + start/stop
        control = ctk.CTkFrame(sidebar, fg_color="transparent")
        control.grid(row=len(_NAV) + 3, column=0, sticky="ew", padx=14,
                     pady=16)
        control.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(control, text="● " + t("stopped"),
                                         font=theme.font(13, "bold"),
                                         text_color=pal["danger"], anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.toggle_btn = ctk.CTkButton(
            control, text="▶  " + t("start"), height=42, corner_radius=12,
            fg_color=pal["accent"], hover_color=pal["accent_hover"],
            font=theme.font(14, "bold"), command=self.toggle_engine)
        self.toggle_btn.grid(row=1, column=0, sticky="ew")

    # -- navigation -------------------------------------------------------
    def select_tab(self, key: str) -> None:
        if key not in self.tabs:
            return
        pal = theme.palette()
        for name, tab in self.tabs.items():
            if name == key:
                tab.grid()
                if hasattr(tab, "on_show"):
                    tab.on_show()
            else:
                tab.grid_remove()
        for name, btn in self.nav_buttons.items():
            btn.configure(fg_color=pal["accent"] if name == key
                          else "transparent",
                          text_color="#FFFFFF" if name == key
                          else ("#1F2937", "#E5E7EB"))
        self._current = key

    # -- engine control ---------------------------------------------------
    def toggle_engine(self) -> None:
        if self.engine.is_running:
            self.stop_engine()
        else:
            self.start_engine()

    def start_engine(self) -> None:
        self.engine.start()

    def stop_engine(self) -> None:
        self.engine.stop()

    # -- engine events (called from worker threads) -----------------------
    def _on_engine_event(self, event: EngineEvent) -> None:
        self.run_on_ui(lambda e=event: self._handle_engine_event(e))

    def _handle_engine_event(self, event: EngineEvent) -> None:
        dash: DashboardTab = self.tabs["dashboard"]  # type: ignore
        if event.type == "status":
            status = EngineStatus(event.payload.get("status", "stopped"))
            self._update_status_ui(status)
        elif event.type == "processed":
            dash.add_activity(
                f"{event.payload.get('author', '?')}: "
                f"{event.payload.get('text', '')}", "in")
            dash.refresh_stats()
        elif event.type == "reply":
            dash.add_activity(
                f"→ {event.payload.get('author', '?')}: "
                f"{event.payload.get('text', '')}", "out")
            dash.refresh_stats()
        elif event.type == "stats":
            dash.refresh_stats()
            if self._current == "stats":
                self.tabs["stats"].reload()  # type: ignore
        elif event.type == "error":
            dash.add_activity(event.payload.get("message", "error"), "err")

    def _update_status_ui(self, status: EngineStatus) -> None:
        pal = theme.palette()
        running = status in (EngineStatus.RUNNING, EngineStatus.STARTING)
        color = pal["success"] if running else (
            pal["warning"] if status == EngineStatus.ERROR else pal["danger"])
        text = {
            EngineStatus.RUNNING: t("running"),
            EngineStatus.STARTING: t("start") + "…",
            EngineStatus.STOPPING: t("stop") + "…",
            EngineStatus.ERROR: t("error"),
            EngineStatus.STOPPED: t("stopped"),
        }.get(status, t("stopped"))
        self.status_label.configure(text="● " + text, text_color=color)
        self.toggle_btn.configure(
            text=("⏹  " + t("stop")) if running else ("▶  " + t("start")))
        self.tabs["dashboard"].update_status(status)  # type: ignore
        self.tray.update_status(status)

    # -- helpers ----------------------------------------------------------
    def run_on_ui(self, func) -> None:
        """Schedule ``func`` to run on the Tk main thread."""
        try:
            self.after(0, func)
        except Exception:
            pass

    def refresh_all_tabs(self) -> None:
        for tab in self.tabs.values():
            if hasattr(tab, "refresh_texts"):
                try:
                    tab.refresh_texts()
                except Exception:
                    pass

    def _on_language_changed(self, _language: str) -> None:
        self.title(f"{t('app_title')} v{__version__}")
        for key, _icon, label_key in _NAV:
            icon = dict((k, ic) for k, ic, _ in _NAV)[key]
            self.nav_buttons[key].configure(text=f"  {icon}   {t(label_key)}")
        self.refresh_all_tabs()
        self._update_status_ui(self.engine.status)

    def _uptime_tick(self) -> None:
        if self.engine.is_running:
            self.tabs["dashboard"].refresh_stats()  # type: ignore
        self.after(1000, self._uptime_tick)

    def _check_updates_async(self) -> None:
        import threading

        def worker() -> None:
            info = check_for_update()
            if info:
                self.run_on_ui(lambda: self._notify_update(info))

        threading.Thread(target=worker, daemon=True).start()

    def _notify_update(self, info) -> None:
        from .widgets import message_box

        message_box("Update available",
                    f"Version {info.version} is available.\n{info.notes}\n\n"
                    f"{info.url}", icon="info")

    # -- window lifecycle -------------------------------------------------
    def show_window(self, tab: Optional[str] = None) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        if tab:
            self.select_tab(tab)

    def hide_window(self) -> None:
        self.withdraw()

    def _on_close(self) -> None:
        if self.cfg.get("close_to_tray", True):
            self.hide_window()
        else:
            self.quit_app()

    def quit_app(self) -> None:
        if not confirm_box(t("confirm"), t("confirm_exit")):
            return
        log.info("Shutting down application.")
        try:
            self.engine.shutdown()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.cfg.close()
        except Exception:
            pass
        self.destroy()


def run_app() -> None:
    cfg = get_config()
    theme.init_theme(cfg.get("theme", "dark"),
                     cfg.get("color_theme", theme.DEFAULT_PALETTE))
    get_i18n().set_language(cfg.get("language", "ru"))
    app = MainWindow()
    app.mainloop()
