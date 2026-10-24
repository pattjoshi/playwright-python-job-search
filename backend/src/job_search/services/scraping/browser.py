"""Browsers for the job sites.

Each site gets its own browser running in its own thread, so LinkedIn, Naukri and Indeed
can be searched at the same time. (Playwright's sync API objects only work on the thread
that created them, so every call for a site is run on that site's thread.) Within one
site everything stays sequential and polite.
"""

import logging
import sys
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from playwright.sync_api import Browser, BrowserContext, Playwright, Route, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from job_search.services.scraping.base import BaseScraper

log = logging.getLogger(__name__)

# Never needed to read job listings; skipping them makes every page load faster.
BLOCKED_RESOURCES = {"image", "media", "font"}


# Without this flag Chromium tells every page it is automated (navigator.webdriver), and Naukri answers "Access Denied".
LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled"]
OS_PART = {"win32": "Windows NT 10.0; Win64; x64", "darwin": "Macintosh; Intel Mac OS X 10_15_7"}


def launch(playwright: Playwright, headless: bool, executable_path: str | None) -> Browser:
    """Your installed Google Chrome when there is one (sites trust it more), else Playwright's Chromium."""
    if not executable_path:
        try:
            return playwright.chromium.launch(channel="chrome", headless=headless, args=LAUNCH_ARGS)
        except PlaywrightError:
            log.debug("Google Chrome isn't installed; using Playwright's Chromium")
    return playwright.chromium.launch(headless=headless, executable_path=executable_path, args=LAUNCH_ARGS)


def user_agent(browser: Browser) -> str:
    """A normal Chrome user agent: a hidden browser otherwise says "HeadlessChrome", which sites block on sight."""
    major = browser.version.split(".")[0]
    system = OS_PART.get(sys.platform, "X11; Linux x86_64")
    return f"Mozilla/5.0 ({system}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"


def block_assets(context: BrowserContext, block_styles: bool) -> None:
    """Abort images, fonts and media (and stylesheets if nobody is watching the browser)."""
    blocked = BLOCKED_RESOURCES | ({"stylesheet"} if block_styles else set())

    def handle(route: Route) -> None:
        if route.request.resource_type in blocked:
            route.abort()
        else:
            route.fallback()  # let other handlers (or the network) take it

    context.route("**/*", handle)


class SiteSession:
    """One site's browser + scraper, living on its own thread."""

    def __init__(
        self,
        site: str,
        make_scraper: Callable[[BrowserContext], BaseScraper],
        headless: bool,
        executable_path: str | None = None,
        block: bool = True,
    ):
        self.site = site
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"{site}-browser")
        self._playwright = None
        self._browser = None
        try:
            self.scraper: BaseScraper = self._executor.submit(
                self._open, make_scraper, headless, executable_path, block
            ).result()
        except BaseException:
            self._executor.shutdown(wait=False)
            raise

    def _open(self, make_scraper, headless: bool, executable_path: str | None, block: bool) -> BaseScraper:
        self._playwright = sync_playwright().start()
        try:
            self._browser = launch(self._playwright, headless, executable_path)
            context = self._browser.new_context(locale="en-US", user_agent=user_agent(self._browser))
            if block:
                block_assets(context, block_styles=headless)
            return make_scraper(context)
        except BaseException:
            self._close()
            raise

    def submit(self, fn: Callable[..., object], *args) -> Future:
        """Run fn(scraper, *args) on this site's thread."""
        return self._executor.submit(fn, self.scraper, *args)

    def _close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            if self._playwright is not None:
                self._playwright.stop()
            self._browser = self._playwright = None

    def close(self) -> None:
        try:
            self._executor.submit(self._close).result(timeout=30)
        except Exception as error:  # closing must never hide the real result
            log.debug("Closing the %s browser failed: %s", self.site, error)
        finally:
            self._executor.shutdown(wait=False)
