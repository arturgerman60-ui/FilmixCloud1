"""Rule matching + response rendering."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from ..models.message import ChatMessage
from ..models.repository import Repository
from ..models.rule import Rule
from ..utils.helpers import parse_price
from ..utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class MatchResult:
    rule: Optional[Rule]
    text: str
    price: float = 0.0
    used_ai: bool = False


class RuleEngine:
    """Turns an incoming message into a rendered reply.

    Evaluation order: enabled rules by descending priority. The first matching
    rule wins. The response is treated as a template *name* if it matches a
    stored template, otherwise as inline text; either way ``{variables}`` are
    interpolated.
    """

    def __init__(self, repository: Repository) -> None:
        self.repo = repository

    def _context(self, message: ChatMessage) -> Dict[str, str]:
        return {
            "username": message.author,
            "game": message.game or "",
            "chat_id": message.chat_id,
            "message": message.text,
        }

    def evaluate(self, message: ChatMessage) -> Optional[MatchResult]:
        game_filter = message.game.lower() if message.game else ""
        for rule in self.repo.rules_by_priority():
            if not rule.enabled:
                continue
            if rule.games and game_filter and \
                    game_filter not in [g.lower() for g in rule.games]:
                continue
            if not rule.matches(message.text):
                continue

            text, price = self._render_response(rule, message)
            if not text:
                continue
            log.debug("Rule '%s' matched message from %s.", rule.name,
                      message.author)
            return MatchResult(rule=rule, text=text, price=price)
        return None

    def _render_response(self, rule: Rule, message: ChatMessage) -> tuple[str, float]:
        context = self._context(message)
        template = self.repo.template_by_name(rule.response_template)
        if template:
            rendered = template.render(context)
            price = template.implied_price() or 0.0
            return rendered, price
        # Inline text response; still interpolate simple variables.
        inline = rule.response_template
        for key, value in context.items():
            inline = inline.replace("{" + key + "}", str(value))
        return inline, parse_price(inline) or 0.0
