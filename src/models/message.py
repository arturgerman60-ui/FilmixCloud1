"""Chat message value object exchanged between browser layer and engine."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..utils.helpers import now_iso


@dataclass
class ChatMessage:
    chat_id: str
    author: str
    text: str
    is_mine: bool = False          # True if sent by the bot/account owner
    game: str = ""
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)
