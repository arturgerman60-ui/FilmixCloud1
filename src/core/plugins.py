"""Simple plugin system.

A plugin is a ``.py`` file in the plugins directory that defines a subclass of
:class:`Plugin`. Plugins receive lifecycle hooks and can transform outgoing
replies (e.g. append a signature, translate, run custom logic).

Example plugin (plugins/signature.py)::

    from src.core.plugins import Plugin

    class SignaturePlugin(Plugin):
        name = "Signature"
        def on_before_send(self, message, reply):
            return reply + "\\n\\n— sent by FunPay AutoResponder"
"""
from __future__ import annotations

import importlib.util
import inspect
from typing import List, Optional

from ..models.message import ChatMessage
from ..utils.logger import get_logger
from ..utils.paths import plugins_dir

log = get_logger(__name__)


class Plugin:
    """Base class for user plugins. Override the hooks you need."""

    name: str = "Unnamed plugin"
    enabled: bool = True

    def on_load(self) -> None:
        ...

    def on_start(self) -> None:
        ...

    def on_stop(self) -> None:
        ...

    def on_message(self, message: ChatMessage) -> None:
        """Called for every incoming message (observation only)."""

    def on_before_send(self, message: ChatMessage, reply: str) -> Optional[str]:
        """Transform an outgoing reply. Return new text or None to keep it."""
        return None


class PluginManager:
    def __init__(self) -> None:
        self._plugins: List[Plugin] = []

    def load_all(self) -> None:
        self._plugins.clear()
        directory = plugins_dir()
        for file in sorted(directory.glob("*.py")):
            if file.name.startswith("_"):
                continue
            self._load_file(file)
        if self._plugins:
            log.info("Loaded %d plugin(s): %s", len(self._plugins),
                     ", ".join(p.name for p in self._plugins))

    def _load_file(self, file) -> None:
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Plugin) and obj is not Plugin:
                    instance = obj()
                    instance.on_load()
                    self._plugins.append(instance)
        except Exception as exc:
            log.warning("Failed to load plugin %s: %s", file.name, exc)

    # -- dispatch ---------------------------------------------------------
    def dispatch_start(self) -> None:
        self._safe_all("on_start")

    def dispatch_stop(self) -> None:
        self._safe_all("on_stop")

    def dispatch_message(self, message: ChatMessage) -> None:
        for plugin in self._enabled():
            try:
                plugin.on_message(message)
            except Exception as exc:
                log.debug("Plugin %s on_message error: %s", plugin.name, exc)

    def apply_before_send(self, message: ChatMessage, reply: str) -> str:
        for plugin in self._enabled():
            try:
                new = plugin.on_before_send(message, reply)
                if isinstance(new, str) and new:
                    reply = new
            except Exception as exc:
                log.debug("Plugin %s on_before_send error: %s", plugin.name, exc)
        return reply

    def _enabled(self) -> List[Plugin]:
        return [p for p in self._plugins if p.enabled]

    def _safe_all(self, hook: str) -> None:
        for plugin in self._enabled():
            try:
                getattr(plugin, hook)()
            except Exception as exc:
                log.debug("Plugin %s %s error: %s", plugin.name, hook, exc)

    @property
    def plugins(self) -> List[Plugin]:
        return list(self._plugins)
