"""Инициализация базы данных SQLite через SQLModel."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import settings

# check_same_thread=False позволяет использовать соединение в разных потоках
# (uvicorn воркеры). Для локального SQLite это безопасно.
engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Создаёт таблицы и стартовую запись настроек, если их ещё нет."""
    # Импорт моделей внутри функции, чтобы избежать циклических импортов.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing = session.get(models.CompanySettings, 1)
        if existing is None:
            session.add(models.CompanySettings(id=1))
            session.commit()


def get_session() -> Iterator[Session]:
    """Зависимость FastAPI: выдаёт сессию БД на время запроса."""
    with Session(engine) as session:
        yield session
