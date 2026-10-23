"""Which job boards you're signed in to (in auto-apply's saved browser), and pages saved when a job fails."""

import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

log = logging.getLogger(__name__)

SIGN_IN_WAIT_S = 300  # time you get to log in yourself (OTP included) after pressing Sign in


class BrowserClosedError(Exception):
    """The auto-apply browser window was closed while it was working."""


class BoardSignIns:
    """Remembers boards you signed in to, so the page can show "Signed in" and let you turn them on."""

    def __init__(self, files_dir: Path):
        self.path = Path(files_dir) / "signed-in.json"

    def boards(self) -> dict[str, str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def mark(self, board: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({**self.boards(), board: datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")


def save_page(page: Page, path: Path) -> None:
    """Keep the page's HTML when a job didn't go through, so the problem can be fixed from the real page."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page.content(), encoding="utf-8")
    except Exception as error:  # saving it is a nice-to-have
        log.debug("Couldn't save the page: %s", error)


def is_closed_error(page: Page, error: Exception) -> bool:
    return page.is_closed() or "has been closed" in str(error) or "Failed to open a new tab" in str(error)
