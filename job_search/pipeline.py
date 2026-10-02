"""End-to-end flow: resume -> profile -> search boards -> filter -> score -> report."""

import logging
import re
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from job_search.browser import SiteSession, block_assets  # noqa: F401  (block_assets re-exported)
from job_search.cache import Cache, profile_key, resume_key
from job_search.config import Settings
from job_search.history import JobHistory
from job_search.html_report import write_html_report
from job_search.llm import SCORING_PROMPT, JobMatcherLLM, TokenUsage
from job_search.locations import is_remote, normalize_location
from job_search.models import Job, Profile
from job_search.report import write_reports
from job_search.resume import read_resume_text
from job_search.scrapers import SCRAPERS, BaseScraper
from job_search.utils import SearchStopped, experience_matches, parse_experience

log = logging.getLogger(__name__)

DEFAULT_LOCATION = "India"

# on_event(name, data) lets a UI follow along. Names: "stage", "profile", "site", "progress", "funnel".
EventCallback = Callable[[str, dict], None]


@dataclass
class SearchOptions:
    resume_path: Path
    sites: list[str] = field(default_factory=lambda: list(SCRAPERS))
    locations: list[str] = field(default_factory=list)  # empty = from the resume; may include "Remote"
    keywords: list[str] = field(default_factory=list)
    experience: tuple[int, int] | None = None  # wanted years, e.g. (1, 2)
    max_age_hours: int = 24
    max_pages: int = 3
    top_n: int = 40  # jobs per site to open and score
    results: int = 10  # jobs per site shown in the report...
    results_per_site: dict[str, int] = field(default_factory=dict)  # ...unless set for that site here
    only_new: bool = False  # hide jobs shown in earlier searches
    history_path: Path | None = None  # where seen/applied/hidden jobs and runs are remembered; None = don't
    cache_path: Path | None = None  # saved descriptions/scores/resume readings; None = no cache
    block_assets: bool = True  # skip images/fonts (and styles when the browser is hidden)
    parallel_sites: bool = True  # search the job sites at the same time (one browser each)
    profile: Profile | None = None  # already-extracted resume profile (skips that AI call)
    origin: str = "cli"  # who started the run (web / daily / cli), for the run history
    use_llm: bool = True
    headless: bool = True
    output_dir: Path = Path("output")


@dataclass
class RunStats:
    """How a run went: shown in the UI and saved in the run history."""

    duration_s: float = 0.0
    sites: dict[str, dict] = field(default_factory=dict)  # site -> {"status", "found"}
    funnel: list = field(default_factory=list)  # [(label, count), ...]
    profile_reused: bool = False
    descriptions_reused: int = 0
    descriptions_fetched: int = 0
    scores_reused: int = 0
    scored: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    cost_usd: float | None = None


@dataclass
class SearchResult:
    profile: Profile
    jobs: list[Job]  # every scored job, best first
    top_by_site: dict[str, list[Job]]  # what the HTML report shows
    html_path: Path
    xlsx_path: Path
    csv_path: Path
    stats: RunStats = field(default_factory=RunStats)


def results_for(options: SearchOptions, site: str) -> int:
    return options.results_per_site.get(site, options.results)


