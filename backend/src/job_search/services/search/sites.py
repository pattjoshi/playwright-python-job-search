"""Work done on each job site's browser: running the searches and opening job pages."""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future

from playwright.sync_api import Error as PlaywrightError

from job_search.models import Job
from job_search.services.matching_service import SearchStopped, search_locations
from job_search.services.scraping import BaseScraper, SiteSession

log = logging.getLogger(__name__)

Emit = Callable[..., None]


def _ignore(*_args, **_kwargs) -> None:
    pass


def on_each_site(
    sessions: dict[str, SiteSession],
    parallel: bool,
    make_task: Callable[[str], Callable[[BaseScraper], object]],
) -> dict[str, object]:
    """Run a task on each site's browser thread (all at once, or one after another).

    A site that fails unexpectedly is logged and skipped; Stop is re-raised once all sites have finished.
    """
    results: dict[str, object] = {}
    stopped = False

    def collect(site: str, future: Future) -> None:
        nonlocal stopped
        try:
            results[site] = future.result()
        except SearchStopped:
            stopped = True
        except Exception:
            log.exception("%s failed; continuing with the other sites", site)

    if parallel:
        futures = {site: session.submit(make_task(site)) for site, session in sessions.items()}
        for site, future in futures.items():
            collect(site, future)
    else:
        for site, session in sessions.items():
            collect(site, session.submit(make_task(site)))
            if stopped:
                break
    if stopped:
        raise SearchStopped()
    return results


class Progress:
    """Thread-safe "done / total" counter for work spread over several site threads."""

    def __init__(self, total: int, report: Callable[[int, int], None]):
        self.total, self.done, self.report = total, 0, report
        self._lock = threading.Lock()

    def tick(self) -> int:
        with self._lock:
            self.done += 1
            done = self.done
        self.report(done - 1, self.total)
        return done


def fetch_details(scraper: BaseScraper, jobs: list[Job], progress: Progress) -> None:
    """Open each job's page on this site's browser to read the full description."""
    for job in jobs:
        scraper.check_stop()
        if scraper.unreachable:
            log.info("%s stopped responding; skipping its remaining job details", scraper.name)
            return
        number = progress.tick()
        log.info("Fetching details %d/%d: %s at %s", number, progress.total, job.title, job.company)
        try:
            scraper.fetch_description(job)
        except PlaywrightError as error:
            log.warning("Skipping details for %s: %s", job.url, error)


def collect_site(
    scraper: BaseScraper, site: str, queries: list[str], locations: list[str], emit: Emit = _ignore
) -> list[Job]:
    """Run every search for one site (on that site's browser thread)."""
    try:
        return _collect_site(scraper, site, queries, locations, emit)
    except SearchStopped:
        raise
    except Exception:
        emit("site", site=site, status="failed", found=0)
        raise


def _collect_site(scraper: BaseScraper, site: str, queries: list[str], locations: list[str], emit: Emit) -> list[Job]:
    jobs: list[Job] = []
    emit("site", site=site, status="running", found=0)
    found_here, failures, searches = 0, 0, 0
    for query, location in [(q, loc) for q in queries for loc in search_locations(scraper, locations)]:
        if scraper.unreachable:
            log.warning("%s isn't responding; skipping its remaining searches this run", scraper.name)
            break
        searches += 1
        try:
            found = scraper.search(query, location)
        except PlaywrightError as error:
            # One board failing (timeout, block) shouldn't kill the whole run.
            log.warning("%s search %r/%r failed: %s", scraper.name, query, location, error)
            failures += 1
            continue
        log.info("%s: %d jobs for %r in %r", scraper.name, len(found), query, location)
        jobs.extend(found)
        found_here += len(found)
        emit("site", site=site, status="running", found=found_here)
        scraper.pause()
    status = "failed" if failures == searches or (scraper.unreachable and not found_here) else "done"
    if scraper.blocked and not found_here:
        status = "blocked"  # the page tells the user to turn on Show browser and solve the check
    emit("site", site=site, status=status, found=found_here)
    return jobs


def collect_jobs(
    scrapers: dict[str, BaseScraper], queries: list[str], locations: list[str], emit: Emit = _ignore
) -> list[Job]:
    """All sites one after another on the current thread (used by tests and simple callers)."""
    jobs: list[Job] = []
    for site, scraper in scrapers.items():
        jobs.extend(collect_site(scraper, site, queries, locations, emit))
    return jobs
