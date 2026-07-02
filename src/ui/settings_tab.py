"""Settings tab: all configuration grouped into cards + FunPay account setup."""
from __future__ import annotations

import threading
from tkinter import filedialog

import customtkinter as ctk

from ..core import settings_io
from ..core.ai_client import AIClient
from ..models.account import Account
from ..utils import autostart, security
from ..utils.i18n import get_i18n, t
from ..utils.logger import get_logger
from . import theme
from .widgets import (AccentButton, Card, GhostButton, SectionTitle,
                      labeled_entry, message_box, toast)

log = get_logger(__name__)


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.cfg = app.cfg
        self._vars: dict = {}
        self._build()

    # -- helpers ----------------------------------------------------------
    def _section(self, parent, title: str) -> ctk.CTkFrame:
        card = Card(parent)
        card.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(card, text=title, font=theme.font(16, "bold"),
                     anchor="w").grid(row=0, column=0, columnspan=2,
                                      sticky="w", padx=18, pady=(14, 8))
        return card

    def _switch(self, parent, key: str, label: str, row: int) -> None:
        var = ctk.BooleanVar(value=bool(self.cfg.get(key)))
        self._vars[key] = var
        sw = ctk.CTkSwitch(parent, text=label, variable=var)
        sw.grid(row=row, column=0, columnspan=2, sticky="w", padx=18, pady=6)

    def _entry(self, parent, key: str, label: str, row: int, col: int = 0,
               width: int = 120) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, sticky="w", padx=18, pady=6)
        ctk.CTkLabel(frame, text=label, font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(row=0,
                                                                     column=0,
                                                                     sticky="w")
        var = ctk.StringVar(value=str(self.cfg.get(key)))
        self._vars[key] = var
        ctk.CTkEntry(frame, textvariable=var, width=width, height=34).grid(
            row=1, column=0, sticky="w")

    # -- layout -----------------------------------------------------------
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        header.grid_columnconfigure(0, weight=1)
        self._title = SectionTitle(header, text=t("nav_settings"))
        self._title.grid(row=0, column=0, sticky="w")
        AccentButton(header, text="💾 " + t("set_save"), width=150,
                     command=self._save).grid(row=0, column=1, sticky="e")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=4)
        scroll.grid_columnconfigure(0, weight=1)
        r = 0

        r = self._build_account(scroll, r)
        r = self._build_general(scroll, r)
        r = self._build_timing(scroll, r)
        r = self._build_mode_filters(scroll, r)
        r = self._build_network(scroll, r)
        r = self._build_notify(scroll, r)
        r = self._build_ai(scroll, r)
        r = self._build_io(scroll, r)

    # -- account ----------------------------------------------------------
    def _build_account(self, parent, row: int) -> int:
        card = self._section(parent, "🔐 " + t("set_account"))
        card.grid(row=row, column=0, sticky="ew", pady=8)

        acc = self.app.repo.active_account()
        c1, self.e_login = labeled_entry(card, t("set_login"),
                                         placeholder="email / username")
        c1.grid(row=1, column=0, sticky="ew", padx=18, pady=6)
        c2, self.e_password = labeled_entry(card, t("set_password"), show="•")
        c2.grid(row=1, column=1, sticky="ew", padx=18, pady=6)
        c3, self.e_gk = labeled_entry(card, t("set_golden_key"),
                                      placeholder="golden_key cookie")
        c3.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=6)

        if acc:
            self.e_login.insert(0, acc.login)
            if acc.get_password():
                self.e_password.insert(0, acc.get_password())
            if acc.get_golden_key():
                self.e_gk.insert(0, acc.get_golden_key())

        row_btn = ctk.CTkFrame(card, fg_color="transparent")
        row_btn.grid(row=3, column=0, columnspan=2, sticky="w", padx=18,
                     pady=(6, 14))
        AccentButton(row_btn, text=t("set_test_login"), width=170,
                     command=self._test_login).grid(row=0, column=0,
                                                     padx=(0, 8))
        return row + 1

    def _persist_account(self) -> Account:
        acc = self.app.repo.active_account()
        if acc is None:
            acc = Account(label="FunPay", login=self.e_login.get().strip())
            self.app.repo.upsert_account(acc)
            self.cfg.set("active_account_id", acc.id)
        acc.login = self.e_login.get().strip()
        acc.use_golden_key = bool(self.e_gk.get().strip())
        pwd = self.e_password.get().strip()
        gk = self.e_gk.get().strip()
        if pwd:
            acc.set_password(pwd)
        if gk:
            acc.set_golden_key(gk)
        self.app.repo.upsert_account(acc)
        return acc

    def _test_login(self) -> None:
        acc = self._persist_account()
        toast(self, "…", "info")

        def worker() -> None:
            from ..browser import create_client

            client = create_client(acc)
            ok = False
            try:
                ok = client.start()
            finally:
                try:
                    client.stop()
                except Exception:
                    pass

            def done() -> None:
                if ok:
                    message_box(t("success"), "Login OK ✅", icon="check")
                else:
                    message_box(t("warning"),
                                "Не удалось войти. Проверьте golden_key / "
                                "данные. (В demo-режиме вход всегда успешен.)",
                                icon="warning")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # -- general ----------------------------------------------------------
    def _build_general(self, parent, row: int) -> int:
        card = self._section(parent, "⚙️ " + t("set_general"))
        card.grid(row=row, column=0, sticky="ew", pady=8)

        lang_frame = ctk.CTkFrame(card, fg_color="transparent")
        lang_frame.grid(row=1, column=0, sticky="w", padx=18, pady=6)
        ctk.CTkLabel(lang_frame, text=t("set_language"),
                     font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(row=0,
                                                                     column=0,
                                                                     sticky="w")
        self.lang_var = ctk.StringVar(value=self.cfg.get("language", "ru"))
        ctk.CTkOptionMenu(lang_frame, values=["ru", "en"],
                          variable=self.lang_var, width=120,
                          command=self._on_language).grid(row=1, column=0,
                                                          sticky="w")

        theme_frame = ctk.CTkFrame(card, fg_color="transparent")
        theme_frame.grid(row=1, column=1, sticky="w", padx=18, pady=6)
        ctk.CTkLabel(theme_frame, text=t("set_theme"), font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(row=0,
                                                                     column=0,
                                                                     sticky="w")
        self.appearance_var = ctk.StringVar(value=self.cfg.get("theme", "dark"))
        ctk.CTkOptionMenu(theme_frame, values=["dark", "light", "system"],
                          variable=self.appearance_var, width=120,
                          command=self._on_appearance).grid(row=1, column=0,
                                                            sticky="w")
        self.color_var = ctk.StringVar(
            value=self.cfg.get("color_theme", theme.DEFAULT_PALETTE))
        ctk.CTkOptionMenu(theme_frame, values=theme.available_palettes(),
                          variable=self.color_var, width=140,
                          command=self._on_color).grid(row=1, column=1,
                                                       sticky="w", padx=8)

        self._switch(card, "close_to_tray", t("set_tray_close"), 2)
        self._switch(card, "start_minimized", "Start minimized", 3)
        self._switch(card, "autostart_windows", t("set_autostart"), 4)
        ctk.CTkFrame(card, fg_color="transparent", height=8).grid(row=5,
                                                                  column=0)
        return row + 1

    def _on_language(self, value: str) -> None:
        self.cfg.set("language", value)
        get_i18n().set_language(value)

    def _on_appearance(self, value: str) -> None:
        self.cfg.set("theme", value)
        theme.apply_appearance(value)

    def _on_color(self, value: str) -> None:
        self.cfg.set("color_theme", value)
        theme.set_palette(value)
        message_box(t("success"),
                    "Тема применится полностью после перезапуска. / "
                    "Restart to fully apply the accent theme.", icon="info")

    # -- timing -----------------------------------------------------------
    def _build_timing(self, parent, row: int) -> int:
        card = self._section(parent, "⏳ " + t("set_timing"))
        card.grid(row=row, column=0, sticky="ew", pady=8)
        self._entry(card, "poll_min_seconds", t("set_poll_min"), 1, 0)
        self._entry(card, "poll_max_seconds", t("set_poll_max"), 1, 1)
        self._entry(card, "reply_delay_min", t("set_reply_min"), 2, 0)
        self._entry(card, "reply_delay_max", t("set_reply_max"), 2, 1)
        self._switch(card, "typing_simulation", "Typing simulation", 3)
        self._switch(card, "human_jitter", "Human jitter (anti-ban)", 4)
        ctk.CTkFrame(card, fg_color="transparent", height=8).grid(row=5,
                                                                  column=0)
        return row + 1

    # -- mode + filters ---------------------------------------------------
    def _build_mode_filters(self, parent, row: int) -> int:
        card = self._section(parent, "🎯 " + t("set_filters"))
        card.grid(row=row, column=0, sticky="ew", pady=8)

        mode_frame = ctk.CTkFrame(card, fg_color="transparent")
        mode_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=18,
                        pady=6)
        ctk.CTkLabel(mode_frame, text="Work mode", font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(row=0,
                                                                     column=0,
                                                                     sticky="w")
        self.mode_var = ctk.StringVar(value=self.cfg.get("work_mode",
                                                         "all_chats"))
        ctk.CTkOptionMenu(mode_frame,
                          values=["new_dialogs", "all_chats", "specific_games"],
                          variable=self.mode_var, width=200).grid(row=1,
                                                                  column=0,
                                                                  sticky="w")
        self._switch(card, "auto_status_online", "Auto status: Online", 2)

        ctk.CTkLabel(card, text="Whitelist (comma-separated)",
                     font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(
            row=3, column=0, sticky="w", padx=18)
        self.tb_white = ctk.CTkTextbox(card, height=52, corner_radius=8)
        self.tb_white.insert("1.0", ", ".join(self.cfg.get("whitelist", [])))
        self.tb_white.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(card, text="Blacklist (comma-separated)",
                     font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(
            row=3, column=1, sticky="w", padx=18)
        self.tb_black = ctk.CTkTextbox(card, height=52, corner_radius=8)
        self.tb_black.insert("1.0", ", ".join(self.cfg.get("blacklist", [])))
        self.tb_black.grid(row=4, column=1, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(card, text="Specific games (comma-separated)",
                     font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(
            row=5, column=0, sticky="w", padx=18)
        self.tb_games = ctk.CTkTextbox(card, height=48, corner_radius=8)
        self.tb_games.insert("1.0", ", ".join(self.cfg.get("specific_games",
                                                           [])))
        self.tb_games.grid(row=6, column=0, columnspan=2, sticky="ew", padx=18,
                          pady=(0, 14))
        return row + 1

    # -- network ----------------------------------------------------------
    def _build_network(self, parent, row: int) -> int:
        card = self._section(parent, "🌐 " + t("set_network"))
        card.grid(row=row, column=0, sticky="ew", pady=8)
        self._switch(card, "headless", t("set_headless"), 1)
        self._switch(card, "proxy_enabled", t("set_proxy_enable"), 2)

        pf = ctk.CTkFrame(card, fg_color="transparent")
        pf.grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=6)
        self.proxy_type = ctk.StringVar(value=self.cfg.get("proxy_type",
                                                          "http"))
        ctk.CTkOptionMenu(pf, values=["http", "socks5"],
                          variable=self.proxy_type, width=100).grid(row=0,
                                                                    column=0,
                                                                    padx=(0, 8))
        self.proxy_host = ctk.CTkEntry(pf, placeholder_text="host", width=200)
        self.proxy_host.insert(0, self.cfg.get("proxy_host", ""))
        self.proxy_host.grid(row=0, column=1, padx=(0, 8))
        self.proxy_port = ctk.CTkEntry(pf, placeholder_text="port", width=90)
        self.proxy_port.insert(0, str(self.cfg.get("proxy_port", 0) or ""))
        self.proxy_port.grid(row=0, column=2, padx=(0, 8))
        self.proxy_user = ctk.CTkEntry(pf, placeholder_text="user", width=140)
        self.proxy_user.insert(0, self.cfg.get("proxy_user", ""))
        self.proxy_user.grid(row=0, column=3, padx=(0, 8))
        self.proxy_pass = ctk.CTkEntry(pf, placeholder_text="password",
                                       show="•", width=140)
        self.proxy_pass.grid(row=0, column=4)
        ctk.CTkFrame(card, fg_color="transparent", height=8).grid(row=4,
                                                                  column=0)
        return row + 1

    # -- notifications ----------------------------------------------------
    def _build_notify(self, parent, row: int) -> int:
        card = self._section(parent, "🔔 " + t("set_notify"))
        card.grid(row=row, column=0, sticky="ew", pady=8)
        self._switch(card, "notifications_enabled", "Desktop notifications", 1)
        self._switch(card, "sound_enabled", "Sound alerts", 2)
        self._entry(card, "sound_file", "Sound file", 3, 0, width=200)
        ctk.CTkFrame(card, fg_color="transparent", height=8).grid(row=4,
                                                                  column=0)
        return row + 1

    # -- AI ---------------------------------------------------------------
    def _build_ai(self, parent, row: int) -> int:
        card = self._section(parent, "🤖 " + t("set_ai"))
        card.grid(row=row, column=0, sticky="ew", pady=8)

        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=6)
        self.ai_backend = ctk.StringVar(value=self.cfg.get("ai_backend",
                                                          "none"))
        ctk.CTkOptionMenu(bf, values=["none", "ollama", "lmstudio"],
                          variable=self.ai_backend, width=140).grid(row=0,
                                                                    column=0,
                                                                    padx=(0, 8))
        self.ai_url = ctk.CTkEntry(bf, placeholder_text="base url", width=240)
        self.ai_url.insert(0, self.cfg.get("ai_base_url", ""))
        self.ai_url.grid(row=0, column=1, padx=(0, 8))
        self.ai_model = ctk.CTkEntry(bf, placeholder_text="model", width=160)
        self.ai_model.insert(0, self.cfg.get("ai_model", ""))
        self.ai_model.grid(row=0, column=2, padx=(0, 8))
        GhostButton(bf, text="Ping", width=80, command=self._ping_ai).grid(
            row=0, column=3)

        ctk.CTkLabel(card, text="System prompt", font=theme.font(12),
                     text_color=theme.palette()["text_muted"]).grid(
            row=2, column=0, sticky="w", padx=18)
        self.ai_prompt = ctk.CTkTextbox(card, height=60, corner_radius=8)
        self.ai_prompt.insert("1.0", self.cfg.get("ai_system_prompt", ""))
        self.ai_prompt.grid(row=3, column=0, columnspan=2, sticky="ew",
                            padx=18, pady=(0, 8))
        self._switch(card, "ai_fallback_only",
                     "Use AI only when no rule matches", 4)
        ctk.CTkFrame(card, fg_color="transparent", height=8).grid(row=5,
                                                                  column=0)
        return row + 1

    def _ping_ai(self) -> None:
        self._apply_ai_to_config()
        ok = AIClient().ping()
        message_box(t("success") if ok else t("warning"),
                    "AI backend reachable ✅" if ok else "AI backend "
                    "unreachable.", icon="check" if ok else "warning")

    def _apply_ai_to_config(self) -> None:
        self.cfg.update({
            "ai_backend": self.ai_backend.get(),
            "ai_base_url": self.ai_url.get().strip(),
            "ai_model": self.ai_model.get().strip(),
            "ai_system_prompt": self.ai_prompt.get("1.0", "end").strip(),
        })

    # -- import / export --------------------------------------------------
    def _build_io(self, parent, row: int) -> int:
        card = self._section(parent, "📦 Import / Export")
        card.grid(row=row, column=0, sticky="ew", pady=8)
        rowf = ctk.CTkFrame(card, fg_color="transparent")
        rowf.grid(row=1, column=0, columnspan=2, sticky="w", padx=18,
                  pady=(6, 16))
        GhostButton(rowf, text="⬇ " + t("set_export"), width=180,
                    command=self._export).grid(row=0, column=0, padx=(0, 8))
        GhostButton(rowf, text="⬆ " + t("set_import"), width=180,
                    command=self._import).grid(row=0, column=1)
        return row + 1

    def _export(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")],
                                            initialfile="fpar_backup.json")
        if path:
            try:
                settings_io.export_bundle(path)
                toast(self, t("success"), "success")
            except Exception as exc:
                message_box(t("error"), str(exc), icon="cancel")

    def _import(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            try:
                settings_io.import_bundle(path)
                toast(self, t("success"), "success")
                self.app.refresh_all_tabs()
            except Exception as exc:
                message_box(t("error"), str(exc), icon="cancel")

    # -- save all ---------------------------------------------------------
    def _save(self) -> None:
        updates: dict = {}
        for key, var in self._vars.items():
            value = var.get()
            if key.endswith("_seconds") or key.startswith(("poll_", "reply_")):
                try:
                    value = int(float(value))
                except (ValueError, TypeError):
                    value = self.cfg.get(key)
            updates[key] = value

        updates["work_mode"] = self.mode_var.get()
        updates["proxy_type"] = self.proxy_type.get()
        updates["proxy_host"] = self.proxy_host.get().strip()
        try:
            updates["proxy_port"] = int(self.proxy_port.get() or 0)
        except ValueError:
            updates["proxy_port"] = 0
        updates["proxy_user"] = self.proxy_user.get().strip()
        if self.proxy_pass.get().strip():
            security.set_secret("proxy:password", self.proxy_pass.get().strip())

        updates["whitelist"] = self._split(self.tb_white.get("1.0", "end"))
        updates["blacklist"] = self._split(self.tb_black.get("1.0", "end"))
        updates["specific_games"] = self._split(self.tb_games.get("1.0", "end"))

        self.cfg.update(updates)
        self._apply_ai_to_config()
        self._persist_account()

        try:
            autostart.enable(bool(self.cfg.get("autostart_windows")))
        except Exception:
            pass

        toast(self, t("set_saved"), "success")
        self.app.refresh_all_tabs()

    @staticmethod
    def _split(text: str) -> list[str]:
        return [item.strip() for item in text.replace("\n", ",").split(",")
                if item.strip()]

    def refresh_texts(self) -> None:
        self._title.configure(text=t("nav_settings"))

    def on_show(self) -> None:
        pass
