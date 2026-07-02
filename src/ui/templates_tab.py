"""Message templates tab: list + editor with variables and AI generation."""
from __future__ import annotations

import threading

import customtkinter as ctk

from ..core.ai_client import AIClient
from ..models.template import Template
from ..utils.i18n import t
from . import theme
from .widgets import (AccentButton, Card, GhostButton, SectionTitle,
                      confirm_box, message_box, toast)


class TemplatesTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()
        self.reload()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 12))
        header.grid_columnconfigure(0, weight=1)
        self._title = SectionTitle(header, text=t("tpl_title"))
        self._title.grid(row=0, column=0, sticky="w")
        self.btn_add = AccentButton(header, text="➕ " + t("tpl_add"),
                                    width=170, command=self.open_editor)
        self.btn_add.grid(row=0, column=1, sticky="e")

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew", padx=4)
        self.list.grid_columnconfigure(0, weight=1)

    def reload(self) -> None:
        for child in self.list.winfo_children():
            child.destroy()
        templates = self.app.repo.templates()
        if not templates:
            ctk.CTkLabel(self.list, text=t("tpl_empty"), font=theme.font(14),
                         text_color=theme.palette()["text_muted"]).grid(
                row=0, column=0, pady=40)
            return
        for i, tpl in enumerate(templates):
            self._render_row(i, tpl)

    def _render_row(self, index: int, tpl: Template) -> None:
        pal = theme.palette()
        card = Card(self.list)
        card.grid(row=index, column=0, sticky="ew", pady=6, padx=2)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=f"📝  {tpl.name}", font=theme.font(15, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="w",
                                      padx=16, pady=(12, 0))
        preview = tpl.body[:110] + ("…" if len(tpl.body) > 110 else "")
        ctk.CTkLabel(card, text=preview, font=theme.font(11),
                     text_color=pal["text_muted"], anchor="w",
                     justify="left", wraplength=520).grid(
            row=1, column=0, sticky="w", padx=16, pady=(2, 12))

        variables = tpl.variables()
        if variables:
            ctk.CTkLabel(card, text="{ " + ", ".join(variables) + " }",
                         font=theme.font(10), text_color=pal["accent"],
                         anchor="w").grid(row=2, column=0, sticky="w",
                                          padx=16, pady=(0, 12))

        GhostButton(card, text="✏️", width=42,
                    command=lambda tp=tpl: self.open_editor(tp)).grid(
            row=0, column=1, rowspan=3, padx=4, pady=12)
        GhostButton(card, text="🗑", width=42, border_color=pal["danger"],
                    command=lambda tp=tpl: self._delete(tp)).grid(
            row=0, column=2, rowspan=3, padx=(0, 14), pady=12)

    def _delete(self, tpl: Template) -> None:
        if confirm_box(t("confirm"), t("confirm_delete")):
            self.app.repo.delete_template(tpl.id)
            self.reload()
            toast(self, t("success"), "success")

    def open_editor(self, tpl: Template | None = None) -> None:
        TemplateEditor(self, self.app, tpl, on_save=self._on_saved)

    def _on_saved(self, tpl: Template) -> None:
        self.app.repo.upsert_template(tpl)
        self.reload()
        toast(self, t("success"), "success")

    def refresh_texts(self) -> None:
        self._title.configure(text=t("tpl_title"))
        self.btn_add.configure(text="➕ " + t("tpl_add"))
        self.reload()

    def on_show(self) -> None:
        self.reload()


class TemplateEditor(ctk.CTkToplevel):
    def __init__(self, master, app, tpl: Template | None, on_save):
        super().__init__(master)
        self.app = app
        self.on_save = on_save
        self.tpl = tpl or Template()
        self.title(t("tpl_add"))
        self.geometry("560x520")
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text=t("tpl_name"), anchor="w",
                     font=theme.font(12)).grid(row=0, column=0, sticky="ew",
                                               padx=24, pady=(20, 0))
        self.e_name = ctk.CTkEntry(self, height=36)
        self.e_name.insert(0, self.tpl.name)
        self.e_name.grid(row=1, column=0, sticky="ew", padx=24, pady=6)

        ctk.CTkLabel(self, text=t("tpl_body"), anchor="w",
                     font=theme.font(12)).grid(row=2, column=0, sticky="ew",
                                               padx=24)
        self.e_body = ctk.CTkTextbox(self, corner_radius=10)
        self.e_body.insert("1.0", self.tpl.body)
        self.e_body.grid(row=3, column=0, sticky="nsew", padx=24, pady=6)

        ai_row = ctk.CTkFrame(self, fg_color="transparent")
        ai_row.grid(row=4, column=0, sticky="ew", padx=24, pady=6)
        ai_row.grid_columnconfigure(0, weight=1)
        self.e_ai = ctk.CTkEntry(ai_row,
                                 placeholder_text="Опишите задачу для ИИ…")
        self.e_ai.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_ai = GhostButton(ai_row, text="🤖 " + t("tpl_generate_ai"),
                                  width=190, command=self._generate_ai)
        self.btn_ai.grid(row=0, column=1)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=5, column=0, sticky="ew", padx=24, pady=18)
        btns.grid_columnconfigure(0, weight=1)
        GhostButton(btns, text=t("cancel"), width=120,
                    command=self.destroy).grid(row=0, column=0, sticky="e",
                                               padx=(0, 8))
        AccentButton(btns, text=t("save"), width=140,
                     command=self._save).grid(row=0, column=1, sticky="e")

    def _generate_ai(self) -> None:
        brief = self.e_ai.get().strip()
        if not brief:
            return
        self.btn_ai.configure(state="disabled", text="…")

        def worker() -> None:
            ai = AIClient()
            result = ai.generate_template(brief) if ai.enabled else None

            def done() -> None:
                self.btn_ai.configure(state="normal",
                                      text="🤖 " + t("tpl_generate_ai"))
                if result:
                    self.e_body.delete("1.0", "end")
                    self.e_body.insert("1.0", result)
                else:
                    message_box(t("warning"),
                                "ИИ недоступен. Проверьте настройки (Ollama / "
                                "LM Studio).", icon="warning")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _save(self) -> None:
        self.tpl.name = self.e_name.get().strip()
        self.tpl.body = self.e_body.get("1.0", "end").strip()
        if not self.tpl.name or not self.tpl.body:
            message_box(t("error"), "Name and body are required.", icon="cancel")
            return
        self.on_save(self.tpl)
        self.destroy()
