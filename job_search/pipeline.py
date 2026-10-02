"""End-to-end flow: resume -> profile -> search boards -> filter -> score -> report."""

import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from job_search.config import Settings
from job_search.html_report import write_html_report
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
    top_n: int = 40  # jobs per site to open and score
    results: int = 10  # jobs per site shown in the report...
    results_per_site: dict[str, int] = field(default_factory=dict)  # ...unless set for that site here
    use_llm: bool = True
    headless: bool = True
    output_dir: Path = Path("output")


@dataclass
class SearchResult:
    profile: Profile
    jobs: list[Job]  # every scored job, best first
    top_by_site: dict[str, list[Job]]  # what the HTML report shows
    html_path: Path
    xlsx_path: Path
    csv_path: Path


def results_for(options: SearchOptions, site: str) -> int:
    return options.results_per_site.get(site, options.results)


def run(
    options: SearchOptions,
    settings: Settings,
    on_profile: Callable[[Profile, list[str], list[str]], None] | None = None,
) -> SearchResult:
    """Run a full search. on_profile(profile, queries, locations) fires once the resume is understood."""
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
    if on_profile:
        on_profile(profile, queries, locations)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=options.headless,
            executable_path=settings.chromium_executable,
        )
        context = browser.new_context(locale="en-US")
        try:
            scrapers = {
                site: SCRAPERS[site](
                    context,
                    max_pages=options.max_pages,
                    max_age_hours=options.max_age_hours,
                    interactive=not options.headless,
                )
                for site in options.sites
            }
            jobs = collect_jobs(scrapers, queries, locations)
            jobs = filter_recent(dedupe(jobs), options.max_age_hours)
            log.info("%d unique jobs posted in the last %dh", len(jobs), options.max_age_hours)
            if not jobs:
                log.warning("No jobs found. Try --show-browser to see what the site returns, or broader --keywords.")

            terms = profile.skills + profile.target_titles
            # Score at least as many jobs as each site will show.
            limits = {site: max(options.top_n, results_for(options, site)) for site in options.sites}
            shortlist = shortlist_per_site(jobs, terms, limits)
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
    for job in shortlist:
        if not job.matched_skills:
            job.matched_skills = matched_skills(job, profile.skills)

    shortlist.sort(key=lambda job: job.score if job.score is not None else -1, reverse=True)
    top_by_site = {
        site: [job for job in shortlist if job.source == site][: results_for(options, site)] for site in options.sites
    }

    stem = f"jobs_{datetime.now():%Y%m%d_%H%M}"
    html_path = options.output_dir / f"{stem}.html"
    write_html_report(profile, top_by_site, html_path, max_age_hours=options.max_age_hours)
    xlsx_path, csv_path = write_reports(shortlist, options.output_dir, stem)
    return SearchResult(
        profile=profile,
        jobs=shortlist,
        top_by_site=top_by_site,
        html_path=html_path,
        xlsx_path=xlsx_path,
        csv_path=csv_path,
    )


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


def shortlist_per_site(jobs: list[Job], terms: list[str], limits: Mapping[str, int]) -> list[Job]:
    """Pick each site's most promising jobs (up to limits[site]), so one busy board can't crowd out the others."""
    ranked = sorted(jobs, key=lambda job: keyword_score(job, terms), reverse=True)
    counts: dict[str, int] = {}
    shortlist = []
    for job in ranked:
        if counts.get(job.source, 0) < limits.get(job.source, 0):
            counts[job.source] = counts.get(job.source, 0) + 1
            shortlist.append(job)
    return shortlist


def keyword_score(job: Job, terms: list[str]) -> int:
    """Cheap 0-100 relevance: share of the candidate's skills/titles mentioned in the job."""
    terms = [term for term in terms if term.strip()]
    if not terms:
        return 0
    return round(100 * len(matched_skills(job, terms)) / len(terms))


def matched_skills(job: Job, skills: list[str]) -> list[str]:
    """Skills from the list that the job's title or description mentions."""
    text = f"{job.title} {job.description}".lower()
    # Whole-word match so "java" doesn't count inside "javascript".
    return [
        skill for skill in skills if skill.strip() and re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", text)
    ]
