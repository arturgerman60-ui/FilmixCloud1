"""AutoResponder engine — the heart of the application.

Runs on a dedicated worker thread, polls the FunPay client for new messages,
applies filters + rules (+ optional AI fallback), and schedules human-like,
anti-spam-friendly replies through a background scheduler. All state changes are
published as :class:`EngineEvent` objects to a listener (the UI) so the GUI can
update without ever touching engine internals directly.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional

from ..browser import BaseFunPayClient, create_client
from ..models.message import ChatMessage
from ..models.repository import Repository, get_repository
from ..utils.config import get_config
from ..utils.helpers import human_delay, sleep_interruptible, truncate
from ..utils.logger import get_logger
from . import notifier
from .ai_client import AIClient
from .plugins import PluginManager
from .rule_engine import RuleEngine

log = get_logger(__name__)


class EngineStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class EngineEvent:
    """Something worth telling the UI about."""

    type: str                      # status | processed | reply | error | stats
    payload: dict = field(default_factory=dict)


EventListener = Callable[[EngineEvent], None]


class AutoResponder:
    def __init__(self, repository: Optional[Repository] = None) -> None:
        self.repo = repository or get_repository()
        self.cfg = get_config()
        self.rule_engine = RuleEngine(self.repo)
        self.ai = AIClient()
        self.plugins = PluginManager()

        self._status = EngineStatus.STOPPED
        self._client: Optional[BaseFunPayClient] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._listeners: List[EventListener] = []
        self._scheduler = self._make_scheduler()

        self._started_at: Optional[datetime] = None
        self._known_chats: set[str] = set()
        self._last_reply_at: Dict[str, float] = {}   # per-chat cooldown
        self._history: Dict[str, List[str]] = {}     # per-chat convo for AI
        self._global_last_reply = 0.0

    # -- scheduler --------------------------------------------------------
    def _make_scheduler(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            sched = BackgroundScheduler(daemon=True)
            sched.start()
            log.debug("APScheduler started for deferred replies.")
            return sched
        except Exception as exc:
            log.warning("APScheduler unavailable (%s); using threading.Timer.", exc)
            return None

    # -- listeners --------------------------------------------------------
    def add_listener(self, listener: EventListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: EventListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _emit(self, event_type: str, **payload) -> None:
        event = EngineEvent(type=event_type, payload=payload)
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception as exc:  # pragma: no cover
                log.debug("Listener error: %s", exc)

    # -- public state -----------------------------------------------------
    @property
    def status(self) -> EngineStatus:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status in (EngineStatus.RUNNING, EngineStatus.STARTING)

    @property
    def uptime_seconds(self) -> int:
        if not self._started_at:
            return 0
        return int((datetime.now() - self._started_at).total_seconds())

    def _set_status(self, status: EngineStatus) -> None:
        self._status = status
        self._emit("status", status=status.value)
        log.info("Engine status → %s", status.value)

    # -- lifecycle --------------------------------------------------------
    def start(self, force_mock: bool = False) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._force_mock = force_mock
        self.plugins.load_all()
        self._thread = threading.Thread(target=self._run, name="fpar-engine",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._status == EngineStatus.STOPPED:
            return
        self._set_status(EngineStatus.STOPPING)
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and \
                self._thread is not threading.current_thread():
            self._thread.join(timeout=15)
        self._teardown_client()
        self.plugins.dispatch_stop()
        self._started_at = None
        self._set_status(EngineStatus.STOPPED)

    def shutdown(self) -> None:
        """Full shutdown incl. scheduler — call once on app exit."""
        self.stop()
        if self._scheduler is not None:
            try:
                self._scheduler.shutdown(wait=False)
            except Exception:
                pass

    def _teardown_client(self) -> None:
        if self._client:
            try:
                self._client.stop()
            except Exception:
                pass
            self._client = None

    # -- main loop --------------------------------------------------------
    def _run(self) -> None:
        self._set_status(EngineStatus.STARTING)
        self._started_at = datetime.now()
        try:
            account = self.repo.active_account()
            self._client = create_client(account, force_mock=getattr(
                self, "_force_mock", False))
            if not self._client.start():
                self._set_status(EngineStatus.ERROR)
                notifier.notify("FunPay AutoResponder",
                                "Не удалось войти в аккаунт / login failed.")
                return

            if self.cfg.get("auto_status_online", True):
                self._client.set_online(True)

            self.plugins.dispatch_start()
            self._set_status(EngineStatus.RUNNING)
            notifier.notify("FunPay AutoResponder",
                            "Автоответчик запущен ✅", sound=False)

            while not self._stop_event.is_set():
                self._poll_once()
                delay = human_delay(
                    float(self.cfg.get("poll_min_seconds", 3)),
                    float(self.cfg.get("poll_max_seconds", 8)),
                )
                sleep_interruptible(delay, self._stop_event.is_set)
        except Exception as exc:
            log.exception("Engine loop crashed: %s", exc)
            self.repo.stats.record_error()
            self._emit("error", message=str(exc))
            self._set_status(EngineStatus.ERROR)
        finally:
            if self.cfg.get("auto_status_online", True) and self._client:
                try:
                    self._client.set_online(False)
                except Exception:
                    pass

    def _poll_once(self) -> None:
        try:
            messages = self._client.fetch_new_messages() if self._client else []
        except Exception as exc:
            log.warning("Polling failed: %s", exc)
            self.repo.stats.record_error()
            return

        for message in messages:
            if self._stop_event.is_set():
                break
            self._handle_message(message)

    # -- message handling -------------------------------------------------
    def _handle_message(self, message: ChatMessage) -> None:
        if message.is_mine:
            return

        self.repo.stats.record_processed()
        self._history.setdefault(message.chat_id, []).append(
            f"{message.author}: {message.text}")
        self.plugins.dispatch_message(message)
        self._emit("processed", author=message.author,
                   text=truncate(message.text, 80), game=message.game)

        if not self._passes_filters(message):
            return

        reply = self._decide_reply(message)
        if reply is None:
            return

        reply_text, rule_id, price, used_ai = reply
        reply_text = self.plugins.apply_before_send(message, reply_text)
        self._schedule_reply(message, reply_text, rule_id, price, used_ai)

    def _passes_filters(self, message: ChatMessage) -> bool:
        author = (message.author or "").lower()
        blacklist = [x.lower() for x in self.cfg.get("blacklist", [])]
        whitelist = [x.lower() for x in self.cfg.get("whitelist", [])]

        if author in blacklist:
            log.debug("Skipping blacklisted user %s", message.author)
            return False
        if whitelist and author not in whitelist:
            log.debug("Skipping non-whitelisted user %s", message.author)
            return False

        mode = self.cfg.get("work_mode", "all_chats")
        is_new_chat = message.chat_id not in self._known_chats
        self._known_chats.add(message.chat_id)

        if mode == "new_dialogs" and not is_new_chat:
            return False
        if mode == "specific_games":
            allowed = [g.lower() for g in self.cfg.get("specific_games", [])]
            if allowed and (message.game or "").lower() not in allowed:
                return False
        return True

    def _decide_reply(self, message: ChatMessage):
        result = self.rule_engine.evaluate(message)
        if result and result.text:
            return result.text, result.rule.id if result.rule else None, \
                result.price, False

        # AI fallback (only if enabled and configured to fill gaps).
        if self.ai.enabled and self.cfg.get("ai_fallback_only", True):
            context = "\n".join(self._history.get(message.chat_id, [])[-8:])
            ai_reply = self.ai.generate_reply(message.text, context)
            if ai_reply:
                return ai_reply, None, 0.0, True
        return None

    # -- reply scheduling / anti-spam -------------------------------------
    def _within_cooldown(self, message: ChatMessage, rule_id: Optional[str]) -> bool:
        now = time.time()
        last = self._last_reply_at.get(message.chat_id, 0.0)
        rule = next((r for r in self.repo.rules() if r.id == rule_id), None)
        cooldown = rule.cooldown_seconds if rule else 0
        if cooldown and (now - last) < cooldown:
            log.debug("Chat %s within cooldown; skipping.", message.chat_id)
            return True
        return False

    def _schedule_reply(self, message: ChatMessage, text: str,
                        rule_id: Optional[str], price: float, used_ai: bool) -> None:
        if self._within_cooldown(message, rule_id):
            return

        delay = human_delay(
            float(self.cfg.get("reply_delay_min", 8)),
            float(self.cfg.get("reply_delay_max", 25)),
        )
        log.info("Scheduling reply to %s in %.1fs: %s",
                 message.author, delay, truncate(text, 60))

        def _send() -> None:
            if self._stop_event.is_set() or not self._client:
                return
            ok = False
            try:
                ok = self._client.send_message(message.chat_id, text)
            except Exception as exc:
                log.warning("send_message error: %s", exc)
            if ok:
                self._last_reply_at[message.chat_id] = time.time()
                self._history.setdefault(message.chat_id, []).append(f"me: {text}")
                self.repo.stats.record_reply(rule_id=rule_id, price=price, ai=used_ai)
                self.repo.save_stats()
                self._emit("reply", author=message.author,
                           text=truncate(text, 80), price=price, ai=used_ai)
                self._emit("stats")
                notifier.notify(
                    f"Ответ отправлен → {message.author}",
                    text, sound=True,
                )
            else:
                self.repo.stats.record_error()

        self._defer(_send, delay)

    def _defer(self, func: Callable[[], None], delay: float) -> None:
        if self._scheduler is not None:
            try:
                self._scheduler.add_job(
                    func, "date",
                    run_date=datetime.now() + timedelta(seconds=delay),
                    misfire_grace_time=30,
                )
                return
            except Exception as exc:
                log.debug("Scheduler add_job failed (%s); using Timer.", exc)
        timer = threading.Timer(delay, func)
        timer.daemon = True
        timer.start()
