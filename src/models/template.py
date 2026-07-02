"""Message template model with variable interpolation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict

from ..utils.helpers import new_id, parse_price

_VAR_PATTERN = re.compile(r"\{(\w+)\}")


@dataclass
class Template:
    """Reusable message with ``{variable}`` placeholders.

    Supported built-in variables include ``{username}``, ``{game}``,
    ``{price}`` plus anything supplied at render time.
    """

    name: str = "New template"
    body: str = ""
    id: str = field(default_factory=new_id)

    def variables(self) -> list[str]:
        return sorted(set(_VAR_PATTERN.findall(self.body)))

    def render(self, context: Dict[str, str] | None = None) -> str:
        context = context or {}

        def _sub(match: re.Match) -> str:
            key = match.group(1)
            return str(context.get(key, match.group(0)))

        return _VAR_PATTERN.sub(_sub, self.body)

    def implied_price(self) -> float | None:
        """Best-effort price parsed from the body (for earnings stats)."""
        return parse_price(self.body)

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "Template":
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)
