"""Small helpers shared by scrapers and the pipeline."""

import re

_UNIT_HOURS = {
    "second": 1 / 3600,
    "sec": 1 / 3600,
    "minute": 1 / 60,
    "min": 1 / 60,
    "hour": 1,
    "hr": 1,
    "day": 24,
    "week": 24 * 7,
    "month": 24 * 30,
    "year": 24 * 365,
}

_RELATIVE = re.compile(r"(\d+)\+?\s*(second|sec|minute|min|hour|hr|day|week|month|year)s?\b")


def parse_relative_age(text: str) -> float | None:
    """Turn job-board phrases like '3 hours ago' or 'Just posted' into hours.

    Returns None when the text can't be understood, so callers can decide
    whether to keep the job.
    """
    text = (text or "").strip().lower()
    if not text:
        return None
    if any(word in text for word in ("just now", "just posted", "today", "moments ago")):
        return 0.0
    if "few hours" in text:
        return 3.0
    if "yesterday" in text:
        return 24.0

    match = _RELATIVE.search(text)
    if match:
        return int(match.group(1)) * _UNIT_HOURS[match.group(2)]
    return None
