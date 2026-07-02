"""Загрузка настроек приложения из переменных окружения / файла .env.

Файл .env читается вручную (без внешних зависимостей), чтобы приложение
запускалось у покупателя без лишних пакетов.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Простейший парсер .env: KEY=VALUE построчно, без кавычек-магии."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Не перезаписываем уже установленные переменные окружения.
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


class Settings:
    """Контейнер с конфигурацией приложения."""

    app_name: str = "InvoiceForge"
    version: str = "1.0.0"

    # Пароль для входа в панель управления.
    password: str = os.getenv("INVOICEFORGE_PASSWORD", "admin")

    # Секрет для подписи cookie. В проде обязательно менять.
    secret_key: str = os.getenv(
        "INVOICEFORGE_SECRET", "invoiceforge-dev-secret-change-me"
    )

    port: int = int(os.getenv("INVOICEFORGE_PORT", "8000"))

    data_dir: Path = BASE_DIR / os.getenv("INVOICEFORGE_DATA_DIR", "data")

    # Лимиты демо-режима (когда лицензия не активирована).
    demo_max_clients: int = 3
    demo_max_documents: int = 5

    @property
    def db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "invoiceforge.db"

    @property
    def license_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "license.key"


settings = Settings()
