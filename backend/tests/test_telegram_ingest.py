import pytest

from app.settings import TelegramSettings
from app.store import EventStore
from app.telegram_ingest import BS4_AVAILABLE, TelegramIngestor


pytestmark = pytest.mark.skipif(not BS4_AVAILABLE, reason="beautifulsoup4 is required")


def test_extract_web_messages_from_public_channel_html() -> None:
    html = """
    <div class="tgme_widget_message" data-post="monitor_ukr/123" data-time="1719855600">
      <div class="tgme_widget_message_text js-message_text">Шахед у Харківській області</div>
    </div>
    <div class="tgme_widget_message" data-post="monitor_ukr/124" data-time="1719855660">
      <div class="tgme_widget_message_text js-message_text">FPV в районі Чугуїв</div>
    </div>
    """
    settings = TelegramSettings(
        enabled=True,
        bot_token=None,
        api_id=None,
        api_hash=None,
        session_string=None,
        sources=["monitor_ukr"],
        poll_seconds=20,
        bootstrap_limit=20,
    )
    ingestor = TelegramIngestor(store=EventStore(), settings=settings)

    messages = ingestor._extract_web_messages(html, fallback_source="monitor_ukr")

    assert len(messages) == 2
    assert messages[0]["source"] == "monitor_ukr"
    assert messages[0]["message_id"] == 123
    assert "Харківській" in messages[0]["text"]