def run(
    options: SearchOptions,
    settings: Settings,
    on_event: EventCallback | None = None,
    stop_event: threading.Event | None = None,
) -> SearchResult:
    """Run a full search. Raises SearchStopped if stop_event gets set. Every run is saved in the run history."""
    stop_event = stop_event or threading.Event()
    stats = RunStats()
    started_at = datetime.now().isoformat(timespec="seconds")
    clock = time.monotonic()
    status, error, result = "error", None, None

    def emit(name: str, **data) -> None:
        # Keep a copy for the run history, then pass it on to the UI.
        if name == "site":
            stats.sites[data["site"]] = {"status": data["status"], "found": data["found"]}
        elif name == "funnel":
            stats.funnel = list(data["steps"])
        if on_event:
            on_event(name, data)

    try:
        result = _run(options, settings, emit, stop_event, stats)
        status = "done"
        return result
    except SearchStopped:
        status = "stopped"
        raise
    except Exception as exc:
        error = str(exc) or exc.__class__.__name__
        raise
    finally:
        stats.duration_s = round(time.monotonic() - clock, 1)
        stats.cost_usd = stats.usage.cost_usd(settings.price_input, settings.price_output, settings.price_cached_input)
        log.info(
            "Run %s in %.0fs · AI: %d calls, %d tokens in (%d cached), %d out%s · reused %d scores, %d descriptions",
            status, stats.duration_s, stats.usage.calls, stats.usage.input_tokens, stats.usage.cached_tokens,
            stats.usage.output_tokens, f" · ~${stats.cost_usd:.4f}" if stats.cost_usd is not None else "",
            stats.scores_reused, stats.descriptions_reused,
        )
        if options.history_path:
            _record_run(options, started_at, status, stats, result, error)


