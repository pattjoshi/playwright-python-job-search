"""The search steps: resume -> profile -> search sites -> filter -> open job pages -> score -> report."""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial

from job_search.config import Settings
from job_search.models import Job, Profile, RunStats, SearchOptions, SearchResult
from job_search.repositories import CacheRepository, JobHistoryRepository, profile_key
from job_search.repositories.search_filters_repository import SearchFiltersRepository
from job_search.services.llm_service import SCORING_PROMPT, JobMatcherLLM
from job_search.services.matching_service import (
    SearchStopped,
    filter_experience,
    keyword_score,
    matched_skills,
    shortlist_per_site,
)
from job_search.services.reporting import write_html_report, write_reports
from job_search.services.resume_service import read_resume_text
from job_search.services.scraping import SCRAPERS, SiteSession
from job_search.services.search.filters import apply_filters
from job_search.services.search.profile import read_profile, resume_locations
from job_search.services.search.sites import Progress, collect_site, fetch_details, on_each_site

log = logging.getLogger(__name__)


def results_for(options: SearchOptions, site: str) -> int:
    """How many jobs to show for a site."""
    return options.results_per_site.get(site, options.results)


@dataclass
class _Run:
    """Everything the steps of one search share."""

    options: SearchOptions
    settings: Settings
    emit: Callable[..., None]
    stop_event: threading.Event
    stats: RunStats
    cache: CacheRepository | None
    history: JobHistoryRepository | None

    def check_stop(self) -> None:
        if self.stop_event.is_set():
            raise SearchStopped()


def run_pipeline(
    options: SearchOptions, settings: Settings, emit: Callable[..., None], stop_event: threading.Event, stats: RunStats
) -> SearchResult:
    options.sites = options.sites or list(SCRAPERS)
    run = _Run(
        options, settings, emit, stop_event, stats,
        cache=CacheRepository(options.cache_path) if options.cache_path else None,
        history=JobHistoryRepository(options.history_path) if options.history_path else None,
    )

    emit("stage", stage="resume")
    llm = _make_llm(run)
    profile = _load_profile(run, llm)
    run.check_stop()

    queries = options.keywords or profile.search_queries[:3] or profile.target_titles[:3]
    if not queries:
        raise ValueError("No search keywords found. Pass them with --keywords.")
    locations = options.locations or resume_locations(profile)
    log.info("Searching %s for %s in %s", ", ".join(options.sites), queries, locations)
    emit("profile", profile=profile, queries=queries, locations=locations)

    terms = profile.skills + profile.target_titles
    shortlist, funnel = _search_and_open(run, queries, locations, terms)

    funnel.append(("checked", len(shortlist)))
    if options.experience:
        before = len(shortlist)
        shortlist = filter_experience(shortlist, options.experience)
        if before != len(shortlist):
            log.info("Skipped %d jobs whose description asks for experience outside %d-%d years",
                     before - len(shortlist), *options.experience)
    funnel.append(("scored", len(shortlist)))
    emit("funnel", steps=list(funnel))

    _score(run, llm, profile, shortlist, terms)
    return _report(run, profile, shortlist)


def _make_llm(run: _Run) -> JobMatcherLLM | None:
    if not run.options.use_llm:
        return None
    if not run.settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to .env, or run with --no-llm and --keywords.")
    llm = JobMatcherLLM(run.settings.openai_api_key, run.settings.openai_model)
    run.stats.usage = getattr(llm, "usage", run.stats.usage)
    return llm


def _load_profile(run: _Run, llm: JobMatcherLLM | None) -> Profile:
    options = run.options
    if options.profile:
        return options.profile
    if llm:
        return read_profile(llm, options.resume_path, run.settings.openai_model, run.cache, run.stats)
    read_resume_text(options.resume_path)  # still fail early on an unreadable file
    return Profile(target_titles=list(options.keywords), search_queries=list(options.keywords))


def _open_sessions(run: _Run) -> dict[str, SiteSession]:
    options, sessions = run.options, {}
    try:
        for site in options.sites:
            run.check_stop()
            make_scraper = partial(
                SCRAPERS[site],
                max_pages=options.max_pages,
                max_age_hours=options.max_age_hours,
                interactive=not options.headless,
                experience=options.experience,
                stop_event=run.stop_event,
            )
            sessions[site] = SiteSession(
                site, make_scraper, headless=options.headless,
                executable_path=run.settings.chromium_executable, block=options.block_assets,
            )
    except BaseException:
        for session in sessions.values():
            session.close()
        raise
    return sessions


