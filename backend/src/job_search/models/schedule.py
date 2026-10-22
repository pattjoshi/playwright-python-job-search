"""Saved daily-search schedule: what to run, and when."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_time(text: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = text.strip().split(":")
        hour, minute = int(hour_text), int(minute_text)
    except (AttributeError, ValueError):
        raise ValueError("Time must look like 09:00") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Time must be between 00:00 and 23:59")
    return hour, minute


@dataclass
class Schedule:
    time: str  # "HH:MM", 24-hour, local time
    days: list[str] = field(default_factory=lambda: list(DAYS))
    open_report: bool = True
    search: dict = field(default_factory=dict)  # serialized SearchOptions
    saved_at: str = ""

    def next_run(self, now: datetime | None = None) -> datetime:
        now = now or datetime.now()
        hour, minute = parse_time(self.time)
        for offset in range(8):
            day = now + timedelta(days=offset)
            candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if DAYS[candidate.weekday()] in self.days and candidate > now:
                return candidate
        raise ValueError("schedule has no days")  # can't happen after validation
