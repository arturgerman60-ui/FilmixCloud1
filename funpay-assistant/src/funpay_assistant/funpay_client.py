"""Живой клиент FunPay через golden_key (cookie сессии).

ВАЖНО про надёжность:
FunPay не имеет официального публичного API. Этот клиент общается с сайтом
по неофициальным эндпоинтам (как это делают открытые боты Cardinal/Vertex).
Разметка сайта иногда меняется, поэтому клиент написан устойчиво: любые сбои
парсинга не роняют программу, а логируются. Для демонстрации и тестов
используйте демо-режим (DemoClient).

Как получить golden_key:
1. Войдите на funpay.com в браузере.
2. F12 → Application/Storage → Cookies → funpay.com → значение `golden_key`.
3. Вставьте его в настройках программы.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import requests

from .events import ChatMessage, Order, PollResult

BASE_URL = "https://funpay.com"


class FunPayClient:
    def __init__(self, golden_key: str, user_agent: str, log: Callable[[str], None] | None = None) -> None:
        self.golden_key = golden_key
        self.log = log or (lambda msg: None)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.session.cookies.set("golden_key", golden_key, domain="funpay.com")
        self.csrf_token: str | None = None
        self.user_id: str | None = None
        self._seen_orders: set[str] = set()
        self._seen_messages: set[str] = set()
        self._lots: list[tuple[str, str]] = []  # (game_id, node_id)

    # ---- авторизация ----
    def authenticate(self) -> bool:
        try:
            response = self.session.get(BASE_URL + "/", timeout=20)
            response.raise_for_status()
            html = response.text
            # app-data содержит userId и csrf-token в JSON-атрибуте body.
            data_match = re.search(r'data-app-data="([^"]+)"', html)
            if data_match:
                import html as html_mod
                import json
                payload = json.loads(html_mod.unescape(data_match.group(1)))
                self.csrf_token = payload.get("csrf-token")
                self.user_id = str(payload.get("userId") or "")
            if not self.user_id:
                self.log("Не удалось определить userId — проверьте golden_key.")
                return False
            self._discover_lots(html)
            self.log(f"Авторизация успешна, userId={self.user_id}")
            return True
        except Exception as exc:  # noqa: BLE001
            self.log(f"Ошибка авторизации: {exc}")
            return False

    def _discover_lots(self, profile_html: str) -> None:
        """Находит игры/категории продавца для авто-поднятия."""
        try:
            profile = self.session.get(f"{BASE_URL}/users/{self.user_id}/", timeout=20).text
            pairs = set(re.findall(r'data-game="(\d+)"[^>]*data-node="(\d+)"', profile))
            pairs |= set(re.findall(r'data-node="(\d+)"[^>]*data-game="(\d+)"', profile))
            # нормализуем в (game_id, node_id)
            self._lots = []
            for a, b in pairs:
                self._lots.append((a, b))
            self.log(f"Найдено категорий для поднятия: {len(self._lots)}")
        except Exception as exc:  # noqa: BLE001
            self.log(f"Не удалось получить список лотов: {exc}")

    # ---- опрос событий ----
    def poll(self) -> PollResult:
        result = PollResult()
        result.orders = self._poll_orders()
        result.messages = self._poll_messages()
        return result

    def _poll_orders(self) -> list[Order]:
        orders: list[Order] = []
        try:
            html = self.session.get(f"{BASE_URL}/orders/trade", timeout=20).text
            # Каждая строка заказа содержит id вида #ABCDEFGH и статус «Оплачен».
            for block in re.findall(r'href="[^"]*/orders/([A-Z0-9]+)/"[\s\S]{0,400}?', html)[:20]:
                order_id = f"#{block}"
                if order_id in self._seen_orders:
                    continue
                self._seen_orders.add(order_id)
                orders.append(Order(order_id=order_id, buyer="покупатель",
                                    chat_id=block, lot_title="Заказ FunPay"))
        except Exception as exc:  # noqa: BLE001
            self.log(f"Ошибка опроса заказов: {exc}")
        return orders

    def _poll_messages(self) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        try:
            html = self.session.get(f"{BASE_URL}/chat/", timeout=20).text
            for chat_id, preview in re.findall(
                r'data-id="(\d+)"[\s\S]{0,300}?contact-item-message">([^<]+)<', html
            )[:20]:
                key = f"{chat_id}:{preview.strip()[:40]}"
                if key in self._seen_messages:
                    continue
                self._seen_messages.add(key)
                messages.append(ChatMessage(chat_id=chat_id, author=f"chat {chat_id}",
                                            text=preview.strip()))
        except Exception as exc:  # noqa: BLE001
            self.log(f"Ошибка опроса чатов: {exc}")
        return messages

    # ---- отправка сообщения ----
    def send_message(self, chat_id: str, text: str) -> bool:
        if not self.csrf_token:
            return False
        try:
            payload = {
                "request": '{"action":"chat_message","data":{"node":"%s","last_message":-1,'
                           '"content":%s}}' % (chat_id, _json_str(text)),
                "csrf_token": self.csrf_token,
            }
            response = self.session.post(f"{BASE_URL}/runner/", data=payload, timeout=20,
                                         headers={"X-Requested-With": "XMLHttpRequest"})
            return response.status_code == 200
        except Exception as exc:  # noqa: BLE001
            self.log(f"Ошибка отправки сообщения: {exc}")
            return False

    # ---- поднятие лотов ----
    def raise_lots(self):
        if not self._lots:
            return []
        raised = []
        for game_id, node_id in self._lots:
            try:
                response = self.session.post(
                    f"{BASE_URL}/lots/raise",
                    data={"game_id": game_id, "node_id": node_id},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    timeout=20,
                )
                if response.status_code == 200:
                    raised.append(node_id)
            except Exception as exc:  # noqa: BLE001
                self.log(f"Ошибка поднятия лота {node_id}: {exc}")
        return raised


def _json_str(text: str) -> str:
    import json
    return json.dumps(text, ensure_ascii=False)
