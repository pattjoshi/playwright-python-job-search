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

from job_search.models import Job
from job_search.services.location_service import is_remote
from job_search.services.matching_service import parse_relative_age
from job_search.services.scraping.apply_links import external_apply_url
from job_search.services.scraping.base import BaseScraper
from job_search.services.scraping.naukri_cards import BASE_URL, CARD, absolute_url, parse_search_results

log = logging.getLogger(__name__)

API_PATH = re.compile(r"/jobapi/v\d+/search")  # the version number changes now and then
PAGE_SIZE = 20
API_WAIT_S = 20  # seconds to wait for the results to arrive



class NaukriScraper(BaseScraper):
    name = "naukri"
    # Naukri searches "Pune, Bengaluru" in one go, but a long city list returns fewer jobs than the cities do alone.
    cities_per_search = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._warmed = False

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
        self._warm_up()
        captured: list = []

        def on_response(response) -> None:
            if API_PATH.search(response.url):
                captured.append(response)

        self.page.on("response", on_response)
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            # Wait for the page's own search call, but give up at once on the "Access Denied" page.
            deadline = time.monotonic() + API_WAIT_S
            while not captured and time.monotonic() < deadline and not self._denied():
                self.page.wait_for_timeout(250)
        except PlaywrightError as error:
            log.warning("Naukri: page failed to load (%s)", error.message.splitlines()[0])
        finally:
            self.page.remove_listener("response", on_response)

        if captured and captured[0].ok:
            data = captured[0].json()
            jobs = parse_api_jobs(data)
            log.info("Naukri: %d jobs on this page (%s in total)", len(jobs), data.get("noOfJobs", "?"))
            return jobs
        if captured:
            log.warning("Naukri search API returned %s; reading the page instead", captured[0].status)
        if self._blocked():
            return None
        try:
            self.page.wait_for_selector(CARD, timeout=10_000)
        except PlaywrightError:
            log.info("Naukri: no job cards on %s", url)
            return []
        return parse_search_results(self.page)

    def _warm_up(self) -> None:
        """Open the home page once first, like a person would: straight to a search link looks like a bot."""
        if self._warmed:
            return
        self._warmed = True
        try:
            self.page.goto(BASE_URL, wait_until="domcontentloaded")
            self.page.wait_for_timeout(1500)
        except PlaywrightError as error:
            log.debug("Naukri home page didn't load (%s)", error)

    def _denied(self) -> bool:
        try:
            return "access denied" in (self.page.title() or "").lower()
        except PlaywrightError:  # the page is navigating
            return False

    def _blocked(self) -> bool:
        if not self._denied():
            return False
        if self.interactive:
            log.warning("Naukri is showing a bot check. Solve it in the browser window (waiting up to 90s)...")
            try:
                self.page.wait_for_selector(CARD, timeout=90_000)
                return False
            except PlaywrightError:
                pass
        self.blocked = True  # every later search would be refused too: stop this site for this run
        log.warning("Naukri refused the automated browser (Access Denied), so it was skipped this run. "
                    "Turn on Show browser and search again: you can solve the check in the window if it asks.")
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
                url=absolute_url(item.get("jdURL") or f"/job-listings-{job_id}"),
                posted_text=posted_text,
                hours_ago=hours_ago,
                description=description,
                experience=placeholders.get("experience", ""),
                # Set for "Apply on company site" jobs; most Naukri jobs are applied to on Naukri itself.
                apply_url=external_apply_url(str(item.get("applyRedirectUrl") or ""), board_hosts=("naukri.com",)),
            )
        )
    return jobs


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _strip_html(html: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())
