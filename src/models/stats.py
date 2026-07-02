"""Aggregated runtime + persisted statistics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict


@dataclass
class Statistics:
    messages_processed: int = 0
    replies_sent: int = 0
    earned: float = 0.0
    ai_replies: int = 0
    errors: int = 0
    # date (YYYY-MM-DD) -> replies count
    by_day: Dict[str, int] = field(default_factory=dict)
    # rule id -> trigger count
    by_rule: Dict[str, int] = field(default_factory=dict)

    def record_processed(self) -> None:
        self.messages_processed += 1

    def record_reply(self, rule_id: str | None = None, price: float = 0.0,
                     ai: bool = False) -> None:
        self.replies_sent += 1
        if ai:
            self.ai_replies += 1
        if price:
            self.earned += price
        today = date.today().isoformat()
        self.by_day[today] = self.by_day.get(today, 0) + 1
        if rule_id:
            self.by_rule[rule_id] = self.by_rule.get(rule_id, 0) + 1

    def record_error(self) -> None:
        self.errors += 1

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "Statistics":
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in (data or {}).items() if k in allowed}
        return cls(**clean)
