"""Generate application icons and a notification sound.

Run once to (re)create the visual/audio assets bundled with the app::

    python scripts/generate_assets.py

Icons are drawn procedurally with Pillow so the repository stays free of opaque
binaries that can't be regenerated. Several tray variants are produced.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "src" / "assets" / "icons"
SOUNDS = ROOT / "src" / "assets" / "sounds"

ACCENT = (59, 130, 246, 255)      # funpay blue
ACCENT_2 = (37, 99, 235, 255)
EMERALD = (16, 185, 129, 255)
VIOLET = (139, 92, 246, 255)
AMBER = (245, 158, 11, 255)


def _rounded(size: int, radius: int, color) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((2, 2, size - 2, size - 2), radius=radius,
                           fill=color)
    return img


def _controller_glyph(draw: ImageDraw.ImageDraw, size: int,
                      color=(255, 255, 255, 255)) -> None:
    """Draw a stylised game-controller 'F' badge."""
    cx = size // 2
    cy = size // 2
    r = size // 4
    # body
    draw.rounded_rectangle((cx - r * 1.6, cy - r * 0.7, cx + r * 1.6,
                            cy + r * 0.9), radius=r // 2, fill=color)
    # d-pad + buttons cut-outs
    hole = (ACCENT[0], ACCENT[1], ACCENT[2], 255)
    draw.ellipse((cx - r * 1.2, cy - r * 0.2, cx - r * 0.6, cy + r * 0.4),
                 fill=hole)
    draw.ellipse((cx + r * 0.6, cy - r * 0.2, cx + r * 1.2, cy + r * 0.4),
                 fill=hole)


def make_icon(color, filename: str, size: int = 256) -> Image.Image:
    img = _rounded(size, size // 5, color)
    draw = ImageDraw.Draw(img)
    # subtle top highlight for a glassy feel
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlight)
    hdraw.rounded_rectangle((2, 2, size - 2, size // 2), radius=size // 5,
                            fill=(255, 255, 255, 40))
    img.alpha_composite(highlight)
    _controller_glyph(draw, size)
    img.save(ICONS / filename)
    return img


def make_tray_variants() -> None:
    for name, color in (("tray", ACCENT), ("tray_green", EMERALD),
                        ("tray_violet", VIOLET), ("tray_amber", AMBER)):
        make_icon(color, f"{name}.png", size=64)


def make_app_icon() -> None:
    base = make_icon(ACCENT, "app.png", size=256)
    # Windows .ico with multiple resolutions.
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(ICONS / "app.ico", sizes=sizes)
    # Additional palette variants for the "themes" feature.
    make_icon(EMERALD, "app_emerald.png", size=256)
    make_icon(VIOLET, "app_violet.png", size=256)
    make_icon(AMBER, "app_amber.png", size=256)


def make_notify_sound() -> None:
    """A short pleasant two-tone 'ding' as a 16-bit PCM WAV."""
    framerate = 44100
    path = SOUNDS / "notify.wav"
    frames = bytearray()
    for freq, dur in ((880.0, 0.09), (1320.0, 0.16)):
        n = int(framerate * dur)
        for i in range(n):
            envelope = math.exp(-3.0 * i / n)
            sample = int(0.5 * envelope * 32767 *
                         math.sin(2 * math.pi * freq * i / framerate))
            frames += struct.pack("<h", sample)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(bytes(frames))


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    SOUNDS.mkdir(parents=True, exist_ok=True)
    make_app_icon()
    make_tray_variants()
    make_notify_sound()
    print(f"Assets written to {ICONS} and {SOUNDS}")


if __name__ == "__main__":
    main()
