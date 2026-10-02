"""Settings loaded from environment variables (and a local .env file).

Search settings here are your personal defaults. Each one matches a command-line
option of the same name (RESULTS <-> --results), and the command line always wins.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from job_search.utils import parse_experience_option

DEFAULT_MODEL = "gpt-5.4-mini"
PROJECT_ENV = Path(__file__).resolve().parent.parent / ".env"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str = DEFAULT_MODEL
    chromium_executable: str | None = None

    # Search defaults
    resume: Path | None = None
    locations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    sites: list[str] = field(default_factory=list)  # empty = all boards
    results: int = 10
    results_per_site: dict[str, int] = field(default_factory=dict)  # from RESULTS_<SITE>
    hours: int = 24
    top: int = 40
    max_pages: int = 3
    experience: tuple[int, int] | None = None
    only_new: bool = False
    history_path: Path = Path("data") / "history.sqlite3"
    keep_days: int = 30  # delete old uploads/reports/cache after this many days; 0 = never
    parallel_sites: bool = True  # search all job sites at the same time
    # Optional OpenAI prices (USD per 1M tokens) to show an estimated cost per run.
    price_input: float | None = None
    price_output: float | None = None
    price_cached_input: float | None = None

    @property
    def cache_path(self) -> Path:
        return self.history_path.parent / "cache.sqlite3"


def load_settings() -> Settings:
    # .env in the folder you run from first, then the project folder. Neither overrides
    # variables already set in the real environment.
    load_dotenv(find_dotenv(usecwd=True))
    load_dotenv(PROJECT_ENV)
    resume = _get("RESUME")
    return Settings(
        openai_api_key=_get("OPENAI_API_KEY"),
        openai_model=_get("OPENAI_MODEL") or DEFAULT_MODEL,
        chromium_executable=_get("CHROMIUM_EXECUTABLE"),
        resume=Path(resume) if resume else None,
        locations=_get_list("LOCATION"),
        keywords=_get_list("KEYWORDS"),
        sites=[site.lower() for site in _get_list("SITES")],
        results=_get_int("RESULTS", 10),
        results_per_site=_get_results_per_site(),
        hours=_get_int("HOURS", 24),
        top=_get_int("TOP", 40),
        max_pages=_get_int("MAX_PAGES", 3),
        experience=_get_experience(),
        only_new=_get_bool("ONLY_NEW"),
        history_path=Path(_get("HISTORY_DB") or Path("data") / "history.sqlite3"),
        keep_days=_get_int("KEEP_DAYS", 30, minimum=0),
        parallel_sites=_get_bool("PARALLEL_SITES", default=True),
        price_input=_get_price("OPENAI_PRICE_INPUT"),
        price_output=_get_price("OPENAI_PRICE_OUTPUT"),
        price_cached_input=_get_price("OPENAI_PRICE_CACHED_INPUT"),
    )


def _get(name: str) -> str | None:
    value = (os.getenv(name) or "").strip().strip("\"'")
    return value or None


def _get_list(name: str) -> list[str]:
    # Comma-separated, because search phrases contain spaces: "Python Developer, SDET"
    return [item.strip() for item in (_get(name) or "").split(",") if item.strip()]


def _get_results_per_site() -> dict[str, int]:
    # RESULTS_LINKEDIN=20, RESULTS_NAUKRI=12, ... (any site name works)
    prefix = "RESULTS_"
    return {
        name[len(prefix) :].lower(): _get_int(name, 0)
        for name in sorted(os.environ)
        if name.upper().startswith(prefix) and _get(name) is not None
    }


def _get_experience() -> tuple[int, int] | None:
    value = _get("EXPERIENCE")
    if value is None:
        return None
    try:
        return parse_experience_option(value)
    except ValueError as error:
        raise ValueError(f"EXPERIENCE in .env: {error}") from None


def _get_price(name: str) -> float | None:
    value = _get(name)
    if value is None:
        return None
    try:
        price = float(value)
    except ValueError:
        raise ValueError(f"{name} in .env must be a number (USD per 1M tokens), got {value!r}") from None
    if price < 0:
        raise ValueError(f"{name} in .env can't be negative")
    return price


def _get_bool(name: str, default: bool = False) -> bool:
    value = (_get(name) or "").lower()
    if value == "":
        return default
    if value in ("0", "false", "no", "off"):
        return False
    if value in ("1", "true", "yes", "on"):
        return True
    raise ValueError(f"{name} in .env must be true or false, got {value!r}")


def _get_int(name: str, default: int, minimum: int = 1) -> int:
    value = _get(name)
    if value is None:
        return default
    try:
        number = int(value)
    except ValueError:
        raise ValueError(f"{name} in .env must be a whole number, got {value!r}") from None
    if number < minimum:
        raise ValueError(f"{name} in .env must be at least {minimum}, got {number}")
    return number
