"""Шаблоны авто-ответов, правила авто-выдачи и склад ключей."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import get_config_dir


@dataclass
class ReplyRule:
    """Правило авто-ответа: если в сообщении есть одно из keywords → text."""

    keywords: list[str]
    text: str


@dataclass
class DeliveryRule:
    """Правило авто-выдачи для лота, чьё название содержит match.

    mode = "keys"     → выдать один ключ из склада pool (и удалить его);
    mode = "template" → выдать текст text (плейсхолдеры {order}, {buyer}, {lot}).
    """

    match: str
    mode: str = "template"
    pool: str = ""
    text: str = "Спасибо за покупку, {buyer}! Ваш заказ {order} готов."


@dataclass
class TemplatesData:
    default_reply: str = (
        "Здравствуйте! Спасибо за обращение. Отвечу в течение нескольких минут. "
        "Товар выдаётся автоматически сразу после оплаты."
    )
    reply_rules: list[ReplyRule] = field(default_factory=list)
    delivery_rules: list[DeliveryRule] = field(default_factory=list)
    # Склад ключей: имя пула -> список ключей (по одному на строку).
    key_pools: dict[str, list[str]] = field(default_factory=dict)


def _templates_path() -> Path:
    return get_config_dir() / "templates.json"


def default_templates() -> TemplatesData:
    """Стартовые шаблоны, чтобы продукт работал «из коробки»."""
    return TemplatesData(
        reply_rules=[
            ReplyRule(["привет", "здравствуй", "добрый"], "Здравствуйте! Чем могу помочь?"),
            ReplyRule(["гаранти", "обман", "скам"],
                      "Все сделки идут через гаранта FunPay — вы ничем не рискуете."),
            ReplyRule(["сколько", "цена", "стоит"],
                      "Актуальная цена указана в лоте. Могу предложить скидку при заказе от 2 шт."),
        ],
        delivery_rules=[
            DeliveryRule(match="key", mode="keys", pool="default"),
            DeliveryRule(match="", mode="template",
                         text="Спасибо за покупку, {buyer}! Заказ {order} ({lot}) выполнен. "
                              "Отличной игры! Буду благодарен за отзыв ⭐"),
        ],
        key_pools={"default": []},
    )


def load_templates() -> TemplatesData:
    path = _templates_path()
    if not path.exists():
        data = default_templates()
        save_templates(data)
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return TemplatesData(
            default_reply=raw.get("default_reply", ""),
            reply_rules=[ReplyRule(**r) for r in raw.get("reply_rules", [])],
            delivery_rules=[DeliveryRule(**d) for d in raw.get("delivery_rules", [])],
            key_pools={k: list(v) for k, v in raw.get("key_pools", {}).items()},
        )
    except Exception:  # noqa: BLE001
        return default_templates()


def save_templates(data: TemplatesData) -> None:
    payload = {
        "default_reply": data.default_reply,
        "reply_rules": [{"keywords": r.keywords, "text": r.text} for r in data.reply_rules],
        "delivery_rules": [
            {"match": d.match, "mode": d.mode, "pool": d.pool, "text": d.text}
            for d in data.delivery_rules
        ],
        "key_pools": data.key_pools,
    }
    _templates_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
