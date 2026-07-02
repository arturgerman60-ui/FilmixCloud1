"""Графический интерфейс (Tkinter). Идёт в комплекте с Python — не требует
дополнительных установок у пользователя после сборки в .exe.
"""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk

from .config import AppConfig, load_config, save_config
from .demo_client import DemoClient
from .engine import Engine
from .licensing import machine_id, verify_license
from .templates_store import load_templates, save_templates
from .version import APP_NAME, VERSION

DARK_BG = "#0f1420"
PANEL = "#161c2b"
ACCENT = "#4f7cff"
TEXT = "#e8eefc"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("900x620")
        self.configure(bg=DARK_BG)

        self.config_data: AppConfig = load_config()
        self.templates = load_templates()
        self.engine: Engine | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._build_style()
        self._build_ui()
        self.after(200, self._drain_log)
        self._refresh_license_badge()

    # ---------- стиль ----------
    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=DARK_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT, padding=(16, 8))
        style.map("TNotebook.Tab", background=[("selected", ACCENT)])
        style.configure("TFrame", background=DARK_BG)
        style.configure("TLabel", background=DARK_BG, foreground=TEXT)
        style.configure("TButton", background=ACCENT, foreground="#ffffff", padding=8)
        style.configure("TCheckbutton", background=DARK_BG, foreground=TEXT)

    # ---------- интерфейс ----------
    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=DARK_BG)
        top.pack(fill="x", padx=14, pady=10)
        tk.Label(top, text="⚡ " + APP_NAME, bg=DARK_BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        self.badge = tk.Label(top, text="DEMO", bg="#ffb020", fg="#0f1420",
                              font=("Segoe UI", 10, "bold"), padx=10, pady=3)
        self.badge.pack(side="right")
        self.status_lbl = tk.Label(top, text="Остановлено", bg=DARK_BG, fg="#8a97b1")
        self.status_lbl.pack(side="right", padx=12)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._tab_dashboard(notebook)
        self._tab_settings(notebook)
        self._tab_templates(notebook)
        self._tab_license(notebook)

    def _tab_dashboard(self, nb: ttk.Notebook) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="Панель")
        controls = tk.Frame(frame, bg=DARK_BG)
        controls.pack(fill="x", pady=10)
        self.start_btn = tk.Button(controls, text="▶ Запустить", command=self.start_engine,
                                   bg=ACCENT, fg="#fff", font=("Segoe UI", 11, "bold"),
                                   relief="flat", padx=16, pady=8)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = tk.Button(controls, text="■ Остановить", command=self.stop_engine,
                                  bg="#273044", fg=TEXT, relief="flat", padx=16, pady=8,
                                  state="disabled")
        self.stop_btn.pack(side="left")
        self.stats_lbl = tk.Label(controls, text="Ответов: 0 · Выдач: 0 · Поднятий: 0",
                                  bg=DARK_BG, fg="#8a97b1")
        self.stats_lbl.pack(side="right")

        self.log_text = tk.Text(frame, bg="#0b1120", fg="#c9d6ee", relief="flat",
                                font=("Consolas", 10), height=22)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.insert("end", "Готов к запуску. В демо-режиме события имитируются.\n")
        self.log_text.configure(state="disabled")

    def _tab_settings(self, nb: ttk.Notebook) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="Настройки")

        self.demo_var = tk.BooleanVar(value=self.config_data.demo_mode)
        self.raise_var = tk.BooleanVar(value=self.config_data.auto_raise)
        self.reply_var = tk.BooleanVar(value=self.config_data.auto_reply)
        self.delivery_var = tk.BooleanVar(value=self.config_data.auto_delivery)

        tk.Label(frame, text="golden_key (cookie сессии FunPay):", bg=DARK_BG, fg=TEXT).pack(anchor="w", pady=(12, 2))
        self.gk_entry = tk.Entry(frame, width=80, show="•", bg="#0b1120", fg=TEXT, relief="flat")
        self.gk_entry.pack(fill="x")
        self.gk_entry.insert(0, self.config_data.get_golden_key())

        ttk.Checkbutton(frame, text="Демо-режим (без реального FunPay)", variable=self.demo_var).pack(anchor="w", pady=6)
        ttk.Checkbutton(frame, text="Авто-поднятие лотов", variable=self.raise_var).pack(anchor="w")
        ttk.Checkbutton(frame, text="Авто-ответчик", variable=self.reply_var).pack(anchor="w")
        ttk.Checkbutton(frame, text="Авто-выдача товара", variable=self.delivery_var).pack(anchor="w")

        row = tk.Frame(frame, bg=DARK_BG)
        row.pack(fill="x", pady=8)
        tk.Label(row, text="Интервал поднятия (мин):", bg=DARK_BG, fg=TEXT).pack(side="left")
        self.raise_interval = tk.Entry(row, width=6, bg="#0b1120", fg=TEXT, relief="flat")
        self.raise_interval.pack(side="left", padx=6)
        self.raise_interval.insert(0, str(self.config_data.raise_interval_min))
        tk.Label(row, text="Опрос (сек):", bg=DARK_BG, fg=TEXT).pack(side="left", padx=(16, 0))
        self.poll_interval = tk.Entry(row, width=6, bg="#0b1120", fg=TEXT, relief="flat")
        self.poll_interval.pack(side="left", padx=6)
        self.poll_interval.insert(0, str(self.config_data.poll_interval_sec))

        tk.Button(frame, text="💾 Сохранить настройки", command=self.save_settings,
                  bg=ACCENT, fg="#fff", relief="flat", padx=14, pady=8).pack(anchor="w", pady=12)

    def _tab_templates(self, nb: ttk.Notebook) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="Шаблоны и ключи")

        tk.Label(frame, text="Приветствие по умолчанию:", bg=DARK_BG, fg=TEXT).pack(anchor="w", pady=(10, 2))
        self.default_reply = tk.Text(frame, height=3, bg="#0b1120", fg=TEXT, relief="flat")
        self.default_reply.pack(fill="x")
        self.default_reply.insert("end", self.templates.default_reply)

        tk.Label(frame, text="Склад ключей (пул «default», по одному в строке):",
                 bg=DARK_BG, fg=TEXT).pack(anchor="w", pady=(12, 2))
        self.keys_text = tk.Text(frame, height=10, bg="#0b1120", fg=TEXT, relief="flat")
        self.keys_text.pack(fill="both", expand=True)
        self.keys_text.insert("end", "\n".join(self.templates.key_pools.get("default", [])))

        tk.Button(frame, text="💾 Сохранить шаблоны", command=self.save_templates_ui,
                  bg=ACCENT, fg="#fff", relief="flat", padx=14, pady=8).pack(anchor="w", pady=10)

    def _tab_license(self, nb: ttk.Notebook) -> None:
        frame = ttk.Frame(nb)
        nb.add(frame, text="Лицензия")
        tk.Label(frame, text="Лицензионный ключ:", bg=DARK_BG, fg=TEXT).pack(anchor="w", pady=(12, 2))
        self.license_entry = tk.Text(frame, height=4, bg="#0b1120", fg=TEXT, relief="flat")
        self.license_entry.pack(fill="x")
        self.license_entry.insert("end", self.config_data.license_key)
        tk.Button(frame, text="Активировать", command=self.activate_license,
                  bg=ACCENT, fg="#fff", relief="flat", padx=14, pady=8).pack(anchor="w", pady=10)
        tk.Label(frame, text=f"ID этого компьютера: {machine_id()}",
                 bg=DARK_BG, fg="#8a97b1").pack(anchor="w")
        tk.Label(frame, text="Без лицензии программа работает в демо-режиме "
                             "(только имитация событий).",
                 bg=DARK_BG, fg="#8a97b1", wraplength=760, justify="left").pack(anchor="w", pady=6)

    # ---------- действия ----------
    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def _drain_log(self) -> None:
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        if self.engine:
            s = self.engine.stats
            self.stats_lbl.config(
                text=f"Ответов: {s['replies']} · Выдач: {s['deliveries']} · Поднятий: {s['raises']}"
            )
        self.after(300, self._drain_log)

    def _refresh_license_badge(self) -> None:
        info = verify_license(self.config_data.license_key)
        if info.is_pro:
            self.badge.config(text="PRO", bg="#37d39a")
        else:
            self.badge.config(text="DEMO", bg="#ffb020")

    def save_settings(self) -> None:
        self.config_data.set_golden_key(self.gk_entry.get().strip())
        self.config_data.demo_mode = self.demo_var.get()
        self.config_data.auto_raise = self.raise_var.get()
        self.config_data.auto_reply = self.reply_var.get()
        self.config_data.auto_delivery = self.delivery_var.get()
        try:
            self.config_data.raise_interval_min = max(5, int(self.raise_interval.get()))
            self.config_data.poll_interval_sec = max(3, int(self.poll_interval.get()))
        except ValueError:
            messagebox.showerror(APP_NAME, "Интервалы должны быть числами.")
            return
        save_config(self.config_data)
        messagebox.showinfo(APP_NAME, "Настройки сохранены.")

    def save_templates_ui(self) -> None:
        self.templates.default_reply = self.default_reply.get("1.0", "end").strip()
        keys = [line.strip() for line in self.keys_text.get("1.0", "end").splitlines() if line.strip()]
        self.templates.key_pools["default"] = keys
        save_templates(self.templates)
        messagebox.showinfo(APP_NAME, f"Шаблоны сохранены. Ключей на складе: {len(keys)}")

    def activate_license(self) -> None:
        key = self.license_entry.get("1.0", "end").strip()
        info = verify_license(key)
        if not info.valid:
            messagebox.showerror(APP_NAME, f"Лицензия недействительна: {info.error}")
            return
        self.config_data.license_key = key
        save_config(self.config_data)
        self._refresh_license_badge()
        messagebox.showinfo(APP_NAME, "Лицензия активирована. Спасибо!")

    def _make_client(self):
        if self.config_data.demo_mode or not self.config_data.get_golden_key():
            return DemoClient()
        from .funpay_client import FunPayClient
        return FunPayClient(self.config_data.get_golden_key(),
                            self.config_data.user_agent, log=self.log)

    def start_engine(self) -> None:
        self.templates = load_templates()
        client = self._make_client()
        self.engine = Engine(client, self.config_data, self.templates, log=self.log)
        self.engine.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_lbl.config(text="Работает", fg="#37d39a")

    def stop_engine(self) -> None:
        if self.engine:
            self.engine.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_lbl.config(text="Остановлено", fg="#8a97b1")


def run() -> None:
    App().mainloop()
