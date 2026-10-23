"""Auto-apply's rules: valid settings, today's limits, and which platforms to leave out of a run."""

from job_search.repositories.auto_apply_repository import SETTINGS
from job_search.services.auto_apply.boards import BOARDS
from job_search.services.auto_apply.platforms import PLATFORMS

LIMITS = {"min_score": (0, 100), "daily_limit": (1, 100), "board_daily_limit": (1, 50)}
COMPANY_PLATFORMS = (*PLATFORMS, "other")


class AutoApplyError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def clean_settings(values: dict) -> dict:
    """Validated settings from a request body (only the keys given). Raises AutoApplyError."""
    cleaned = {}
    for name in SETTINGS:
        if name not in values:
            continue
        value = values[name]
        if name in LIMITS:
            low, high = LIMITS[name]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise AutoApplyError(f"{name.replace('_', ' ').capitalize()} must be a whole number from {low} to {high}.")
        elif not isinstance(value, bool):
            raise AutoApplyError(f"{name.replace('_', ' ').capitalize()} must be true or false.")
        cleaned[name] = value
    return cleaned


def remaining_today(settings: dict, done: dict[str, int]) -> dict[str, int]:
    """{"company": n, "naukri": n, ...}: how many more applications each kind may send today."""
    company_done = sum(count for platform, count in done.items() if platform not in BOARDS)
    left = {"company": max(0, settings["daily_limit"] - company_done)}
    left.update({board: max(0, settings["board_daily_limit"] - done.get(board, 0)) for board in BOARDS})
    return left


def skipped_platforms(skip: set[str], left: dict[str, int]) -> tuple[str, ...]:
    """Platforms not to pick from now: boards that are off, signed out or at their limit; company sites at theirs."""
    return (*skip, *(() if left["company"] else COMPANY_PLATFORMS))