def _run(
    options: SearchOptions,
    settings: Settings,
    emit: Callable[..., None],
    stop_event: threading.Event,
    stats: RunStats,
) -> SearchResult:
    def check_stop() -> None:
        if stop_event.is_set():
            raise SearchStopped()

    emit("stage", stage="resume")
    llm = None
    if options.use_llm:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to .env, or run with --no-llm and --keywords.")
        llm = JobMatcherLLM(settings.openai_api_key, settings.openai_model)
        stats.usage = getattr(llm, "usage", stats.usage)
    cache = Cache(options.cache_path) if options.cache_path else None
    if options.profile:
        profile = options.profile
    elif llm:
        profile = read_profile(llm, options.resume_path, settings.openai_model, cache, stats)
    else:
        read_resume_text(options.resume_path)  # still fail early on an unreadable file
        profile = Profile(target_titles=list(options.keywords), search_queries=list(options.keywords))
    check_stop()

    queries = options.keywords or profile.search_queries[:3] or profile.target_titles[:3]
    if not queries:
        raise ValueError("No search keywords found. Pass them with --keywords.")
    locations = options.locations or _resume_locations(profile)
    log.info("Searching %s for %s in %s", ", ".join(options.sites), queries, locations)
    emit("profile", profile=profile, queries=queries, locations=locations)

    history = JobHistory(options.history_path) if options.history_path else None
    sessions: dict[str, SiteSession] = {}
    try:
        for site in options.sites:
            check_stop()
            sessions[site] = SiteSession(
                site,
                partial(
                    SCRAPERS[site],
                    max_pages=options.max_pages,
                    max_age_hours=options.max_age_hours,
                    interactive=not options.headless,
                    experience=options.experience,
                    stop_event=stop_event,
                ),
                headless=options.headless,
                executable_path=settings.chromium_executable,
                block=options.block_assets,
            )
        scrapers = {site: session.scraper for site, session in sessions.items()}

        emit("stage", stage="search")
        if options.parallel_sites and len(sessions) > 1:
            log.info("Searching %d sites at the same time", len(sessions))
        per_site = _on_each_site(
            sessions, options.parallel_sites, lambda site: partial(collect_site, site=site, queries=queries, locations=locations, emit=emit)
        )
        jobs = [job for site in options.sites for job in per_site.get(site, [])]

        # How many jobs survive each step, so a short result list can be explained.
        funnel = [("found", len(jobs))]
        jobs = dedupe(jobs)
        funnel.append(("unique", len(jobs)))
        jobs = filter_recent(jobs, options.max_age_hours)
        funnel.append((f"posted in {options.max_age_hours}h", len(jobs)))
        if history:
            jobs = history.filter(jobs, only_new=options.only_new)
            funnel.append(("new" if options.only_new else "not applied/hidden", len(jobs)))
        if options.experience:
            # Boards that state experience (e.g. Naukri "2-5 Yrs") can be checked before scoring.
            jobs = filter_experience(jobs, options.experience, use_description=False)
            funnel.append((f"match {options.experience[0]}-{options.experience[1]} yrs", len(jobs)))
        log.info("Jobs kept at each step: %s", " → ".join(f"{count} {label}" for label, count in funnel))
        emit("funnel", steps=list(funnel))
        if not jobs:
            log.warning("No jobs left. Try broader keywords, more locations, a wider experience range or a longer time window.")

        terms = profile.skills + profile.target_titles
        # Score at least as many jobs as each site will show.
        limits = {site: max(options.top_n, results_for(options, site)) for site in options.sites}
        shortlist = shortlist_per_site(jobs, terms, limits)

        emit("stage", stage="details")
        # Only jobs without a description need opening (Naukri's come with the search),
        # and only the ones we haven't opened in an earlier run.
        to_fetch = [job for job in shortlist if not job.description]
        if cache and to_fetch:
            before = len(to_fetch)
            to_fetch = cache.fill_descriptions(to_fetch)
            stats.descriptions_reused = before - len(to_fetch)
            if stats.descriptions_reused:
                log.info("Reused %d saved job descriptions", stats.descriptions_reused)
        skipped = {site for site, scraper in scrapers.items() if scraper.unreachable}
        if skipped:
            log.info("Not opening job details on %s (not responding)", ", ".join(sorted(skipped)))
            to_fetch = [job for job in to_fetch if job.source not in skipped]
        progress = _Progress(len(to_fetch), lambda done, total: emit("progress", stage="details", done=done, total=total))
        by_site = {site: [job for job in to_fetch if job.source == site] for site in sessions}
        _on_each_site(
            {site: sessions[site] for site, site_jobs in by_site.items() if site_jobs},
            options.parallel_sites,
            lambda site: partial(fetch_details, jobs=by_site[site], progress=progress),
        )
        stats.descriptions_fetched = sum(1 for job in to_fetch if job.description)
        if cache:
            cache.save_descriptions(to_fetch)
    finally:
        for session in sessions.values():
            session.close()

    funnel.append(("checked", len(shortlist)))
    if options.experience:
        before = len(shortlist)
        shortlist = filter_experience(shortlist, options.experience)
        if before != len(shortlist):
            log.info("Skipped %d jobs whose description asks for experience outside %d-%d years", before - len(shortlist), *options.experience)
    funnel.append(("scored", len(shortlist)))
    emit("funnel", steps=list(funnel))

    emit("stage", stage="score")
    if llm:
        def score_progress(done: int, total: int) -> None:
            check_stop()
            emit("progress", stage="score", done=done, total=total)

        key = profile_key(profile, options.experience, settings.openai_model, SCORING_PROMPT)
        to_score = cache.fill_scores(shortlist, key) if cache else shortlist
        stats.scores_reused = len(shortlist) - len(to_score)
        stats.scored = len(to_score)
        if stats.scores_reused:
            log.info("Reused %d saved scores; scoring %d new jobs", stats.scores_reused, len(to_score))
        llm.score_jobs(profile, to_score, experience=options.experience, progress=score_progress)
        if cache:
            cache.save_scores(to_score, key)
    else:
        for job in shortlist:
            job.score = keyword_score(job, terms)
    for job in shortlist:
        if not job.matched_skills:
            job.matched_skills = matched_skills(job, profile.skills)

    emit("stage", stage="report")
    shortlist.sort(key=lambda job: job.score if job.score is not None else -1, reverse=True)
    top_by_site = {
        site: [job for job in shortlist if job.source == site][: results_for(options, site)] for site in options.sites
    }
    if history:
        history.record_seen([job for jobs in top_by_site.values() for job in jobs])

    stem = f"jobs_{datetime.now():%Y%m%d_%H%M%S}"
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
        stats=stats,
    )


