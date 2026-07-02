"""Вспомогательные функции: расчёт сумм и форматирование валют."""

from __future__ import annotations

from .models import Document, LineItem

CURRENCY_SYMBOLS = {
    "UAH": "₴",
    "USD": "$",
    "EUR": "€",
    "RUB": "₽",
    "PLN": "zł",
    "GBP": "£",
}


def currency_symbol(code: str) -> str:
    return CURRENCY_SYMBOLS.get(code.upper(), code)


def format_money(amount: float, currency: str = "UAH") -> str:
    """Форматирует число как «1 234,56 ₴» (пробел-разделитель тысяч, запятая)."""
    whole, frac = f"{amount:,.2f}".split(".")
    whole = whole.replace(",", " ")
    return f"{whole},{frac} {currency_symbol(currency)}"


def compute_totals(document: Document, items: list[LineItem]) -> dict[str, float]:
    """Возвращает subtotal, discount, tax, total для документа."""
    subtotal = sum(item.quantity * item.unit_price for item in items)
    discount = max(0.0, min(document.discount, subtotal))
    taxable = subtotal - discount
    tax = taxable * (document.tax_rate / 100.0)
    total = taxable + tax
    return {
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": total,
    }
