"""FunPay account model.

Only non-secret metadata is persisted here. Passwords / golden_key cookies are
stored via the OS keyring (see ``utils.security``), keyed by the account id.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..utils.helpers import new_id
from ..utils import security


@dataclass
class Account:
    label: str = "My FunPay account"
    login: str = ""            # email / username (non-secret display value)
    use_golden_key: bool = True
    session_valid: bool = False
    id: str = field(default_factory=new_id)

    # -- secret helpers (keyring backed) ---------------------------------
    @property
    def _pwd_key(self) -> str:
        return f"account:{self.id}:password"

    @property
    def _gk_key(self) -> str:
        return f"account:{self.id}:golden_key"

    def set_password(self, password: str) -> None:
        security.set_secret(self._pwd_key, password)

    def get_password(self) -> str:
        return security.get_secret(self._pwd_key) or ""

    def set_golden_key(self, value: str) -> None:
        security.set_secret(self._gk_key, value)

    def get_golden_key(self) -> str:
        return security.get_secret(self._gk_key) or ""

    def forget_secrets(self) -> None:
        security.delete_secret(self._pwd_key)
        security.delete_secret(self._gk_key)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "login": self.login,
            "use_golden_key": self.use_golden_key,
            "session_valid": self.session_valid,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        allowed = {"label", "login", "use_golden_key", "session_valid", "id"}
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)
