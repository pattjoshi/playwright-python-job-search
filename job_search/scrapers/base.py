"""Common interface every job-board scraper implements."""

import logging
import random
import threading
from abc import ABC, abstractmethod

from playwright.sync_api import BrowserContext, Page

from job_search.models import Job
from job_search.utils import SearchStopped

log = logging.getLogger(__name__)


class BaseScraper(ABC):
    #: Short id used on the command line and in reports, e.g. "linkedin".
    name: str = ""

    def __init__(
        self,
        context: BrowserContext,
        max_pages: int = 3,
        max_age_hours: int = 24,
        delay_range: tuple[float, float] = (2.0, 5.0),
        interactive: bool = False,
        experience: tuple[int, int] | None = None,
        stop_event: threading.Event | None = None,
    ):
        self.context = context
        self.max_pages = max_pages
        self.max_age_hours = max_age_hours
        self.delay_range = delay_range
        # True when the browser window is visible, so a person can solve a bot check.
        self.interactive = interactive
        # Wanted years of experience (min, max), for boards that can filter by it.
        self.experience = experience
        self.stop_event = stop_event or threading.Event()
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None or self._page.is_closed():
            self._page = self.context.new_page()
        return self._page

    @abstractmethod
    def search(self, query: str, location: str) -> list[Job]:
        """Return jobs for one query/location, using the board's own date filter."""

    def fetch_description(self, job: Job) -> None:
        """Fill in job.description. Boards that include it in search results can skip this."""

    @property
    def max_age_days(self) -> int:
        """Boards that filter by whole days: 24h -> 1, 36h -> 2."""
        return max(1, -(-self.max_age_hours // 24))

    def pause(self) -> None:
        """Wait a human-like random interval between requests to stay polite. Stops early on Stop."""
        if self.stop_event.wait(random.uniform(*self.delay_range)):
            raise SearchStopped()

    def check_stop(self) -> None:
        if self.stop_event.is_set():
            raise SearchStopped()
