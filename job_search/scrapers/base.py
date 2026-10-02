"""Common interface every job-board scraper implements."""

import logging
import random
import threading
from abc import ABC, abstractmethod

from playwright.sync_api import BrowserContext, Page, Response
from playwright.sync_api import Error as PlaywrightError

from job_search.models import Job
from job_search.utils import SearchStopped

log = logging.getLogger(__name__)

# Responses that mean "slow down / try again later".
RETRY_STATUSES = {429, 503}
# After this many page loads in a row fail even with retries, give up on the site for this run.
MAX_FAILED_LOADS = 2


class BaseScraper(ABC):
    #: Short id used on the command line and in reports, e.g. "linkedin".
    name: str = ""
    #: True if one search can cover several cities ("Pune, Bengaluru"), saving requests.
    combine_locations: bool = False
    #: Seconds to wait before each retry of a rate-limited or failed page load.
    retry_delays: tuple[float, ...] = (8.0, 20.0)

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
        self.failed_loads = 0  # consecutive page loads that failed even after retries
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

    @property
    def unreachable(self) -> bool:
        """The site keeps failing (down, blocking us, or no network): stop wasting time on it."""
        return self.failed_loads >= MAX_FAILED_LOADS

    def check_stop(self) -> None:
        if self.stop_event.is_set():
            raise SearchStopped()

    def goto(self, url: str) -> Response | None:
        """Open a page, waiting and retrying when the site rate-limits (429/503) or the load fails.

        Returns the last response (check .ok), or None if the page never loaded.
        """
        response = None
        for attempt, delay in enumerate((0.0, *self.retry_delays)):
            if delay:
                log.info("%s: waiting %.0fs before retry %d", self.name, delay, attempt)
                if self.stop_event.wait(delay):
                    raise SearchStopped()
            try:
                response = self.page.goto(url, wait_until="domcontentloaded")
            except PlaywrightError as error:
                # Chromium raises (instead of returning) for some error pages, e.g. an empty 429.
                log.warning("%s: page failed to load (%s)", self.name, error.message.splitlines()[0])
                response = None
                continue
            if response is not None and response.status in RETRY_STATUSES:
                log.warning("%s: site answered %s (too many requests)", self.name, response.status)
                continue
            self.failed_loads = 0
            return response
        self.failed_loads += 1
        return response
