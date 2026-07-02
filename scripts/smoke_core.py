"""Headless smoke test of the core engine (no GUI).

Runs the AutoResponder with the mock FunPay client for a few seconds and prints
the resulting statistics. Used in CI / verification where no display exists.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging, get_logger  # noqa: E402
from src.core.engine import AutoResponder  # noqa: E402
from src.models.repository import get_repository  # noqa: E402


def main() -> int:
    setup_logging("INFO")
    log = get_logger("smoke")
    repo = get_repository()
    engine = AutoResponder(repo)

    events = []
    engine.add_listener(lambda e: events.append(e.type))

    log.info("Starting engine (mock) for ~14s...")
    engine.start(force_mock=True)
    time.sleep(14)
    engine.shutdown()

    stats = repo.stats
    log.info("processed=%d replies=%d earned=%.1f errors=%d",
             stats.messages_processed, stats.replies_sent, stats.earned,
             stats.errors)
    log.info("event types seen: %s", set(events))

    assert stats.messages_processed >= 1, "no messages processed"
    assert "status" in set(events), "no status events"
    print("SMOKE CORE: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
