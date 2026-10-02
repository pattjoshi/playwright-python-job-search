"""End-to-end flow: resume -> profile -> search boards -> filter -> score -> report."""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from job_search.config import Settings
from job_search.llm import JobMatcherLLM
from job_search.models import Job, Profile
from job_search.report import write_reports
from job_search.resume import read_resume_text
from job_search.scrapers import SCRAPERS, BaseScraper

log = logging.getLogger(__name__)

DEFAULT_LOCATION = "India"


@dataclass
class SearchOptions:
    resume_path: Path
    sites: list[str] = field(default_factory=lambda: list(SCRAPERS))
    location: str | None = None
    keywords: list[str] = field(default_factory=list)
    max_age_hours: int = 24
    max_pages: int = 3
    top_n: int = 40
    use_llm: bool = True
    headless: bool = True
    output_dir: Path = Path("output")


@dataclass
class SearchResult:
    profile: Profile
    jobs: list[Job]
    xlsx_path: Path
    csv_path: Path


def run(options: SearchOptions, settings: Settings) -> SearchResult:
    resume_text = read_resume_text(options.resume_path)
    log.info("Read %d characters from %s", len(resume_text), options.resume_path)

    llm = None
    if options.use_llm:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to .env, or run with --no-llm and --keywords.")
        llm = JobMatcherLLM(settings.openai_api_key, settings.openai_model)
        log.info("Reading resume with %s", settings.openai_model)
        profile = llm.extract_profile(resume_text)
    else:
        profile = Profile(target_titles=list(options.keywords), search_queries=list(options.keywords))

    queries = options.keywords or profile.search_queries[:3] or profile.target_titles[:3]
    if not queries:
        raise ValueError("No search keywords found. Pass them with --keywords.")
    locations = [options.location] if options.location else (profile.locations[:2] or [DEFAULT_LOCATION])
    log.info("Searching %s for %s in %s", ", ".join(options.sites), queries, locations)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=options.headless,
            executable_path=settings.chromium_executable,
        )
        context = browser.new_context(locale="en-US")
        try:
            scrapers = {
                site: SCRAPERS[site](context, max_pages=options.max_pages, max_age_hours=options.max_age_hours)
                for site in options.sites
            }
            jobs = collect_jobs(scrapers, queries, locations)
            jobs = filter_recent(dedupe(jobs), options.max_age_hours)
            log.info("%d unique jobs posted in the last %dh", len(jobs), options.max_age_hours)
            if not jobs:
                log.warning("No jobs found. Try --show-browser to see what the site returns, or broader --keywords.")

            terms = profile.skills + profile.target_titles
            jobs.sort(key=lambda job: keyword_score(job, terms), reverse=True)
            shortlist = jobs[: options.top_n]
            for number, job in enumerate(shortlist, start=1):
                log.info("Fetching details %d/%d: %s at %s", number, len(shortlist), job.title, job.company)
                try:
                    scrapers[job.source].fetch_description(job)
                except PlaywrightError as error:
                    log.warning("Skipping details for %s: %s", job.url, error)
        finally:
            browser.close()

    if llm:
        llm.score_jobs(profile, shortlist)
    else:
        for job in shortlist:
            job.score = keyword_score(job, terms)

    shortlist.sort(key=lambda job: job.score if job.score is not None else -1, reverse=True)
    stem = f"jobs_{datetime.now():%Y%m%d_%H%M}"
    xlsx_path, csv_path = write_reports(shortlist, options.output_dir, stem)
    return SearchResult(profile=profile, jobs=shortlist, xlsx_path=xlsx_path, csv_path=csv_path)


def collect_jobs(scrapers: dict[str, BaseScraper], queries: list[str], locations: list[str]) -> list[Job]:
    jobs: list[Job] = []
    for scraper in scrapers.values():
        for query in queries:
            for location in locations:
                try:
                    found = scraper.search(query, location)
                except PlaywrightError as error:
                    # One board failing (timeout, block) shouldn't kill the whole run.
                    log.warning("%s search %r/%r failed: %s", scraper.name, query, location, error)
                    continue
                log.info("%s: %d jobs for %r in %r", scraper.name, len(found), query, location)
                jobs.extend(found)
                scraper.pause()
    return jobs


def dedupe(jobs: list[Job]) -> list[Job]:
    """Drop repeats of the same posting, and the same role listed on several boards."""
    seen_ids: set[tuple[str, str]] = set()
    seen_keys: set[str] = set()
    unique = []
    for job in jobs:
        job_ref = (job.source, job.job_id)
        if job_ref in seen_ids or job.dedupe_key in seen_keys:
            continue
        seen_ids.add(job_ref)
        seen_keys.add(job.dedupe_key)
        unique.append(job)
    return unique


def filter_recent(jobs: list[Job], max_age_hours: int) -> list[Job]:
    """Keep jobs within the window. Unknown ages are kept: the board's own filter already applied."""
    return [job for job in jobs if job.hours_ago is None or job.hours_ago <= max_age_hours]


def keyword_score(job: Job, terms: list[str]) -> int:
    """Cheap 0-100 relevance: share of the candidate's skills/titles mentioned in the job."""
    terms = [term.lower() for term in terms if term.strip()]
    if not terms:
        return 0
    text = f"{job.title} {job.description}".lower()
    # Whole-word match so "java" doesn't count inside "javascript".
    matched = sum(1 for term in terms if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))
    return round(100 * matched / len(terms))
