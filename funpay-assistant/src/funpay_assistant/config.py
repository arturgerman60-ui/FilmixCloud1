"""Хранилище настроек в папке пользователя (%APPDATA%/FunPayAssistant).

golden_key (сессия FunPay) хранится не в открытом виде, а зашифрованным
через Fernet: ключ шифрования лежит рядом в файле key.bin и привязан к
конкретному ПК пользователя.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from cryptography.fernet import Fernet


def get_config_dir() -> Path:
    """Возвращает папку для данных приложения (кроссплатформенно)."""
    if os.name == "nt":  # Windows
        base = Path(os.getenv("APPDATA", Path.home()))
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / "FunPayAssistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fernet() -> Fernet:
    """Ключ шифрования для golden_key. Создаётся один раз на этом ПК."""
    key_file = get_config_dir() / "key.bin"
    if not key_file.exists():
        key_file.write_bytes(Fernet.generate_key())
    return Fernet(key_file.read_bytes())


@dataclass
class AppConfig:
    """Все пользовательские настройки приложения."""

    golden_key_encrypted: str = ""  # зашифрованный cookie сессии FunPay
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    demo_mode: bool = True          # безопасный режим без реального FunPay
    auto_raise: bool = True         # авто-поднятие лотов
    raise_interval_min: int = 240   # как часто поднимать (мин)
    auto_reply: bool = True         # авто-ответчик
    auto_delivery: bool = True      # авто-выдача товара
    poll_interval_sec: int = 6      # период опроса FunPay
    license_key: str = ""

    def set_golden_key(self, plain: str) -> None:
        if plain:
            self.golden_key_encrypted = _fernet().encrypt(plain.encode("utf-8")).decode("ascii")
        else:
            self.golden_key_encrypted = ""

    def get_golden_key(self) -> str:
        if not self.golden_key_encrypted:
            return ""
        try:
            return _fernet().decrypt(self.golden_key_encrypted.encode("ascii")).decode("utf-8")
        except Exception:  # noqa: BLE001 — повреждённый/чужой ключ
            return ""


def config_path() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig(**{k: v for k, v in data.items() if k in AppConfig().__dict__})
    except Exception:  # noqa: BLE001 — битый конфиг = дефолт
        return AppConfig()


def save_config(config: AppConfig) -> None:
    config_path().write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8"
    )
