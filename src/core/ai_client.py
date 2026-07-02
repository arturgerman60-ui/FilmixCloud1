"""Optional local-AI integration (Ollama / LM Studio).

Both backends expose an OpenAI-ish HTTP API on localhost. This module keeps the
dependency surface tiny (just ``requests``) and fails soft: if the backend is
unreachable, calls return ``None`` and the engine falls back to rule replies.
"""
from __future__ import annotations

from typing import List, Optional

from ..utils.config import get_config
from ..utils.logger import get_logger

log = get_logger(__name__)


class AIClient:
    def __init__(self) -> None:
        cfg = get_config()
        self.backend = cfg.get("ai_backend", "none")
        self.base_url = cfg.get("ai_base_url", "http://localhost:11434").rstrip("/")
        self.model = cfg.get("ai_model", "llama3.1")
        self.system_prompt = cfg.get("ai_system_prompt", "")

    @property
    def enabled(self) -> bool:
        return self.backend in ("ollama", "lmstudio")

    def _post(self, url: str, payload: dict, timeout: int = 30) -> Optional[dict]:
        try:
            import requests

            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            log.warning("AI request failed (%s): %s", url, exc)
            return None

    def generate_reply(self, user_message: str,
                       context: Optional[str] = None) -> Optional[str]:
        """Produce a customer-support style reply, or None on failure."""
        if not self.enabled:
            return None

        prompt = user_message
        if context:
            prompt = f"Context:\n{context}\n\nCustomer message:\n{user_message}"

        if self.backend == "ollama":
            data = self._post(f"{self.base_url}/api/chat", {
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            })
            if data:
                return (data.get("message", {}) or {}).get("content", "").strip() or None

        elif self.backend == "lmstudio":
            data = self._post(f"{self.base_url}/v1/chat/completions", {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.6,
            })
            if data:
                choices = data.get("choices") or []
                if choices:
                    return (choices[0].get("message", {})
                            .get("content", "").strip() or None)
        return None

    def generate_template(self, description: str) -> Optional[str]:
        """Generate a message template body from a natural-language brief."""
        if not self.enabled:
            return None
        instruction = (
            "Write a short, friendly marketplace auto-reply message template. "
            "Use placeholders {username}, {game}, {price} where natural. "
            f"Purpose: {description}. Return only the message text."
        )
        return self.generate_reply(instruction)

    def suggest_best_replies(self, history: List[str]) -> Optional[str]:
        """Analyse a conversation and suggest the best next reply."""
        if not self.enabled or not history:
            return None
        convo = "\n".join(history[-12:])
        instruction = (
            "You are assisting a marketplace seller. Given the conversation "
            "below, suggest the single best next reply (concise, polite, "
            "sales-oriented):\n\n" + convo
        )
        return self.generate_reply(instruction)

    def ping(self) -> bool:
        """Check whether the configured backend is reachable."""
        if not self.enabled:
            return False
        try:
            import requests

            if self.backend == "ollama":
                r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            else:
                r = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return r.ok
        except Exception:
            return False
