"""Модели данных (таблицы) приложения."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CompanySettings(SQLModel, table=True):
    """Настройки компании-продавца (одна запись, id=1)."""

    id: int | None = Field(default=1, primary_key=True)
    company_name: str = "Моя компания"
    owner_name: str = ""
    address: str = ""
    tax_id: str = ""  # ЕДРПОУ/ИНН
    phone: str = ""
    email: str = ""
    bank_details: str = ""
    currency: str = "UAH"
    tax_rate: float = 0.0  # НДС/налог в %, по умолчанию 0
    invoice_prefix: str = "INV-"
    proposal_prefix: str = "КП-"
    next_invoice_number: int = 1
    next_proposal_number: int = 1
    language: str = "ru"
    accent_color: str = "#4f7cff"


class Client(SQLModel, table=True):
    """Клиент/покупатель."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    tax_id: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class Document(SQLModel, table=True):
    """Счёт или коммерческое предложение."""

    id: int | None = Field(default=None, primary_key=True)
    doc_type: str = "invoice"  # invoice | proposal
    number: str = ""
    client_id: int = Field(foreign_key="client.id")
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    status: str = "draft"  # draft | sent | paid | overdue
    currency: str = "UAH"
    tax_rate: float = 0.0
    discount: float = 0.0  # абсолютная скидка в валюте
    notes: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class LineItem(SQLModel, table=True):
    """Строка позиции в документе."""

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id")
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    position: int = 0
