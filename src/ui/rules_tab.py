"""Auto-reply rules tab: list of rules + create/edit editor dialog."""
from __future__ import annotations

import customtkinter as ctk

from ..models.rule import MatchType, Rule
from ..utils.i18n import t
from . import theme
from .widgets import (AccentButton, Card, GhostButton, SectionTitle,
                      confirm_box, message_box, toast)

_MATCH_LABELS = {
    MatchType.KEYWORD: "match_keyword",
    MatchType.REGEX: "match_regex",
    MatchType.EXACT: "match_exact",
    MatchType.CONTAINS: "match_contains",
    MatchType.ANY: "match_any",
}


class RulesTab(ctk.CTkFrame):
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
        self._title = SectionTitle(header, text=t("rules_title"))
        self._title.grid(row=0, column=0, sticky="w")
        self.btn_add = AccentButton(header, text="➕ " + t("rules_add"),
                                    width=170, command=self.open_editor)
        self.btn_add.grid(row=0, column=1, sticky="e")

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew", padx=4)
        self.list.grid_columnconfigure(0, weight=1)

    # -- list -------------------------------------------------------------
    def reload(self) -> None:
        for child in self.list.winfo_children():
            child.destroy()

        rules = self.app.repo.rules_by_priority()
        if not rules:
            ctk.CTkLabel(self.list, text=t("rules_empty"),
                         font=theme.font(14),
                         text_color=theme.palette()["text_muted"]).grid(
                row=0, column=0, pady=40)
            return

        for i, rule in enumerate(rules):
            self._render_row(i, rule)

    def _render_row(self, index: int, rule: Rule) -> None:
        pal = theme.palette()
        card = Card(self.list)
        card.grid(row=index, column=0, sticky="ew", pady=6, padx=2)
        card.grid_columnconfigure(1, weight=1)

        switch = ctk.CTkSwitch(card, text="", width=44,
                               command=lambda r=rule: self._toggle(r))
        switch.grid(row=0, column=0, rowspan=2, padx=(16, 10), pady=14)
        switch.select() if rule.enabled else switch.deselect()

        ctk.CTkLabel(card, text=rule.name, font=theme.font(15, "bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(12, 0))

        match_label = t(_MATCH_LABELS.get(rule.match_type, "match_keyword"))
        subtitle = f"{match_label}"
        if rule.pattern:
            subtitle += f" · {rule.pattern[:48]}"
        ctk.CTkLabel(card, text=subtitle, font=theme.font(11),
                     text_color=pal["text_muted"], anchor="w").grid(
            row=1, column=1, sticky="w", pady=(0, 12))

        ctk.CTkLabel(card, text=f"⭐ {rule.priority}", font=theme.font(12),
                     text_color=pal["accent"]).grid(row=0, column=2, rowspan=2,
                                                     padx=8)

        GhostButton(card, text="✏️", width=42,
                    command=lambda r=rule: self.open_editor(r)).grid(
            row=0, column=3, rowspan=2, padx=(4, 4), pady=12)
        GhostButton(card, text="🗑", width=42, border_color=pal["danger"],
                    command=lambda r=rule: self._delete(r)).grid(
            row=0, column=4, rowspan=2, padx=(0, 14), pady=12)

    def _toggle(self, rule: Rule) -> None:
        rule.enabled = not rule.enabled
        self.app.repo.upsert_rule(rule)

    def _delete(self, rule: Rule) -> None:
        if confirm_box(t("confirm"), t("confirm_delete")):
            self.app.repo.delete_rule(rule.id)
            self.reload()
            toast(self, t("success"), "success")

    # -- editor -----------------------------------------------------------
    def open_editor(self, rule: Rule | None = None) -> None:
        RuleEditor(self, self.app, rule, on_save=self._on_saved)

    def _on_saved(self, rule: Rule) -> None:
        self.app.repo.upsert_rule(rule)
        self.reload()
        toast(self, t("success"), "success")

    def refresh_texts(self) -> None:
        self._title.configure(text=t("rules_title"))
        self.btn_add.configure(text="➕ " + t("rules_add"))
        self.reload()

    def on_show(self) -> None:
        self.reload()


class RuleEditor(ctk.CTkToplevel):
    def __init__(self, master, app, rule: Rule | None, on_save):
        super().__init__(master)
        self.app = app
        self.on_save = on_save
        self.rule = rule or Rule()
        self.title(t("rules_edit") if rule else t("rules_add"))
        self.geometry("560x620")
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        pad = {"padx": 24, "pady": 6}

        ctk.CTkLabel(self, text=t("rules_name"), anchor="w",
                     font=theme.font(12)).grid(row=0, column=0, sticky="ew",
                                               padx=24, pady=(20, 0))
        self.e_name = ctk.CTkEntry(self, height=36)
        self.e_name.insert(0, self.rule.name)
        self.e_name.grid(row=1, column=0, sticky="ew", **pad)

        ctk.CTkLabel(self, text=t("rules_match_type"), anchor="w",
                     font=theme.font(12)).grid(row=2, column=0, sticky="ew",
                                               padx=24)
        self.match_var = ctk.StringVar(value=self.rule.match_type.value)
        self.e_match = ctk.CTkOptionMenu(
            self, values=[mt.value for mt in MatchType], variable=self.match_var)
        self.e_match.grid(row=3, column=0, sticky="ew", **pad)

        ctk.CTkLabel(self, text=t("rules_pattern"), anchor="w",
                     font=theme.font(12)).grid(row=4, column=0, sticky="ew",
                                               padx=24)
        self.e_pattern = ctk.CTkEntry(self, height=36,
                                      placeholder_text="привет, hello, ...")
        self.e_pattern.insert(0, self.rule.pattern)
        self.e_pattern.grid(row=5, column=0, sticky="ew", **pad)

        ctk.CTkLabel(self, text=t("rules_response"), anchor="w",
                     font=theme.font(12)).grid(row=6, column=0, sticky="ew",
                                               padx=24)
        self.e_response = ctk.CTkTextbox(self, height=120, corner_radius=10)
        self.e_response.insert("1.0", self.rule.response_template)
        self.e_response.grid(row=7, column=0, sticky="ew", **pad)

        hint = ctk.CTkLabel(
            self,
            text="Можно указать имя шаблона или текст. Переменные: "
                 "{username}, {game}, {price}",
            font=theme.font(11),
            text_color=theme.palette()["text_muted"], anchor="w",
            wraplength=500, justify="left")
        hint.grid(row=8, column=0, sticky="ew", padx=24, pady=(0, 6))

        prio_row = ctk.CTkFrame(self, fg_color="transparent")
        prio_row.grid(row=9, column=0, sticky="ew", padx=24, pady=6)
        prio_row.grid_columnconfigure((1, 3), weight=1)
        ctk.CTkLabel(prio_row, text=t("rules_priority"),
                     font=theme.font(12)).grid(row=0, column=0, padx=(0, 8))
        self.e_priority = ctk.CTkEntry(prio_row, width=90)
        self.e_priority.insert(0, str(self.rule.priority))
        self.e_priority.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(prio_row, text="Cooldown (s)",
                     font=theme.font(12)).grid(row=0, column=2, padx=(16, 8))
        self.e_cooldown = ctk.CTkEntry(prio_row, width=90)
        self.e_cooldown.insert(0, str(self.rule.cooldown_seconds))
        self.e_cooldown.grid(row=0, column=3, sticky="w")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=10, column=0, sticky="ew", padx=24, pady=18)
        btns.grid_columnconfigure(0, weight=1)
        GhostButton(btns, text=t("cancel"), width=120,
                    command=self.destroy).grid(row=0, column=0, sticky="e",
                                               padx=(0, 8))
        AccentButton(btns, text=t("save"), width=140,
                     command=self._save).grid(row=0, column=1, sticky="e")

    def _save(self) -> None:
        self.rule.name = self.e_name.get().strip()
        self.rule.match_type = MatchType.from_value(self.match_var.get())
        self.rule.pattern = self.e_pattern.get().strip()
        self.rule.response_template = self.e_response.get("1.0", "end").strip()
        try:
            self.rule.priority = int(self.e_priority.get() or 100)
        except ValueError:
            self.rule.priority = 100
        try:
            self.rule.cooldown_seconds = int(self.e_cooldown.get() or 0)
        except ValueError:
            self.rule.cooldown_seconds = 0

        error = self.rule.validate()
        if error:
            message_box(t("error"), error, icon="cancel")
            return
        self.on_save(self.rule)
        self.destroy()
