"""Repository layer — persistence for rules, templates, accounts, stats.

Bridges the domain models with the :class:`ConfigStore` tables. Provides an
in-memory cache that the UI mutates and asks the repository to persist.
"""
from __future__ import annotations

import threading
from typing import List, Optional

from ..utils.config import get_config
from ..utils.logger import get_logger
from .account import Account
from .rule import MatchType, Rule
from .stats import Statistics
from .template import Template

log = get_logger(__name__)


def _default_templates() -> List[Template]:
    return [
        Template(name="greeting",
                 body="Здравствуйте, {username}! 👋 Спасибо за обращение. "
                      "Готов помочь с покупкой."),
        Template(name="price",
                 body="Цена — {price} ₽. Оплата через FunPay, выдача сразу "
                      "после оплаты."),
        Template(name="delivery",
                 body="{username}, товар по игре {game} выдам в течение "
                      "нескольких минут после оплаты. Спасибо!"),
        Template(name="afk",
                 body="Здравствуйте! Сейчас я ненадолго отошёл, отвечу в "
                      "ближайшее время. Ваш заказ в приоритете 🙌"),
    ]


def _default_rules() -> List[Rule]:
    return [
        Rule(name="Приветствие", match_type=MatchType.KEYWORD,
             pattern="привет, здравствуй, hello, hi, добрый",
             response_template="greeting", priority=200),
        Rule(name="Вопрос о цене", match_type=MatchType.KEYWORD,
             pattern="цена, сколько, стоит, price, how much",
             response_template="price", priority=180),
        Rule(name="Наличие", match_type=MatchType.KEYWORD,
             pattern="в наличии, есть?, доступно, available, stock",
             response_template="Да, в наличии ✅ Можете оформлять заказ.",
             priority=160),
        Rule(name="Catch-all AFK", match_type=MatchType.ANY, pattern="",
             response_template="afk", priority=1, enabled=False),
    ]


class Repository:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cfg = get_config()
        self._rules: List[Rule] = []
        self._templates: List[Template] = []
        self._accounts: List[Account] = []
        self._stats = Statistics()
        self.load()

    # -- load / seed ------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            rule_rows = self._cfg.table_all("rules")
            self._rules = [Rule.from_dict(r) for r in rule_rows]
            tpl_rows = self._cfg.table_all("templates")
            self._templates = [Template.from_dict(t) for t in tpl_rows]
            acc_rows = self._cfg.table_all("accounts")
            self._accounts = [Account.from_dict(a) for a in acc_rows]
            stat_rows = self._cfg.table_all("stats")
            self._stats = Statistics.from_dict(stat_rows[0] if stat_rows else {})

            seeded = False
            if not self._templates:
                self._templates = _default_templates()
                seeded = True
            if not self._rules:
                self._rules = _default_rules()
                seeded = True
            if seeded:
                self.save_rules()
                self.save_templates()
                log.info("Seeded default rules and templates.")

    # -- rules ------------------------------------------------------------
    def rules(self) -> List[Rule]:
        with self._lock:
            return list(self._rules)

    def rules_by_priority(self) -> List[Rule]:
        with self._lock:
            return sorted(self._rules, key=lambda r: r.priority, reverse=True)

    def upsert_rule(self, rule: Rule) -> None:
        with self._lock:
            for idx, existing in enumerate(self._rules):
                if existing.id == rule.id:
                    self._rules[idx] = rule
                    break
            else:
                self._rules.append(rule)
            self.save_rules()

    def delete_rule(self, rule_id: str) -> None:
        with self._lock:
            self._rules = [r for r in self._rules if r.id != rule_id]
            self.save_rules()

    def save_rules(self) -> None:
        self._cfg.table_replace("rules", [r.to_dict() for r in self._rules])

    # -- templates --------------------------------------------------------
    def templates(self) -> List[Template]:
        with self._lock:
            return list(self._templates)

    def template_by_name(self, name: str) -> Optional[Template]:
        with self._lock:
            for tpl in self._templates:
                if tpl.name == name:
                    return tpl
        return None

    def upsert_template(self, template: Template) -> None:
        with self._lock:
            for idx, existing in enumerate(self._templates):
                if existing.id == template.id:
                    self._templates[idx] = template
                    break
            else:
                self._templates.append(template)
            self.save_templates()

    def delete_template(self, template_id: str) -> None:
        with self._lock:
            self._templates = [t for t in self._templates if t.id != template_id]
            self.save_templates()

    def save_templates(self) -> None:
        self._cfg.table_replace("templates", [t.to_dict() for t in self._templates])

    # -- accounts ---------------------------------------------------------
    def accounts(self) -> List[Account]:
        with self._lock:
            return list(self._accounts)

    def account_by_id(self, account_id: str | None) -> Optional[Account]:
        if not account_id:
            return None
        with self._lock:
            for acc in self._accounts:
                if acc.id == account_id:
                    return acc
        return None

    def active_account(self) -> Optional[Account]:
        return self.account_by_id(self._cfg.get("active_account_id"))

    def upsert_account(self, account: Account) -> None:
        with self._lock:
            for idx, existing in enumerate(self._accounts):
                if existing.id == account.id:
                    self._accounts[idx] = account
                    break
            else:
                self._accounts.append(account)
            self.save_accounts()

    def delete_account(self, account_id: str) -> None:
        with self._lock:
            acc = self.account_by_id(account_id)
            if acc:
                acc.forget_secrets()
            self._accounts = [a for a in self._accounts if a.id != account_id]
            self.save_accounts()

    def save_accounts(self) -> None:
        self._cfg.table_replace("accounts", [a.to_dict() for a in self._accounts])

    # -- stats ------------------------------------------------------------
    @property
    def stats(self) -> Statistics:
        return self._stats

    def save_stats(self) -> None:
        with self._lock:
            self._cfg.table_replace("stats", [self._stats.to_dict()])

    def reset_stats(self) -> None:
        with self._lock:
            self._stats = Statistics()
            self.save_stats()


_instance: Repository | None = None
_instance_lock = threading.Lock()


def get_repository() -> Repository:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = Repository()
    return _instance
