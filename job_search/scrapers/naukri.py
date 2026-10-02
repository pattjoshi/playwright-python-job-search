"""Naukri.com job search (no login needed).

The search page loads its results from Naukri's own JSON endpoint. We open the
normal search page in the browser and read that JSON response as it arrives,
which is far more stable than CSS selectors. If the JSON can't be captured we
fall back to reading the job cards from the page.
"""

import logging
import re
import time
from html import unescape
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from job_search.models import Job
from job_search.locations import is_remote
from job_search.scrapers.base import BaseScraper
from job_search.utils import parse_relative_age

log = logging.getLogger(__name__)

BASE_URL = "https://www.naukri.com"
API_PATH = "/jobapi/v3/search"
PAGE_SIZE = 20

CARD = "div.srp-jobtuple-wrapper, article.jobTuple"
TITLE = "a.title"
COMPANY = "a.comp-name, .comp-name"
LOCATION = ".locWdth, .location, .loc"
POSTED = ".job-post-day, .type br + span, .jobTupleFooter span.fleft"
SNIPPET = ".job-desc, .job-description"
EXPERIENCE = ".expwdth, .exp-wrap, .experience"
TAGS = "ul.tags-gt li, ul.tags li"


class NaukriScraper(BaseScraper):
    name = "naukri"
    combine_locations = True  # Naukri searches "Pune, Bengaluru" in one go

    def search(self, query: str, location: str) -> list[Job]:
        jobs: list[Job] = []
        for page_number in range(1, self.max_pages + 1):
            self.check_stop()
            url = search_url(query, location, page_number, self.max_age_days, self.experience)
            log.info("Naukri: %r in %r, page %d", query, location, page_number)

            page_jobs = self._load_page(url)
            if page_jobs is None:
                break
            jobs.extend(page_jobs)
            if len(page_jobs) < PAGE_SIZE:
                break
            self.pause()
        return jobs

    def _load_page(self, url: str) -> list[Job] | None:
        """Jobs on one results page, or None if Naukri blocked us or failed."""
        try:
            with self.page.expect_response(lambda r: API_PATH in r.url, timeout=20_000) as api:
                self.page.goto(url, wait_until="domcontentloaded")
            response = api.value
            if response.ok:
                return parse_api_jobs(response.json())
            log.warning("Naukri search API returned %s; reading the page instead", response.status)
        except PlaywrightError as error:
            log.debug("Naukri API response not captured (%s); reading the page instead", error)

        if self._blocked():
            return None
        try:
            self.page.wait_for_selector(CARD, timeout=10_000)
        except PlaywrightError:
            log.info("Naukri: no job cards on %s", url)
            return []
        return parse_search_results(self.page)

    def _blocked(self) -> bool:
        title = (self.page.title() or "").lower()
        if "access denied" not in title:
            return False
        if self.interactive:
            log.warning("Naukri is showing a bot check. Solve it in the browser window (waiting up to 90s)...")
            try:
                self.page.wait_for_selector(CARD, timeout=90_000)
                return False
            except PlaywrightError:
                pass
        log.warning("Naukri blocked the request (Access Denied). Try again later, or run with the browser visible.")
        return True


def search_url(
    query: str, location: str, page_number: int, days: int, experience: tuple[int, int] | None = None
) -> str:
    # Naukri's own URL shape: /python-developer-jobs-in-bengaluru-2?k=...&l=...&jobAge=1
    remote = is_remote(location)
    cities = [] if remote else [city.strip() for city in location.split(",") if city.strip()]
    path = f"{_slug(query)}-jobs"
    if cities:
        # Several cities: /python-developer-jobs-in-pune-bengaluru?l=Pune, Bengaluru
        path += "-in-" + "-".join(_slug(city) for city in cities)
    if page_number > 1:
        path += f"-{page_number}"
    params: dict[str, str | int] = {"k": query, "jobAge": days}
    if cities:
        params["l"] = ", ".join(cities)
    if remote:
        params["wfhType"] = 2  # work from home / remote
    if experience:
        # Naukri matches jobs whose range includes this many years; the lower end keeps more results.
        params["experience"] = experience[0]
    return f"{BASE_URL}/{path}?{urlencode(params)}"


def parse_api_jobs(data: dict) -> list[Job]:
    jobs = []
    now_ms = time.time() * 1000
    for item in data.get("jobDetails") or []:
        job_id = str(item.get("jobId") or "").strip()
        title = (item.get("title") or "").strip()
        if not (job_id and title):
            continue

        placeholders = {p.get("type"): p.get("label", "") for p in item.get("placeholders") or [] if isinstance(p, dict)}
        posted_text = item.get("footerPlaceholderLabel") or ""
        # Prefer Naukri's own label ("Few Hours Ago"): createdDate is the *original* posting date,
        # so reposted jobs that Naukri's freshness filter rightly returns would look weeks old.
        hours_ago = parse_relative_age(posted_text)
        created = item.get("createdDate")
        if hours_ago is None and isinstance(created, (int, float)) and created > 0:
            hours_ago = (now_ms - created) / 3_600_000

        skills = item.get("tagsAndSkills") or ""
        description = _strip_html(item.get("jobDescription") or "")
        if skills:
            description = f"{description}\nSkills: {skills.replace(',', ', ')}".strip()

        jobs.append(
            Job(
                source="naukri",
                job_id=job_id,
                title=title,
                company=(item.get("companyName") or "").strip(),
                location=placeholders.get("location", ""),
                url=_absolute(item.get("jdURL") or f"/job-listings-{job_id}"),
                posted_text=posted_text,
                hours_ago=hours_ago,
                description=description,
                experience=placeholders.get("experience", ""),
            )
        )
    return jobs


def parse_search_results(page: Page) -> list[Job]:
    """Fallback: read job cards from the rendered search page."""
    jobs = []
    for card in page.locator(CARD).all():
        link = card.locator(TITLE).first
        if not link.count():
            continue
        title = " ".join(link.inner_text().split())
        url = _absolute(link.get_attribute("href") or "")
        job_id = card.get_attribute("data-job-id") or _job_id_from_url(url)
        if not (title and job_id):
            continue

        posted_text = _text(card, POSTED)
        tags = [" ".join(tag.inner_text().split()) for tag in card.locator(TAGS).all()]
        description = _text(card, SNIPPET)
        if tags:
            description = f"{description}\nSkills: {', '.join(tags)}".strip()
        jobs.append(
            Job(
                source="naukri",
                job_id=job_id,
                title=title,
                company=_text(card, COMPANY),
                location=_text(card, LOCATION),
                url=url,
                posted_text=posted_text,
                hours_ago=parse_relative_age(posted_text),
                description=description,
                experience=_text(card, EXPERIENCE),
            )
        )
    return jobs


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _absolute(url: str) -> str:
    return url if url.startswith("http") else f"{BASE_URL}/{url.lstrip('/')}"


def _job_id_from_url(url: str) -> str:
    match = re.search(r"-(\d{6,})(?:\?|$)", url)
    return match.group(1) if match else ""


def _strip_html(html: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _text(card, selector: str) -> str:
    element = card.locator(selector).first
    return " ".join(element.inner_text().split()) if element.count() else ""
