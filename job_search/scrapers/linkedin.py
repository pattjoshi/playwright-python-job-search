"""LinkedIn jobs via the public (logged-out) job search pages.

LinkedIn serves logged-out job search results from a "guest" endpoint, so no
login is needed and your personal account is never put at risk. Results are
HTML fragments made of job cards, 10 per page.
"""

import logging
import re
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from job_search.models import Job
from job_search.scrapers.base import BaseScraper
from job_search.utils import parse_relative_age

log = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
PAGE_SIZE = 10

CARD = "div.base-card, div.base-search-card"
TITLE = ".base-search-card__title"
COMPANY = ".base-search-card__subtitle"
LOCATION = ".job-search-card__location"
POSTED = "time"
LINK = "a.base-card__full-link"
DESCRIPTION = ".show-more-less-html__markup, .description__text"


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    def search(self, query: str, location: str) -> list[Job]:
        jobs: list[Job] = []
        for page_number in range(self.max_pages):
            params = {
                "keywords": query,
                "location": location,
                "f_TPR": f"r{self.max_age_hours * 3600}",  # posted within N seconds
                "sortBy": "DD",  # newest first
                "start": page_number * PAGE_SIZE,
            }
            url = f"{SEARCH_URL}?{urlencode(params)}"
            log.info("LinkedIn: %r in %r, page %d", query, location, page_number + 1)

            try:
                response = self.page.goto(url, wait_until="domcontentloaded")
            except PlaywrightError as error:
                # Chromium raises (instead of returning) for some error pages, e.g. an empty 429.
                log.warning("LinkedIn request failed (%s); keeping %d jobs found so far", error.message.splitlines()[0], len(jobs))
                break
            if response is None or not response.ok:
                status = response.status if response else "no response"
                log.warning("LinkedIn returned %s; stopping this search (429 means slow down)", status)
                break

            page_jobs = parse_search_results(self.page)
            jobs.extend(page_jobs)
            if len(page_jobs) < PAGE_SIZE:
                break
            self.pause()
        return jobs

    def fetch_description(self, job: Job) -> None:
        response = self.page.goto(DETAIL_URL.format(job_id=job.job_id), wait_until="domcontentloaded")
        if response is None or not response.ok:
            log.warning("Could not load LinkedIn job %s (%s)", job.job_id, response.status if response else "-")
            return
        description = self.page.locator(DESCRIPTION).first
        if description.count():
            job.description = description.inner_text().strip()
        self.pause()


def parse_search_results(page: Page) -> list[Job]:
    """Read job cards from the currently loaded search results page."""
    jobs = []
    for card in page.locator(CARD).all():
        title = _text(card, TITLE)
        link = card.locator(LINK).first
        url = (link.get_attribute("href") or "").split("?")[0] if link.count() else ""
        job_id = _job_id(card.get_attribute("data-entity-urn") or "", url)
        if not (title and job_id):
            continue

        posted_text = _text(card, POSTED)
        jobs.append(
            Job(
                source="linkedin",
                job_id=job_id,
                title=title,
                company=_text(card, COMPANY),
                location=_text(card, LOCATION),
                url=url or f"https://www.linkedin.com/jobs/view/{job_id}",
                posted_text=posted_text,
                hours_ago=parse_relative_age(posted_text),
            )
        )
    return jobs


def _text(card, selector: str) -> str:
    element = card.locator(selector).first
    return " ".join(element.inner_text().split()) if element.count() else ""


def _job_id(urn: str, url: str) -> str:
    # urn looks like "urn:li:jobPosting:4012345678"; URLs end in "-4012345678".
    match = re.search(r"(\d{6,})$", urn) or re.search(r"(\d{6,})/?$", url)
    return match.group(1) if match else ""
