"""Playwright-based FunPay automation client.

This talks to the real funpay.com website through a Chromium browser driven by
Playwright. Authentication is done either via the ``golden_key`` session cookie
(recommended, most reliable) or via the login form.

NOTE ON SELECTORS
-----------------
FunPay is a third-party site and its markup can change without notice. All CSS
selectors are grouped in :class:`Selectors` so they can be updated in one place.
Every network/DOM interaction is defensively wrapped so a markup change degrades
to "no new messages" rather than crashing the app.

Respect FunPay's Terms of Service and applicable laws when using automation.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from ..models.message import ChatMessage
from ..utils.config import get_config
from ..utils.helpers import human_delay, typing_time
from ..utils.logger import get_logger
from ..utils.paths import sessions_dir
from .base import BaseFunPayClient, ClientState

log = get_logger(__name__)

FUNPAY_BASE = "https://funpay.com"


@dataclass
class Selectors:
    """Centralised CSS selectors (update here if FunPay changes markup)."""

    logged_in_marker: str = ".user-link-name, .menu-item-night, .avatar-photo"
    login_form_user: str = "input[name='login']"
    login_form_pass: str = "input[name='password']"
    login_submit: str = "button.btn-primary[type='submit'], .form-login button"
    chat_list_item: str = "a.contact-item"
    chat_item_id_attr: str = "data-id"
    chat_item_name: str = ".media-user-name"
    chat_item_preview: str = ".contact-item-message"
    chat_item_unread: str = ".contact-item.unread, .contact-item.new"
    message_node: str = ".chat-message, .message"
    message_author: str = ".media-user-name, .chat-msg-author"
    message_text: str = ".chat-msg-text, .message-text"
    compose_textarea: str = "textarea.form-control, .chat-form textarea"
    compose_submit: str = ".chat-form button[type='submit'], .btn-send"


class PlaywrightFunPayClient(BaseFunPayClient):
    def __init__(self, account, headless: bool = True) -> None:
        super().__init__(account)
        self.headless = headless
        self.sel = Selectors()
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        # Track last-seen message signature per chat to detect new messages.
        self._seen: Dict[str, Set[str]] = {}

    # -- availability -----------------------------------------------------
    @staticmethod
    def is_available() -> bool:
        try:
            import playwright  # noqa: F401
            from playwright.sync_api import sync_playwright  # noqa: F401

            return True
        except Exception:
            return False

    # -- lifecycle --------------------------------------------------------
    def start(self) -> bool:
        from playwright.sync_api import sync_playwright

        self.state = ClientState.STARTING
        cfg = get_config()
        try:
            self._pw = sync_playwright().start()
            launch_kwargs: dict = {"headless": self.headless}

            proxy = self._proxy_config(cfg)
            if proxy:
                launch_kwargs["proxy"] = proxy

            self._browser = self._pw.chromium.launch(**launch_kwargs)

            storage_state = self._storage_path()
            context_kwargs: dict = {
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "viewport": {"width": 1366, "height": 768},
                "locale": "ru-RU",
            }
            if storage_state.exists():
                context_kwargs["storage_state"] = str(storage_state)

            self._context = self._browser.new_context(**context_kwargs)
            self._page = self._context.new_page()
            log.info("Playwright browser launched (headless=%s).", self.headless)
            return self.login()
        except Exception as exc:
            log.exception("Failed to start Playwright client: %s", exc)
            self.state = ClientState.ERROR
            self.stop()
            return False

    def _proxy_config(self, cfg) -> Optional[dict]:
        if not cfg.get("proxy_enabled"):
            return None
        host = cfg.get("proxy_host")
        port = cfg.get("proxy_port")
        if not host or not port:
            return None
        scheme = "socks5" if cfg.get("proxy_type") == "socks5" else "http"
        server = f"{scheme}://{host}:{port}"
        proxy = {"server": server}
        user = cfg.get("proxy_user")
        if user:
            proxy["username"] = user
            from ..utils import security

            proxy["password"] = security.get_secret("proxy:password") or ""
        return proxy

    def _storage_path(self):
        return sessions_dir() / f"{self.account.id}.json"

    def _persist_session(self) -> None:
        try:
            if self._context:
                self._context.storage_state(path=str(self._storage_path()))
        except Exception as exc:  # pragma: no cover
            log.debug("Could not persist session: %s", exc)

    def stop(self) -> None:
        for closer in (
            lambda: self._context and self._context.close(),
            lambda: self._browser and self._browser.close(),
            lambda: self._pw and self._pw.stop(),
        ):
            try:
                closer()
            except Exception:
                pass
        self._page = self._browser = self._context = self._pw = None
        self.state = ClientState.STOPPED
        log.info("Playwright client stopped.")

    # -- auth -------------------------------------------------------------
    def login(self) -> bool:
        if not self._page:
            return False
        try:
            golden_key = self.account.get_golden_key()
            if self.account.use_golden_key and golden_key:
                self._context.add_cookies([{
                    "name": "golden_key",
                    "value": golden_key,
                    "domain": ".funpay.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }])
                self._page.goto(FUNPAY_BASE, wait_until="domcontentloaded",
                                timeout=30000)
            else:
                self._form_login()

            if self.is_logged_in():
                self.account.session_valid = True
                self.state = ClientState.LOGGED_IN
                self._persist_session()
                log.info("Logged in to FunPay as '%s'.", self.account.login or "?")
                return True

            self.account.session_valid = False
            self.state = ClientState.LOGGED_OUT
            log.warning("FunPay login failed — check golden_key/credentials.")
            return False
        except Exception as exc:
            log.exception("Login error: %s", exc)
            self.state = ClientState.ERROR
            return False

    def _form_login(self) -> None:
        self._page.goto(f"{FUNPAY_BASE}/account/login",
                        wait_until="domcontentloaded", timeout=30000)
        self._page.fill(self.sel.login_form_user, self.account.login)
        self._page.fill(self.sel.login_form_pass, self.account.get_password())
        self._page.click(self.sel.login_submit)
        self._page.wait_for_load_state("networkidle", timeout=30000)

    def is_logged_in(self) -> bool:
        if not self._page:
            return False
        try:
            return self._page.locator(self.sel.logged_in_marker).count() > 0
        except Exception:
            return False

    # -- messaging --------------------------------------------------------
    def fetch_new_messages(self) -> List[ChatMessage]:
        if not self._page:
            return []
        results: List[ChatMessage] = []
        try:
            self._page.goto(f"{FUNPAY_BASE}/chat/",
                            wait_until="domcontentloaded", timeout=30000)
            items = self._page.locator(self.sel.chat_list_item)
            count = min(items.count(), 30)
            for i in range(count):
                item = items.nth(i)
                try:
                    chat_id = item.get_attribute(self.sel.chat_item_id_attr) or str(i)
                    author = self._safe_text(item, self.sel.chat_item_name)
                    preview = self._safe_text(item, self.sel.chat_item_preview)
                    if not preview:
                        continue
                    signature = f"{author}|{preview}"
                    seen = self._seen.setdefault(chat_id, set())
                    if signature in seen:
                        continue
                    seen.add(signature)
                    results.append(ChatMessage(
                        chat_id=chat_id, author=author or "user",
                        text=preview, is_mine=False,
                    ))
                except Exception:
                    continue
        except Exception as exc:
            log.debug("fetch_new_messages failed: %s", exc)
        return results

    def _safe_text(self, scope, selector: str) -> str:
        try:
            loc = scope.locator(selector).first
            if loc.count() == 0:
                return ""
            return (loc.inner_text() or "").strip()
        except Exception:
            return ""

    def send_message(self, chat_id: str, text: str) -> bool:
        if not self._page:
            return False
        try:
            self._page.goto(f"{FUNPAY_BASE}/chat/?node={chat_id}",
                            wait_until="domcontentloaded", timeout=30000)
            box = self._page.locator(self.sel.compose_textarea).first
            box.click()
            # Human-like typing cadence.
            delay_ms = int(typing_time(text) * 1000 / max(len(text), 1))
            box.type(text, delay=max(delay_ms, 15))
            time.sleep(human_delay(0.4, 1.2))
            self._page.locator(self.sel.compose_submit).first.click()
            self._persist_session()
            return True
        except Exception as exc:
            log.warning("send_message failed for chat %s: %s", chat_id, exc)
            return False

    def set_online(self, online: bool) -> None:
        # FunPay shows presence automatically while the session is active; we
        # simply keep the tab warm. Explicit toggling is a no-op placeholder.
        return None
