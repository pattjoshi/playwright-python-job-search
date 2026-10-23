"""Indeed job search (no login needed), India site by default.

Indeed protects its pages with bot checks more than the other boards. If one
appears and the browser is visible (--show-browser / "Show browser" in the UI),
you can solve it and the search continues; otherwise Indeed is skipped.
"""

import logging
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from job_search.models import Job
from job_search.services.matching_service import parse_relative_age
from job_search.services.scraping.apply_links import external_apply_url
from job_search.services.scraping.base import BaseScraper

log = logging.getLogger(__name__)

BASE_URL = "https://in.indeed.com"
PAGE_STEP = 10  # Indeed's "start" parameter moves in steps of 10

CARD = "div.job_seen_beacon, div.cardOutline"
TITLE_LINK = "h2.jobTitle a, a.jcs-JobTitle, a[data-jk]"
TITLE = "h2.jobTitle span[title], h2.jobTitle span, h2.jobTitle"
COMPANY = "[data-testid='company-name'], span.companyName"
LOCATION = "[data-testid='text-location'], div.companyLocation"
POSTED = "[data-testid='myJobsStateDate'], span.date"
SNIPPET = "[data-testid='belowJobSnippet'], div.job-snippet, .underShelfFooter"
DESCRIPTION = "#jobDescriptionText"
# "Apply on company site" (jobs applied to on Indeed itself have a button without a link)
APPLY_LINK = "#applyButtonLinkContainer a[href]"
BOT_CHECK_TITLES = ("just a moment", "security check", "verify", "blocked")


class IndeedScraper(BaseScraper):
    name = "indeed"

    def search(self, query: str, location: str) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for page_number in range(self.max_pages):
            self.check_stop()
            params = {
                "q": query,
                "l": location,  # Indeed understands "Remote" as a location
                "fromage": self.max_age_days,  # posted within N days
                "sort": "date",
                "start": page_number * PAGE_STEP,
            }
            url = f"{BASE_URL}/jobs?{urlencode(params)}"
            log.info("Indeed: %r in %r, page %d", query, location, page_number + 1)

            if self.goto(url) is None:
                log.warning("Indeed: couldn't load results; keeping %d jobs found so far", len(jobs))
                break
            if not self._wait_for_results():
                break

            new_jobs = [job for job in parse_search_results(self.page) if job.job_id not in seen]
            if not new_jobs:
                break
            seen.update(job.job_id for job in new_jobs)
            jobs.extend(new_jobs)
            self.pause()
        return jobs

    def fetch_description(self, job: Job) -> None:
        try:
            if self.goto(job.url) is None:
                raise PlaywrightError("page did not load")
            description = self.page.locator(DESCRIPTION).first
            description.wait_for(timeout=10_000)
            job.description = description.inner_text().strip()
            apply_link = self.page.locator(APPLY_LINK).first
            if apply_link.count():
                job.apply_url = external_apply_url(apply_link.get_attribute("href") or "", BASE_URL, ("indeed.com",))
        except PlaywrightError:
            log.warning("Could not load Indeed job %s", job.job_id)
        self.pause()

    def _wait_for_results(self) -> bool:
        """True once job cards are on the page; False if blocked or there are no results."""
        try:
            self.page.wait_for_selector(CARD, timeout=10_000)
            return True
        except PlaywrightError:
            pass

        title = (self.page.title() or "").lower()
        if not any(word in title for word in BOT_CHECK_TITLES):
            log.info("Indeed: no job cards found")
            return False
        if self.interactive:
            log.warning("Indeed is showing a bot check. Solve it in the browser window (waiting up to 90s)...")
            try:
                self.page.wait_for_selector(CARD, timeout=90_000)
                return True
            except PlaywrightError:
                pass
        log.warning("Indeed showed a bot check and was skipped. Run with the browser visible to solve it.")
        return False


def parse_search_results(page: Page) -> list[Job]:
    jobs = []
    seen: set[str] = set()
    for card in page.locator(CARD).all():
        link = card.locator(TITLE_LINK).first
        if not link.count():
            continue
        job_id = link.get_attribute("data-jk") or ""
        title = _text(card, TITLE) or " ".join(link.inner_text().split())
        # The card selectors can match nested wrappers of the same job.
        if not (job_id and title) or job_id in seen:
            continue
        seen.add(job_id)

        posted_text = _text(card, POSTED).replace("Posted", "").strip()
        jobs.append(
            Job(
                source="indeed",
                job_id=job_id,
                title=title,
                company=_text(card, COMPANY),
                location=_text(card, LOCATION),
                url=f"{BASE_URL}/viewjob?jk={job_id}",
                posted_text=posted_text,
                hours_ago=parse_relative_age(posted_text),
                description=_text(card, SNIPPET),
            )
        )
    return jobs


def _text(card, selector: str) -> str:
    element = card.locator(selector).first
    return " ".join(element.inner_text().split()) if element.count() else ""
