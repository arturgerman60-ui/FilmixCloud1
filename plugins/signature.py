"""Example plugin: append a small signature to every outgoing reply.

Drop ``.py`` files defining a subclass of ``Plugin`` into this folder. Set
``enabled = False`` to disable without deleting. This example is disabled by
default so it doesn't alter replies unexpectedly.
"""
from __future__ import annotations

try:
    from src.core.plugins import Plugin
except ModuleNotFoundError:  # when loaded standalone by the plugin manager
    from core.plugins import Plugin  # type: ignore


class SignaturePlugin(Plugin):
    name = "Signature"
    enabled = False

    def on_before_send(self, message, reply):
        return reply + "\n\n— автоответ / auto-reply"
