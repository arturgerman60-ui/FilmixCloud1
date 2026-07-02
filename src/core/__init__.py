"""Core business logic: rule engine, AI, autoresponder, plugins, updates."""

from .rule_engine import RuleEngine, MatchResult
from .engine import AutoResponder, EngineEvent, EngineStatus

__all__ = [
    "RuleEngine",
    "MatchResult",
    "AutoResponder",
    "EngineEvent",
    "EngineStatus",
]
