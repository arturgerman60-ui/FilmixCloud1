"""Cross-platform 'launch at login' helper.

Windows: HKCU\\...\\Run registry value.
Linux:   XDG autostart .desktop entry.
macOS:   LaunchAgents plist.

All operations are best-effort and never raise to the caller.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .logger import get_logger

log = get_logger(__name__)

_APP_NAME = "FunPayAutoResponder"


def _launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = Path(__file__).resolve().parents[2] / "src" / "main.py"
    return f'"{sys.executable}" "{script}"'


def enable(enabled: bool) -> bool:
    """Enable or disable autostart. Returns True on success."""
    try:
        if sys.platform.startswith("win"):
            return _windows(enabled)
        if sys.platform == "darwin":
            return _macos(enabled)
        return _linux(enabled)
    except Exception as exc:  # pragma: no cover
        log.warning("Autostart change failed: %s", exc)
        return False


def _windows(enabled: bool) -> bool:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                        winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ,
                              _launch_command())
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass
    return True


def _linux(enabled: bool) -> bool:
    autostart_dir = Path.home() / ".config" / "autostart"
    desktop = autostart_dir / f"{_APP_NAME}.desktop"
    if enabled:
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name=FunPay AutoResponder\n"
            f"Exec={_launch_command()}\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
    elif desktop.exists():
        desktop.unlink()
    return True


def _macos(enabled: bool) -> bool:
    agents = Path.home() / "Library" / "LaunchAgents"
    plist = agents / f"com.{_APP_NAME.lower()}.plist"
    if enabled:
        agents.mkdir(parents=True, exist_ok=True)
        plist.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>\n'
            f'  <key>Label</key><string>com.{_APP_NAME.lower()}</string>\n'
            '  <key>ProgramArguments</key><array>\n'
            f'    <string>{sys.executable}</string>\n'
            '  </array>\n'
            '  <key>RunAtLoad</key><true/>\n'
            '</dict></plist>\n',
            encoding="utf-8",
        )
    elif plist.exists():
        plist.unlink()
    return True
