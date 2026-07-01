from app.settings import load_telegram_settings


def test_load_telegram_settings_normalizes_sources(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:token")
    monkeypatch.setenv(
        "TELEGRAM_SOURCES",
        "https://t.me/monitor_ukr,@cxidua,war_monitor,-1001234567890",
    )

    settings = load_telegram_settings()

    assert settings.enabled is True
    assert settings.is_bot_configured is True
    assert settings.sources == ["monitor_ukr", "cxidua", "war_monitor", "-1001234567890"]


def test_load_telegram_settings_web_mode_without_bot(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_ENABLED", "1")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_SOURCES", "monitor_ukr,https://t.me/war_monitor,-100555")

    settings = load_telegram_settings()

    assert settings.is_bot_configured is False
    assert settings.is_web_configured is True
    assert settings.web_sources == ["monitor_ukr", "war_monitor"]
