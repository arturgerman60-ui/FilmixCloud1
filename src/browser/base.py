"""Abstract FunPay client interface."""
from __future__ import annotations

import abc
from enum import Enum
from typing import List

from ..models.message import ChatMessage


class ClientState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    LOGGED_IN = "logged_in"
    LOGGED_OUT = "logged_out"
    ERROR = "error"
    STOPPED = "stopped"


class BaseFunPayClient(abc.ABC):
    """Interface implemented by both the real and mock clients.

    Implementations must be safe to call from a single worker thread. The
    engine never touches the browser from more than one thread at a time.
    """

    def __init__(self, account) -> None:
        self.account = account
        self.state: ClientState = ClientState.IDLE

    # -- lifecycle --------------------------------------------------------
    @abc.abstractmethod
    def start(self) -> bool:
        """Launch the browser / session. Returns True on success."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Tear everything down cleanly."""

    @abc.abstractmethod
    def login(self) -> bool:
        """Authenticate using stored credentials/cookies."""

    @abc.abstractmethod
    def is_logged_in(self) -> bool:
        ...

    # -- messaging --------------------------------------------------------
    @abc.abstractmethod
    def fetch_new_messages(self) -> List[ChatMessage]:
        """Return messages that arrived since the previous poll."""

    @abc.abstractmethod
    def send_message(self, chat_id: str, text: str) -> bool:
        """Send ``text`` to a chat. Returns True on success."""

    # -- presence ---------------------------------------------------------
    def set_online(self, online: bool) -> None:  # optional
        """Update online/offline presence. No-op by default."""
        return None
