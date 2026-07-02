"""Small stateless helpers shared across the app."""
from __future__ import annotations

import random
import time
import uuid
from datetime import datetime
from typing import Iterable


def new_id() -> str:
    """Short unique identifier for records."""
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def human_delay(min_s: float, max_s: float) -> float:
    """Return a randomised, human-looking delay in seconds.

    Uses a triangular distribution biased toward the lower bound so most
    replies feel snappy while occasionally pausing longer — closer to real
    human behaviour than a uniform distribution.
    """
    if max_s < min_s:
        min_s, max_s = max_s, min_s
    if max_s <= 0:
        return 0.0
    mode = min_s + (max_s - min_s) * 0.35
    return round(random.triangular(min_s, max_s, mode), 2)


def typing_time(text: str, cps: float = 7.0) -> float:
    """Estimate a believable 'typing' duration for a message."""
    if not text:
        return 0.0
    base = len(text) / max(cps, 1.0)
    return round(min(base * random.uniform(0.8, 1.3), 12.0), 2)


def sleep_interruptible(seconds: float, stop_check, step: float = 0.2) -> bool:
    """Sleep in small steps, aborting early if ``stop_check()`` becomes true.

    Returns True if it slept the whole duration, False if interrupted.
    """
    elapsed = 0.0
    while elapsed < seconds:
        if stop_check():
            return False
        chunk = min(step, seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk
    return True


def truncate(text: str, length: int = 60) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= length else text[: length - 1] + "…"


def parse_price(text: str) -> float | None:
    """Extract the first number from a template/message as a price value."""
    import re

    match = re.search(r"(\d+[\.,]?\d*)", text or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def coalesce(*values: Iterable) -> object:
    for value in values:
        if value:
            return value
    return None
