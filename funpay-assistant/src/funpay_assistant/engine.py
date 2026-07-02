"""Движок автоматизации: связывает клиента FunPay, шаблоны и правила.

Отделён от GUI и сети, поэтому легко тестируется. Клиент передаётся снаружи
и должен реализовывать методы: authenticate(), poll(), send_message(),
raise_lots(). Так один и тот же движок работает и с живым FunPay, и с демо.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime

from .config import AppConfig, save_config
from .events import ChatMessage, Order
from .templates_store import TemplatesData, save_templates

LogFn = Callable[[str], None]


class Engine:
    def __init__(
        self,
        client,
        config: AppConfig,
        templates: TemplatesData,
        log: LogFn | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.templates = templates
        self._log = log or (lambda msg: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_raise: float | None = None  # None = ещё ни разу не поднимали
        self.stats = {"replies": 0, "deliveries": 0, "raises": 0, "sales_sum": 0.0}

    # ---- логирование ----
    def log(self, message: str) -> None:
        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    # ---- обработка сообщений ----
    def _match_reply(self, text: str) -> str | None:
        lowered = text.lower()
        for rule in self.templates.reply_rules:
            if any(keyword.lower() in lowered for keyword in rule.keywords):
                return rule.text
        return self.templates.default_reply or None

    def handle_message(self, message: ChatMessage) -> None:
        if message.is_mine:
            return
        if not self.config.auto_reply:
            return
        reply = self._match_reply(message.text)
        if reply:
            self.client.send_message(message.chat_id, reply)
            self.stats["replies"] += 1
            self.log(f"Авто-ответ → {message.author}: {reply[:60]}")

    # ---- обработка заказов (авто-выдача) ----
    def _resolve_delivery(self, order: Order) -> str | None:
        for rule in self.templates.delivery_rules:
            if rule.match and rule.match.lower() not in order.lot_title.lower():
                continue
            if rule.mode == "keys":
                pool = self.templates.key_pools.get(rule.pool, [])
                if pool:
                    key = pool.pop(0)
                    save_templates(self.templates)  # фиксируем расход ключа
                    return (f"Спасибо за покупку, {order.buyer}! Ваш ключ для «{order.lot_title}»:\n"
                            f"{key}\n\nПриятной игры! Буду благодарен за отзыв ⭐")
                self.log(f"⚠ Склад ключей «{rule.pool}» пуст — заказ {order.order_id} требует ручной выдачи")
                return None
            return (rule.text
                    .replace("{order}", order.order_id)
                    .replace("{buyer}", order.buyer)
                    .replace("{lot}", order.lot_title))
        return None

    def handle_order(self, order: Order) -> None:
        self.stats["sales_sum"] += order.amount
        self.log(f"💰 Новый заказ {order.order_id}: {order.lot_title} от {order.buyer} "
                 f"({order.amount:.2f} {order.currency})")
        if not self.config.auto_delivery:
            return
        content = self._resolve_delivery(order)
        if content:
            self.client.send_message(order.chat_id, content)
            self.stats["deliveries"] += 1
            self.log(f"📦 Авто-выдача заказа {order.order_id} → {order.buyer}")

    # ---- поднятие лотов ----
    def maybe_raise(self, now: float | None = None) -> None:
        if not self.config.auto_raise:
            return
        now = now if now is not None else time.time()
        interval = self.config.raise_interval_min * 60
        if self._last_raise is not None and now - self._last_raise < interval:
            return
        raised = self.client.raise_lots()
        self._last_raise = now
        if raised:
            self.stats["raises"] += 1
            self.log(f"⬆ Подняты лоты: {', '.join(raised) if isinstance(raised, list) else raised}")

    # ---- один цикл ----
    def tick(self) -> None:
        result = self.client.poll()
        for message in result.messages:
            self.handle_message(message)
        for order in result.orders:
            self.handle_order(order)
        self.maybe_raise()

    # ---- фоновый цикл ----
    def _loop(self) -> None:
        if not self.client.authenticate():
            self.log("❌ Не удалось авторизоваться. Проверьте golden_key или включите демо-режим.")
            return
        self.log("✅ Запущено. Отслеживаю сообщения и заказы…")
        # первое поднятие произойдёт на первом же tick (_last_raise = None)
        self._last_raise = None
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 — не роняем цикл из-за сети
                self.log(f"⚠ Ошибка цикла: {exc}")
            self._stop.wait(self.config.poll_interval_sec)
        self.log("⏹ Остановлено.")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())
