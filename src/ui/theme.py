"""Theme & palette management.

Defines a small set of premium dark/light palettes with an accent colour used
consistently across custom cards and buttons to achieve the glass/neumorphic
look. Appearance mode (dark/light/system) is handled by CustomTkinter; the
accent palette is applied by widgets that read :func:`palette`.
"""
from __future__ import annotations

from typing import Dict

try:
    import customtkinter as ctk
    _CTK = True
except Exception:  # pragma: no cover - allows import without display/deps
    ctk = None  # type: ignore
    _CTK = False


# name -> palette. Each palette carries the accent + surface colours used by
# the custom widgets (base CTk widgets fall back to their theme colours).
PALETTES: Dict[str, dict] = {
    "funpay-blue": {
        "accent": "#3B82F6", "accent_hover": "#2563EB",
        "surface": ("#F3F4F6", "#1A1D23"), "card": ("#FFFFFF", "#22262E"),
        "card_hover": ("#F0F1F3", "#2A2F38"),
        "text_muted": ("#6B7280", "#9AA4B2"), "success": "#22C55E",
        "danger": "#EF4444", "warning": "#F59E0B",
    },
    "emerald": {
        "accent": "#10B981", "accent_hover": "#059669",
        "surface": ("#F3F4F6", "#101815"), "card": ("#FFFFFF", "#18231E"),
        "card_hover": ("#EFF1F0", "#1F2E27"),
        "text_muted": ("#6B7280", "#8FB3A3"), "success": "#22C55E",
        "danger": "#EF4444", "warning": "#F59E0B",
    },
    "violet": {
        "accent": "#8B5CF6", "accent_hover": "#7C3AED",
        "surface": ("#F4F3F6", "#161320"), "card": ("#FFFFFF", "#201B2E"),
        "card_hover": ("#F0EEF4", "#2A2340"),
        "text_muted": ("#6B7280", "#A99CC0"), "success": "#22C55E",
        "danger": "#EF4444", "warning": "#F59E0B",
    },
    "amber": {
        "accent": "#F59E0B", "accent_hover": "#D97706",
        "surface": ("#F5F4F2", "#1B1710"), "card": ("#FFFFFF", "#26200F"),
        "card_hover": ("#F2F0EC", "#312817"),
        "text_muted": ("#6B7280", "#C0AF8F"), "success": "#22C55E",
        "danger": "#EF4444", "warning": "#F59E0B",
    },
    "rose": {
        "accent": "#F43F5E", "accent_hover": "#E11D48",
        "surface": ("#F6F3F4", "#1D1416"), "card": ("#FFFFFF", "#2A1B1F"),
        "card_hover": ("#F4EEEF", "#361f24"),
        "text_muted": ("#6B7280", "#C09098"), "success": "#22C55E",
        "danger": "#EF4444", "warning": "#F59E0B",
    },
}

DEFAULT_PALETTE = "funpay-blue"
_active_palette = DEFAULT_PALETTE

FONT_FAMILY = "Segoe UI"


def available_palettes() -> list[str]:
    return list(PALETTES.keys())


def palette(name: str | None = None) -> dict:
    return PALETTES.get(name or _active_palette, PALETTES[DEFAULT_PALETTE])


def set_palette(name: str) -> None:
    global _active_palette
    if name in PALETTES:
        _active_palette = name


def apply_appearance(mode: str) -> None:
    """mode: dark | light | system"""
    if not _CTK:
        return
    normalized = {"dark": "Dark", "light": "Light", "system": "System"}.get(
        mode.lower(), "Dark")
    ctk.set_appearance_mode(normalized)


def init_theme(appearance: str = "dark", color_theme: str = DEFAULT_PALETTE) -> None:
    if not _CTK:
        return
    ctk.set_default_color_theme("blue")
    set_palette(color_theme)
    apply_appearance(appearance)


def font(size: int = 13, weight: str = "normal"):
    if not _CTK:
        return None
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