def _search_and_open(run: _Run, queries: list[str], locations: list[str], terms: list[str]) -> tuple[list[Job], list]:
    """Search every site, filter the results, then open the shortlisted jobs to read their descriptions."""
    options = run.options
    sessions = _open_sessions(run)
    try:
        run.emit("stage", stage="search")
        if options.parallel_sites and len(sessions) > 1:
            log.info("Searching %d sites at the same time", len(sessions))
        per_site = on_each_site(
            sessions, options.parallel_sites,
            lambda site: partial(collect_site, site=site, queries=queries, locations=locations, emit=run.emit),
        )
        jobs = [job for site in options.sites for job in per_site.get(site, [])]
        saved = SearchFiltersRepository(options.history_path.parent).load() if options.history_path else {}
        jobs, funnel = apply_filters(jobs, options, run.history, run.emit, saved.get("exclude_companies"))

        # Score at least as many jobs as each site will show.
        limits = {site: max(options.top_n, results_for(options, site)) for site in options.sites}
        shortlist = shortlist_per_site(jobs, terms, limits)
        run.emit("stage", stage="details")
        _fetch_descriptions(run, sessions, shortlist)
    finally:
        for session in sessions.values():
            session.close()
    return shortlist, funnel


def _fetch_descriptions(run: _Run, sessions: dict[str, SiteSession], shortlist: list[Job]) -> None:
    # Only jobs without a description need opening (Naukri's come with the search),
    # and only the ones we haven't opened in an earlier run.
    to_fetch = [job for job in shortlist if not job.description]
    if run.cache and to_fetch:
        before = len(to_fetch)
        to_fetch = run.cache.fill_descriptions(to_fetch)
        run.stats.descriptions_reused = before - len(to_fetch)
        if run.stats.descriptions_reused:
            log.info("Reused %d saved job descriptions", run.stats.descriptions_reused)
    skipped = {site for site, session in sessions.items() if session.scraper.unreachable}
    if skipped:
        log.info("Not opening job details on %s (not responding)", ", ".join(sorted(skipped)))
        to_fetch = [job for job in to_fetch if job.source not in skipped]
    progress = Progress(len(to_fetch), lambda done, total: run.emit("progress", stage="details", done=done, total=total))
    by_site = {site: [job for job in to_fetch if job.source == site] for site in sessions}
    on_each_site(
        {site: sessions[site] for site, site_jobs in by_site.items() if site_jobs},
        run.options.parallel_sites,
        lambda site: partial(fetch_details, jobs=by_site[site], progress=progress),
    )
    run.stats.descriptions_fetched = sum(1 for job in to_fetch if job.description)
    if run.cache:
        run.cache.save_descriptions(to_fetch)


def _score(run: _Run, llm: JobMatcherLLM | None, profile: Profile, shortlist: list[Job], terms: list[str]) -> None:
    run.emit("stage", stage="score")
    if llm:
        def score_progress(done: int, total: int) -> None:
            run.check_stop()
            run.emit("progress", stage="score", done=done, total=total)

        options, cache, stats = run.options, run.cache, run.stats
        key = profile_key(profile, options.experience, run.settings.openai_model, SCORING_PROMPT)
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


def _report(run: _Run, profile: Profile, shortlist: list[Job]) -> SearchResult:
    options = run.options
    run.emit("stage", stage="report")
    shortlist.sort(key=lambda job: job.score if job.score is not None else -1, reverse=True)
    top_by_site = {
        site: [job for job in shortlist if job.source == site][: results_for(options, site)] for site in options.sites
    }
    if run.history:
        run.history.record_seen([job for jobs in top_by_site.values() for job in jobs])

    stem = f"jobs_{datetime.now():%Y%m%d_%H%M%S}"
    html_path = options.output_dir / f"{stem}.html"
    write_html_report(profile, top_by_site, html_path, max_age_hours=options.max_age_hours)
    xlsx_path, csv_path = write_reports(shortlist, options.output_dir, stem)
    return SearchResult(profile, shortlist, top_by_site, html_path, xlsx_path, csv_path, stats=run.stats)
