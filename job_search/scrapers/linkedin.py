"""LinkedIn jobs via the public (logged-out) job search pages.

LinkedIn serves logged-out job search results from a "guest" endpoint, so no
login is needed and your personal account is never put at risk. Results are
HTML fragments made of job cards, 10 per page.
"""

import logging
import re
from urllib.parse import urlencode

from playwright.sync_api import Page

from job_search.models import Job
from job_search.locations import is_remote
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
            self.check_stop()
            params = {
                "keywords": query,
                "location": "India" if is_remote(location) else location,
                "f_TPR": f"r{self.max_age_hours * 3600}",  # posted within N seconds
                "sortBy": "DD",  # newest first
                "start": page_number * PAGE_SIZE,
            }
            if is_remote(location):
                params["f_WT"] = "2"  # workplace type: remote
            if self.experience:
                params["f_E"] = ",".join(str(level) for level in experience_levels(*self.experience))
            url = f"{SEARCH_URL}?{urlencode(params)}"
            log.info("LinkedIn: %r in %r, page %d", query, location, page_number + 1)

            response = self.goto(url)
            if response is None or not response.ok:
                status = response.status if response else "no response"
                log.warning("LinkedIn: couldn't load results (%s); keeping %d jobs found so far", status, len(jobs))
                break

            page_jobs = parse_search_results(self.page)
            jobs.extend(page_jobs)
            if len(page_jobs) < PAGE_SIZE:
                break
            self.pause()
        return jobs

    def fetch_description(self, job: Job) -> None:
        response = self.goto(DETAIL_URL.format(job_id=job.job_id))
        if response is None or not response.ok:
            log.warning("Could not load LinkedIn job %s (%s)", job.job_id, response.status if response else "-")
            return
        description = self.page.locator(DESCRIPTION).first
        if description.count():
            job.description = description.inner_text().strip()
        self.pause()


def experience_levels(min_years: int, max_years: int) -> list[int]:
    """LinkedIn's experience filter codes covering a years range.

    1 Internship, 2 Entry level, 3 Associate, 4 Mid-Senior level, 5 Director, 6 Executive.
    """
    bands = [(0, 0, {1, 2}), (1, 2, {2, 3}), (3, 5, {3, 4}), (6, 10, {4}), (11, 14, {4, 5}), (15, 99, {5, 6})]
    levels: set[int] = set()
    for low, high, codes in bands:
        if low <= max_years and high >= min_years:
            levels |= codes
    return sorted(levels)


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
