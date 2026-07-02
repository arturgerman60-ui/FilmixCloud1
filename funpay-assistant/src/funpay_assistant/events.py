"""Единые типы событий, которыми обмениваются клиент FunPay и движок."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """Новое сообщение в чате с покупателем."""

    chat_id: str
    author: str
    text: str
    is_mine: bool = False


@dataclass
class Order:
    """Новый оплаченный заказ."""

    order_id: str
    buyer: str
    chat_id: str
    lot_title: str
    amount: float = 0.0
    currency: str = "RUB"


@dataclass
class PollResult:
    """Результат одного опроса FunPay: новые сообщения и заказы."""

    messages: list[ChatMessage] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
