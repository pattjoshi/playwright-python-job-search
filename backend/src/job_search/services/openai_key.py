"""The OpenAI key: saved in Settings (encrypted on this computer), or OPENAI_API_KEY from .env."""

import logging
import re
from collections.abc import Callable
from dataclasses import replace

from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI, PermissionDeniedError

from job_search.config import Settings
from job_search.repositories.secret_store import SecretStore

log = logging.getLogger(__name__)

SECRET_NAME = "openai_api_key"
NO_KEY_MESSAGE = "Add your OpenAI key first: Settings → OpenAI key (or OPENAI_API_KEY in the .env file)."
KEY_PATTERN = re.compile(r"^sk-[A-Za-z0-9_\-]{20,300}$")


class OpenAIKeyError(ValueError):
    """A key that can't be saved; the message is shown on the page."""


def check_with_openai(key: str) -> None:
    """Ask OpenAI whether it accepts the key (listing models costs nothing)."""
    try:
        OpenAI(api_key=key, max_retries=1, timeout=15).models.list()
    except (AuthenticationError, PermissionDeniedError) as error:
        raise OpenAIKeyError("OpenAI didn't accept this key. Copy it again from platform.openai.com/api-keys.") from error
    except (APIConnectionError, APITimeoutError) as error:
        raise OpenAIKeyError("Couldn't reach OpenAI to check the key. Check your internet connection and try again.") from error


def hint(key: str | None) -> str | None:
    """Enough to recognise a key without revealing it: "sk-…a1b2"."""
    return f"sk-…{key[-4:]}" if key else None


class OpenAIKeyService:
    def __init__(self, store: SecretStore, env_key: str | None, check: Callable[[str], None] = check_with_openai):
        self.store, self.env_key, self.check = store, env_key, check

    def saved(self) -> str | None:
        return self.store.get(SECRET_NAME)

    def current(self) -> str | None:
        """The key the app uses: the one saved in Settings wins over .env."""
        return self.saved() or self.env_key

    def status(self) -> dict:
        saved = self.saved()
        source = "settings" if saved else "env" if self.env_key else None
        return {"source": source, "hint": hint(self.current())}

    def save(self, key: object) -> dict:
        key = str(key or "").strip()
        if not KEY_PATTERN.match(key):
            raise OpenAIKeyError("That doesn't look like an OpenAI key (it starts with sk- and has no spaces).")
        self.check(key)
        self.store.set(SECRET_NAME, key)
        log.info("OpenAI key saved in Settings (%s)", hint(key))
        return self.status()

    def remove(self) -> dict:
        self.store.delete(SECRET_NAME)
        return self.status()


def with_saved_key(settings: Settings, keys: OpenAIKeyService | None = None) -> Settings:
    """Settings that use the key saved in Settings when there is one (for the web app, the daily search and the CLI)."""
    keys = keys or OpenAIKeyService(SecretStore(settings.history_path.parent), settings.openai_api_key)
    return replace(settings, saved_key=keys.saved)