def _on_each_site(
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


class _Progress:
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


def fetch_details(scraper: BaseScraper, jobs: list[Job], progress: _Progress) -> None:
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


def _record_run(options: SearchOptions, started_at: str, status: str, stats: RunStats, result, error) -> None:
    data = {
        "duration_s": stats.duration_s,
        "sites": stats.sites or {site: {"status": "not run", "found": 0} for site in options.sites},
        "requested": {site: results_for(options, site) for site in options.sites},
        "keywords": options.keywords,
        "locations": options.locations,
        "experience": list(options.experience) if options.experience else None,
        "hours": options.max_age_hours,
        "funnel": stats.funnel,
        "shown": sum(len(jobs) for jobs in result.top_by_site.values()) if result else 0,
        "new": sum(1 for jobs in result.top_by_site.values() for job in jobs if job.is_new) if result else 0,
        "report": str(Path(result.html_path).resolve()) if result else None,
        "usage": asdict(stats.usage),
        "cost_usd": stats.cost_usd,
        "scores_reused": stats.scores_reused,
        "descriptions_reused": stats.descriptions_reused,
        "error": error,
    }
    try:
        JobHistory(options.history_path).record_run(started_at, options.origin, status, data)
    except Exception:  # the run history must never break a run
        log.exception("Couldn't save the run history")


def read_profile(
    llm: JobMatcherLLM, resume_path: Path, model: str, cache: Cache | None, stats: RunStats | None = None
) -> Profile:
    """The AI's reading of the resume, reused when the same file was read before."""
    key = resume_key(resume_path, model)
    cached = cache.get_profile(key) if cache else None
    if cached:
        log.info("Reused the saved reading of %s", Path(resume_path).name)
        if stats:
            stats.profile_reused = True
        return cached
    resume_text = read_resume_text(resume_path)
    log.info("Read %d characters from %s", len(resume_text), resume_path)
    log.info("Reading resume with %s", model)
    profile = llm.extract_profile(resume_text)
    if cache:
        cache.save_profile(key, profile)
    return profile


def _resume_locations(profile: Profile) -> list[str]:
    locations: list[str] = []
    for location in profile.locations:
        city = normalize_location(location)
        if city and city not in locations:
            locations.append(city)
    return locations[:2] or [DEFAULT_LOCATION]


def collect_site(
    scraper: BaseScraper,
    site: str,
    queries: list[str],
    locations: list[str],
    emit: Callable[..., None] = lambda *args, **kwargs: None,
) -> list[Job]:
    """Run every search for one site (on that site's browser thread)."""
    try:
        return _collect_site(scraper, site, queries, locations, emit)
    except SearchStopped:
        raise
    except Exception:
        emit("site", site=site, status="failed", found=0)
        raise


def _collect_site(scraper, site, queries, locations, emit) -> list[Job]:
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
    emit("site", site=site, status=status, found=found_here)
    return jobs


def collect_jobs(
    scrapers: dict[str, BaseScraper],
    queries: list[str],
    locations: list[str],
    emit: Callable[..., None] = lambda *args, **kwargs: None,
) -> list[Job]:
    """All sites one after another on the current thread (used by tests and simple callers)."""
    jobs: list[Job] = []
    for site, scraper in scrapers.items():
        jobs.extend(collect_site(scraper, site, queries, locations, emit))
    return jobs


def search_locations(scraper: BaseScraper, locations: list[str]) -> list[str]:
    """Boards that accept several cities in one search get them combined (fewer requests)."""
    if not scraper.combine_locations:
        return locations
    cities = [location for location in locations if not is_remote(location)]
    remote = [location for location in locations if is_remote(location)]
    return ([", ".join(cities)] if cities else []) + remote


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


def filter_experience(jobs: list[Job], wanted: tuple[int, int], use_description: bool = True) -> list[Job]:
    """Drop jobs whose stated experience can't overlap the wanted range. Unknown experience is kept.

    use_description=False only trusts the board's own experience field (before details are fetched).
    """
    kept = []
    for job in jobs:
        job_range = parse_experience(job.experience)
        if job_range is None and use_description:
            job_range = parse_experience(job.description)
        if experience_matches(job_range, wanted):
            kept.append(job)
    return kept


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
