"""Settings loaded from environment variables (and a local .env file).

Search settings here are your personal defaults. Each one matches a command-line
option of the same name (RESULTS <-> --results), and the command line always wins.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

DEFAULT_MODEL = "gpt-5.4-mini"
PROJECT_ENV = Path(__file__).resolve().parent.parent / ".env"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str = DEFAULT_MODEL
    chromium_executable: str | None = None

    # Search defaults
    resume: Path | None = None
    location: str | None = None
    keywords: list[str] = field(default_factory=list)
    sites: list[str] = field(default_factory=list)  # empty = all boards
    results: int = 10
    hours: int = 24
    top: int = 40
    max_pages: int = 3


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
        location=_get("LOCATION"),
        keywords=_get_list("KEYWORDS"),
        sites=[site.lower() for site in _get_list("SITES")],
        results=_get_int("RESULTS", 10),
        hours=_get_int("HOURS", 24),
        top=_get_int("TOP", 40),
        max_pages=_get_int("MAX_PAGES", 3),
    )


def _get(name: str) -> str | None:
    value = (os.getenv(name) or "").strip().strip("\"'")
    return value or None


def _get_list(name: str) -> list[str]:
    # Comma-separated, because search phrases contain spaces: "Python Developer, SDET"
    return [item.strip() for item in (_get(name) or "").split(",") if item.strip()]


def _get_int(name: str, default: int) -> int:
    value = _get(name)
    if value is None:
        return default
    try:
        number = int(value)
    except ValueError:
        raise ValueError(f"{name} in .env must be a whole number, got {value!r}") from None
    if number < 1:
        raise ValueError(f"{name} in .env must be at least 1, got {number}")
    return number
