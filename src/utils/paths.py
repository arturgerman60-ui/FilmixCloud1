"""Centralised filesystem path management.

Resolves a writable per-user data directory that works both when running
from source and when frozen by PyInstaller. All runtime artefacts (database,
logs, sessions, exported files) live under this directory.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "FunPayAutoResponder"


def _frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def resource_dir() -> Path:
    """Directory that holds bundled read-only resources (assets)."""
    if _frozen():
        # PyInstaller unpacks data files next to the executable / into _MEIPASS.
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base
    return Path(__file__).resolve().parents[1]  # -> src/


def asset_path(*parts: str) -> Path:
    """Absolute path to a bundled asset inside src/assets."""
    return resource_dir().joinpath("assets", *parts)


def _default_data_dir() -> Path:
    """Platform-appropriate writable data directory."""
    override = os.environ.get("FPAR_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / APP_DIR_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME

    # Linux / other
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / APP_DIR_NAME


# When running from a checked-out source tree we prefer the repo's ./data
# folder so the developer can inspect artefacts easily.
def _source_data_dir() -> Path | None:
    if _frozen():
        return None
    repo_data = Path(__file__).resolve().parents[2] / "data"
    return repo_data


def data_dir() -> Path:
    """Resolve and create the active data directory."""
    if os.environ.get("FPAR_DATA_DIR"):
        base = _default_data_dir()
    else:
        base = _source_data_dir() or _default_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base


def sub_dir(name: str) -> Path:
    """Create and return a sub-directory of the data directory."""
    path = data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


# Convenience helpers -------------------------------------------------------

def db_path() -> Path:
    return data_dir() / "storage.json"


def logs_dir() -> Path:
    return sub_dir("logs")


def sessions_dir() -> Path:
    return sub_dir("sessions")


def exports_dir() -> Path:
    return sub_dir("exports")


def plugins_dir() -> Path:
    """Directory scanned for user plugins."""
    if _frozen():
        return sub_dir("plugins")
    repo_plugins = Path(__file__).resolve().parents[2] / "plugins"
    repo_plugins.mkdir(parents=True, exist_ok=True)
    return repo_plugins
