"""Small helpers shared by scrapers and the pipeline."""

import re


class SearchStopped(Exception):
    """Raised inside a search when the user pressed Stop."""


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


_EXPERIENCE_RANGE = re.compile(r"(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_EXPERIENCE_MIN = re.compile(
    r"(?:(?:minimum|min\.?|at least)\s*(?:of\s*)?(\d{1,2})\s*\+?\s*(?:years?|yrs?))|(?:(\d{1,2})\s*\+\s*(?:years?|yrs?))",
    re.IGNORECASE,
)
_OPEN_ENDED_MAX = 40


def parse_experience(text: str) -> tuple[int, int] | None:
    """Years of experience a job asks for: '3-6 Yrs' -> (3, 6), '5+ years' -> (5, 40), 'Fresher' -> (0, 1)."""
    text = text or ""
    match = _EXPERIENCE_RANGE.search(text)
    if match:
        low, high = int(match.group(1)), int(match.group(2))
        return (min(low, high), max(low, high))
    match = _EXPERIENCE_MIN.search(text)
    if match:
        return (int(match.group(1) or match.group(2)), _OPEN_ENDED_MAX)
    if re.search(r"\bfreshers?\b", text, re.IGNORECASE):
        return (0, 1)
    return None


def experience_matches(job_range: tuple[int, int] | None, wanted: tuple[int, int] | None) -> bool:
    """True when the ranges overlap, or when either side is unknown (don't drop what we can't judge)."""
    if job_range is None or wanted is None:
        return True
    return job_range[0] <= wanted[1] and job_range[1] >= wanted[0]


def parse_experience_option(text: str) -> tuple[int, int]:
    """'1-2' / '1 to 2' / '3' -> (1, 2) / (1, 2) / (3, 3). Raises ValueError for anything else."""
    numbers = [int(n) for n in re.findall(r"\d+", text or "")]
    if not 1 <= len(numbers) <= 2 or not re.fullmatch(r"\s*\d+\s*(?:(?:-|to)\s*\d+\s*)?", text or ""):
        raise ValueError(f"experience must look like '1-2' or '3', got {text!r}")
    low, high = numbers[0], numbers[-1]
    if low > high:
        low, high = high, low
    if high > 50:
        raise ValueError("experience can be at most 50 years")
    return (low, high)
