"""Простая авторизация одного пользователя через подписанную cookie-сессию."""

from __future__ import annotations

from fastapi import Request
from itsdangerous import BadSignature, URLSafeSerializer

from .config import settings

_serializer = URLSafeSerializer(settings.secret_key, salt="invoiceforge-session")
COOKIE_NAME = "if_session"


def create_session_token() -> str:
    return _serializer.dumps({"auth": True})


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer.loads(token)
    except BadSignature:
        return False
    return bool(data.get("auth"))


def check_password(password: str) -> bool:
    # Сравнение простое: у продукта один администратор.
    return password == settings.password
