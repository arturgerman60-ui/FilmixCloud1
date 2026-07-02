"""Reusable premium widgets built on CustomTkinter.

Cards use large corner radii + subtle surface colours to evoke a soft
glass/neumorphic feel. Helpers gracefully no-op if optional dependencies
(CTkToolTip, CTkMessagebox) are missing.
"""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from . import theme


def attach_tooltip(widget, text: str) -> None:
    """Attach a hover tooltip if CTkToolTip is available."""
    try:
        from CTkToolTip import CTkToolTip

        CTkToolTip(widget, message=text, delay=0.3)
    except Exception:
        pass


def message_box(title: str, message: str, *, icon: str = "info",
                option_1: str = "OK") -> Optional[str]:
    """Show a themed message box; return the clicked option (or None)."""
    try:
        from CTkMessagebox import CTkMessagebox

        box = CTkMessagebox(title=title, message=message, icon=icon,
                            option_1=option_1)
        return box.get()
    except Exception:
        # Fallback to a plain modal so the app still communicates.
        try:
            import tkinter.messagebox as mb

            mb.showinfo(title, message)
        except Exception:
            print(f"[{title}] {message}")
        return option_1


def confirm_box(title: str, message: str) -> bool:
    try:
        from CTkMessagebox import CTkMessagebox

        box = CTkMessagebox(title=title, message=message, icon="question",
                            option_1="Cancel", option_2="OK")
        return box.get() == "OK"
    except Exception:
        try:
            import tkinter.messagebox as mb

            return bool(mb.askyesno(title, message))
        except Exception:
            return False


class Card(ctk.CTkFrame):
    """Rounded surface card."""

    def __init__(self, master, **kwargs):
        pal = theme.palette()
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("fg_color", pal["card"])
        kwargs.setdefault("border_width", 0)
        super().__init__(master, **kwargs)


class StatCard(ctk.CTkFrame):
    """Dashboard metric card: big value + label + emoji icon."""

    def __init__(self, master, *, icon: str, label: str, value: str = "0",
                 accent: Optional[str] = None, **kwargs):
        pal = theme.palette()
        super().__init__(master, corner_radius=18, fg_color=pal["card"],
                         **kwargs)
        accent = accent or pal["accent"]

        self.grid_columnconfigure(1, weight=1)

        self._icon = ctk.CTkLabel(self, text=icon, font=theme.font(30),
                                  width=54)
        self._icon.grid(row=0, column=0, rowspan=2, padx=(18, 8), pady=16)

        self._value = ctk.CTkLabel(self, text=value, font=theme.font(28, "bold"),
                                   anchor="w")
        self._value.grid(row=0, column=1, sticky="sw", padx=(4, 16), pady=(16, 0))

        self._label = ctk.CTkLabel(self, text=label, font=theme.font(12),
                                   text_color=pal["text_muted"], anchor="w")
        self._label.grid(row=1, column=1, sticky="nw", padx=(4, 16), pady=(0, 16))

        self._accent_bar = ctk.CTkFrame(self, width=6, corner_radius=3,
                                        fg_color=accent)
        self._accent_bar.grid(row=0, column=2, rowspan=2, sticky="ns",
                              padx=(0, 10), pady=14)

    def set_value(self, value: str) -> None:
        self._value.configure(text=value)

    def set_label(self, label: str) -> None:
        self._label.configure(text=label)


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text: str, **kwargs):
        super().__init__(master, text=text, font=theme.font(20, "bold"),
                         anchor="w", **kwargs)


class AccentButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        pal = theme.palette()
        kwargs.setdefault("fg_color", pal["accent"])
        kwargs.setdefault("hover_color", pal["accent_hover"])
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("height", 38)
        kwargs.setdefault("font", theme.font(13, "bold"))
        super().__init__(master, **kwargs)


class GhostButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        pal = theme.palette()
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", pal["card_hover"])
        kwargs.setdefault("corner_radius", 12)
        kwargs.setdefault("height", 36)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", pal["text_muted"])
        super().__init__(master, **kwargs)


class Badge(ctk.CTkLabel):
    def __init__(self, master, text: str, color: str, **kwargs):
        super().__init__(master, text=text, fg_color=color, corner_radius=10,
                         font=theme.font(11, "bold"), text_color="#FFFFFF",
                         padx=10, pady=2, **kwargs)


def labeled_entry(master, label: str, *, show: Optional[str] = None,
                  placeholder: str = "") -> tuple[ctk.CTkFrame, ctk.CTkEntry]:
    """Return a (container, entry) pair with a caption label above the entry."""
    pal = theme.palette()
    container = ctk.CTkFrame(master, fg_color="transparent")
    container.grid_columnconfigure(0, weight=1)
    cap = ctk.CTkLabel(container, text=label, font=theme.font(12),
                       text_color=pal["text_muted"], anchor="w")
    cap.grid(row=0, column=0, sticky="ew", pady=(0, 2))
    entry = ctk.CTkEntry(container, show=show, placeholder_text=placeholder,
                         height=36, corner_radius=10)
    entry.grid(row=1, column=0, sticky="ew")
    return container, entry


def toast(master, text: str, kind: str = "info", duration_ms: int = 2600) -> None:
    """Show a transient toast in the bottom-right of ``master``'s toplevel."""
    pal = theme.palette()
    colors = {"info": pal["accent"], "success": pal["success"],
              "error": pal["danger"], "warning": pal["warning"]}
    try:
        top = master.winfo_toplevel()
        frame = ctk.CTkFrame(top, corner_radius=12, fg_color=colors.get(kind,
                             pal["accent"]))
        label = ctk.CTkLabel(frame, text=text, font=theme.font(13, "bold"),
                             text_color="#FFFFFF")
        label.pack(padx=16, pady=10)
        frame.place(relx=0.98, rely=0.96, anchor="se")
        frame.after(duration_ms, frame.destroy)
    except Exception:
        pass
