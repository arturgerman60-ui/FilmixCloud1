import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from funpay_assistant.config import AppConfig  # noqa: E402
from funpay_assistant.engine import Engine  # noqa: E402
from funpay_assistant.events import ChatMessage, Order, PollResult  # noqa: E402
from funpay_assistant.templates_store import (  # noqa: E402
    DeliveryRule,
    ReplyRule,
    TemplatesData,
)


class FakeClient:
    def __init__(self, results):
        self._results = list(results)
        self.sent = []
        self.raised = 0

    def authenticate(self):
        return True

    def poll(self):
        return self._results.pop(0) if self._results else PollResult()

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return True

    def raise_lots(self):
        self.raised += 1
        return ["Steam"]


def _templates():
    return TemplatesData(
        default_reply="Здравствуйте!",
        reply_rules=[ReplyRule(["цена", "сколько"], "Цена в лоте.")],
        delivery_rules=[
            DeliveryRule(match="key", mode="keys", pool="default"),
            DeliveryRule(match="", mode="template", text="Спасибо, {buyer}! Заказ {order}."),
        ],
        key_pools={"default": ["AAAA-BBBB-CCCC"]},
    )


def test_auto_reply_uses_keyword_rule(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    client = FakeClient([PollResult(messages=[ChatMessage("c1", "user", "сколько стоит?")])])
    engine = Engine(client, AppConfig(), _templates())
    engine.tick()
    assert client.sent == [("c1", "Цена в лоте.")]
    assert engine.stats["replies"] == 1


def test_auto_reply_default_when_no_match(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    client = FakeClient([PollResult(messages=[ChatMessage("c1", "user", "здоровеньки")])])
    engine = Engine(client, AppConfig(), _templates())
    engine.tick()
    assert client.sent[0][1] == "Здравствуйте!"


def test_auto_delivery_pops_key(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    templates = _templates()
    client = FakeClient([PollResult(orders=[
        Order("#1", "igor", "c1", "Steam Key: Game", 100.0, "RUB")
    ])])
    engine = Engine(client, AppConfig(), templates)
    engine.tick()
    assert any("AAAA-BBBB-CCCC" in text for _, text in client.sent)
    assert templates.key_pools["default"] == []  # ключ израсходован
    assert engine.stats["deliveries"] == 1
    assert engine.stats["sales_sum"] == 100.0


def test_auto_delivery_template_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    client = FakeClient([PollResult(orders=[
        Order("#2", "petro", "c2", "Brawl Stars Boost", 200.0, "RUB")
    ])])
    engine = Engine(client, AppConfig(), _templates())
    engine.tick()
    assert client.sent == [("c2", "Спасибо, petro! Заказ #2.")]


def test_out_of_stock_no_send(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    templates = _templates()
    templates.key_pools["default"] = []
    client = FakeClient([PollResult(orders=[
        Order("#3", "igor", "c1", "Steam Key: Game", 100.0, "RUB")
    ])])
    engine = Engine(client, AppConfig(), templates)
    engine.tick()
    assert client.sent == []  # нет ключа — не выдаём мусор


def test_raise_respects_interval(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config = AppConfig(raise_interval_min=60)
    engine = Engine(FakeClient([]), config, _templates())
    engine.maybe_raise(now=1000.0)          # первый раз — поднимаем
    assert engine.client.raised == 1
    engine.maybe_raise(now=1000.0 + 30 * 60)  # 30 мин — рано
    assert engine.client.raised == 1
    engine.maybe_raise(now=1000.0 + 61 * 60)  # больше часа — снова
    assert engine.client.raised == 2


def test_reply_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config = AppConfig(auto_reply=False)
    client = FakeClient([PollResult(messages=[ChatMessage("c1", "user", "цена?")])])
    engine = Engine(client, config, _templates())
    engine.tick()
    assert client.sent == []
