"""Демо-клиент: имитирует события FunPay без сети и без аккаунта.

Позволяет продукту полноценно работать «из коробки» для демонстрации
покупателю и для тестов. Реальные продажи — через FunPayClient (live).
"""

from __future__ import annotations

import itertools

from .events import ChatMessage, Order, PollResult


class DemoClient:
    def __init__(self) -> None:
        self._sent: list[tuple[str, str]] = []
        self._script = itertools.cycle(self._make_script())
        self._tick = 0

    @staticmethod
    def _make_script() -> list[PollResult]:
        return [
            PollResult(messages=[ChatMessage("chat-1", "buyer_igor", "Привет, товар в наличии?")]),
            PollResult(orders=[Order("#DEMO-1001", "buyer_igor", "chat-1",
                                     "Steam Key: Cyberpunk 2077", 349.0, "RUB")]),
            PollResult(messages=[ChatMessage("chat-2", "pro_gamer", "сколько стоит буст?")]),
            PollResult(orders=[Order("#DEMO-1002", "pro_gamer", "chat-2",
                                     "Brawl Stars Boost 500 кубков", 590.0, "RUB")]),
            PollResult(),  # тихий цикл
        ]

    def authenticate(self) -> bool:
        return True

    def poll(self) -> PollResult:
        self._tick += 1
        return next(self._script)

    def send_message(self, chat_id: str, text: str) -> bool:
        self._sent.append((chat_id, text))
        return True

    def raise_lots(self):
        return ["Steam", "Brawl Stars"]

    @property
    def sent(self) -> list[tuple[str, str]]:
        return self._sent
