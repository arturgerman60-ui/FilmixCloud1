"""Statistics tab: totals, per-day bar chart (canvas) and top rules."""
from __future__ import annotations

import customtkinter as ctk

from ..utils.i18n import t
from . import theme
from .widgets import Card, GhostButton, SectionTitle, StatCard, confirm_box, toast


class StatsTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()
        self.reload()

    def _build(self) -> None:
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4,
                    pady=(4, 12))
        header.grid_columnconfigure(0, weight=1)
        self._title = SectionTitle(header, text=t("stats_title"))
        self._title.grid(row=0, column=0, sticky="w")
        self.btn_reset = GhostButton(header, text="↺ " + t("stats_reset"),
                                     width=170,
                                     border_color=theme.palette()["danger"],
                                     command=self._reset)
        self.btn_reset.grid(row=0, column=1, sticky="e")

        pal = theme.palette()
        self.card_replies = StatCard(self, icon="✉️", label=t("dash_replies"),
                                     accent=pal["success"])
        self.card_earned = StatCard(self, icon="💰", label=t("dash_earned"),
                                    accent=pal["warning"])
        self.card_ai = StatCard(self, icon="🤖", label="AI replies",
                                accent=pal["accent"])
        for i, c in enumerate((self.card_replies, self.card_earned,
                               self.card_ai)):
            c.grid(row=1, column=i, sticky="nsew", padx=8, pady=8)

        self.chart_card = Card(self)
        self.chart_card.grid(row=2, column=0, columnspan=2, sticky="nsew",
                             padx=8, pady=8)
        self.chart_card.grid_columnconfigure(0, weight=1)
        self.chart_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.chart_card, text=t("stats_by_day"),
                     font=theme.font(15, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.canvas = ctk.CTkCanvas(self.chart_card, highlightthickness=0,
                                    bg=self._bg_hex())
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.canvas.bind("<Configure>", lambda e: self._draw_chart())

        self.top_card = Card(self)
        self.top_card.grid(row=2, column=2, sticky="nsew", padx=8, pady=8)
        self.top_card.grid_columnconfigure(0, weight=1)
        self.top_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.top_card, text=t("stats_top_rules"),
                     font=theme.font(15, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        self.top_list = ctk.CTkScrollableFrame(self.top_card,
                                               fg_color="transparent")
        self.top_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        self.top_list.grid_columnconfigure(0, weight=1)

    def _bg_hex(self) -> str:
        pal = theme.palette()
        card = pal["card"]
        idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
        return card[idx] if isinstance(card, (list, tuple)) else card

    # -- data -------------------------------------------------------------
    def reload(self) -> None:
        stats = self.app.repo.stats
        self.card_replies.set_value(str(stats.replies_sent))
        self.card_earned.set_value(f"{stats.earned:.0f} ₽")
        self.card_ai.set_value(str(stats.ai_replies))
        self._draw_chart()
        self._render_top_rules()

    def _draw_chart(self) -> None:
        try:
            self.canvas.configure(bg=self._bg_hex())
            self.canvas.delete("all")
            data = self.app.repo.stats.by_day
            if not data:
                return
            items = sorted(data.items())[-14:]
            width = self.canvas.winfo_width() or 400
            height = self.canvas.winfo_height() or 200
            if width < 20 or height < 20:
                return
            max_v = max(v for _, v in items) or 1
            pal = theme.palette()
            n = len(items)
            gap = 10
            bar_w = max((width - gap * (n + 1)) / n, 6)
            for i, (day, value) in enumerate(items):
                x0 = gap + i * (bar_w + gap)
                bar_h = (value / max_v) * (height - 34)
                y0 = height - 22 - bar_h
                x1, y1 = x0 + bar_w, height - 22
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=pal["accent"],
                                             outline="")
                self.canvas.create_text((x0 + x1) / 2, y0 - 8, text=str(value),
                                        fill=pal["text_muted"][1], font=("", 9))
                self.canvas.create_text((x0 + x1) / 2, height - 10,
                                        text=day[5:], fill=pal["text_muted"][1],
                                        font=("", 8))
        except Exception:
            pass

    def _render_top_rules(self) -> None:
        for child in self.top_list.winfo_children():
            child.destroy()
        by_rule = self.app.repo.stats.by_rule
        rules = {r.id: r.name for r in self.app.repo.rules()}
        ranked = sorted(by_rule.items(), key=lambda kv: kv[1], reverse=True)[:12]
        pal = theme.palette()
        if not ranked:
            ctk.CTkLabel(self.top_list, text="—", font=theme.font(12),
                         text_color=pal["text_muted"]).grid(row=0, column=0,
                                                            pady=10)
            return
        for i, (rule_id, count) in enumerate(ranked):
            name = rules.get(rule_id, rule_id)
            ctk.CTkLabel(self.top_list, text=f"{i + 1}. {name}",
                         font=theme.font(12), anchor="w").grid(
                row=i, column=0, sticky="w", padx=8, pady=3)
            ctk.CTkLabel(self.top_list, text=str(count),
                         font=theme.font(12, "bold"),
                         text_color=pal["accent"]).grid(row=i, column=1,
                                                         sticky="e", padx=8)

    def _reset(self) -> None:
        if confirm_box(t("confirm"), t("stats_reset") + "?"):
            self.app.repo.reset_stats()
            self.reload()
            toast(self, t("success"), "success")

    def refresh_texts(self) -> None:
        self._title.configure(text=t("stats_title"))
        self.btn_reset.configure(text="↺ " + t("stats_reset"))

    def on_show(self) -> None:
        self.reload()
