"""Offline FunPay simulator.

Generates believable incoming messages so the whole application (engine, rules,
UI, stats, notifications) can be exercised without real credentials or network
access. Also used as a safe fallback when Playwright is unavailable.
"""
from __future__ import annotations

import random
import time
from typing import Dict, List

from ..models.message import ChatMessage
from ..utils.helpers import new_id
from ..utils.logger import get_logger
from .base import BaseFunPayClient, ClientState

log = get_logger(__name__)

_SAMPLE_USERS = ["Alex_Pro", "GamerX", "night_owl", "kupi_bystro",
                 "steam_fan", "Marina", "Dmitry777", "pubg_god"]
_SAMPLE_GAMES = ["CS2", "Dota 2", "PUBG", "Genshin Impact", "Valorant",
                 "Brawl Stars", "Steam"]
_SAMPLE_TEXTS = [
    "привет, это ещё в наличии?",
    "сколько стоит?",
    "здравствуйте, можно купить сейчас?",
    "какая цена?",
    "доступно к покупке?",
    "hello, is it available?",
    "how much for this?",
    "добрый день, готов оплатить",
    "а гарантия есть?",
    "можно скидку?",
]


class MockFunPayClient(BaseFunPayClient):
    def __init__(self, account) -> None:
        super().__init__(account)
        self._last_emit = 0.0
        self._outbox: List[ChatMessage] = []
        self._chat_games: Dict[str, str] = {}

    # -- lifecycle --------------------------------------------------------
    def start(self) -> bool:
        self.state = ClientState.STARTING
        time.sleep(0.3)
        self.state = ClientState.LOGGED_IN
        log.info("[DEMO] Mock FunPay session started.")
        return True

    def stop(self) -> None:
        self.state = ClientState.STOPPED
        log.info("[DEMO] Mock FunPay session stopped.")

    def login(self) -> bool:
        self.state = ClientState.LOGGED_IN
        return True

    def is_logged_in(self) -> bool:
        return self.state == ClientState.LOGGED_IN

    # -- messaging --------------------------------------------------------
    def fetch_new_messages(self) -> List[ChatMessage]:
        # Emit a synthetic customer message roughly every 6-14 seconds.
        now = time.time()
        if now - self._last_emit < random.uniform(6, 14):
            return []
        self._last_emit = now

        chat_id = f"chat_{random.randint(1, 5)}"
        game = self._chat_games.setdefault(chat_id, random.choice(_SAMPLE_GAMES))
        msg = ChatMessage(
            chat_id=chat_id,
            author=random.choice(_SAMPLE_USERS),
            text=random.choice(_SAMPLE_TEXTS),
            is_mine=False,
            game=game,
        )
        log.info("[DEMO] Incoming from %s (%s): %s", msg.author, game, msg.text)
        return [msg]

    def send_message(self, chat_id: str, text: str) -> bool:
        self._outbox.append(ChatMessage(chat_id=chat_id, author="me",
                                        text=text, is_mine=True))
        log.info("[DEMO] Sent to %s: %s", chat_id, text)
        return True

    def set_online(self, online: bool) -> None:
        log.debug("[DEMO] Presence set to %s", "online" if online else "offline")
