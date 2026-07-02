"""Auto-reply rule model."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from ..utils.helpers import new_id


class MatchType(str, Enum):
    """How a rule's pattern is compared against an incoming message."""

    KEYWORD = "keyword"      # any of the comma-separated keywords present
    CONTAINS = "contains"    # raw substring match
    EXACT = "exact"          # full-string equality (trimmed, case-insensitive)
    REGEX = "regex"          # regular expression search
    ANY = "any"              # matches every message (catch-all)

    @classmethod
    def from_value(cls, value: str) -> "MatchType":
        try:
            return cls(value)
        except ValueError:
            return cls.KEYWORD


@dataclass
class Rule:
    """A single auto-reply rule.

    A message is answered with ``response_template`` (a template name or raw
    text) when the message matches ``pattern`` according to ``match_type`` and
    the rule is enabled. Higher ``priority`` rules are evaluated first.
    """

    name: str = "New rule"
    match_type: MatchType = MatchType.KEYWORD
    pattern: str = ""
    response_template: str = ""     # template name OR inline text
    priority: int = 100
    enabled: bool = True
    case_sensitive: bool = False
    cooldown_seconds: int = 0       # per-chat minimum interval for this rule
    games: List[str] = field(default_factory=list)   # limit to games (optional)
    id: str = field(default_factory=new_id)

    # -- matching ---------------------------------------------------------
    def matches(self, text: str) -> bool:
        if not self.enabled:
            return False
        if self.match_type == MatchType.ANY:
            return True

        haystack = text if self.case_sensitive else text.lower()
        pattern = self.pattern if self.case_sensitive else self.pattern.lower()

        try:
            if self.match_type == MatchType.KEYWORD:
                keywords = [k.strip() for k in pattern.split(",") if k.strip()]
                return any(kw in haystack for kw in keywords)
            if self.match_type == MatchType.CONTAINS:
                return pattern in haystack
            if self.match_type == MatchType.EXACT:
                return haystack.strip() == pattern.strip()
            if self.match_type == MatchType.REGEX:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                return re.search(self.pattern, text, flags) is not None
        except re.error:
            return False
        return False

    # -- serialization ----------------------------------------------------
    def to_dict(self) -> dict:
        data = self.__dict__.copy()
        data["match_type"] = self.match_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        data = dict(data)
        data["match_type"] = MatchType.from_value(data.get("match_type", "keyword"))
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)

    def validate(self) -> Optional[str]:
        """Return an error message if the rule is invalid, else ``None``."""
        if not self.name.strip():
            return "Rule name is required."
        if self.match_type != MatchType.ANY and not self.pattern.strip():
            return "Pattern is required for this match type."
        if self.match_type == MatchType.REGEX:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                return f"Invalid regular expression: {exc}"
        if not self.response_template.strip():
            return "Response is required."
        return None
