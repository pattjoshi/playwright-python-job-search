"""Settings loaded from environment variables (and a local .env file)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL = "gpt-5.4-mini"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    chromium_executable: str | None


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
        chromium_executable=os.getenv("CHROMIUM_EXECUTABLE") or None,
    )
