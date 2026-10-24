"""Filters applied to the jobs found, counting how many survive each step (the "funnel")."""

import logging
from collections.abc import Callable

from job_search.models import Job, SearchOptions
from job_search.repositories import JobHistoryRepository
from job_search.services.matching_service import dedupe, filter_experience, filter_recent
from job_search.services.search_filters import without_companies

log = logging.getLogger(__name__)


def apply_filters(
    jobs: list[Job], options: SearchOptions, history: JobHistoryRepository | None, emit: Callable[..., None],
    exclude_companies: list[str] | None = None,
) -> tuple[list[Job], list]:
    """Return the jobs left and the funnel, so a short result list can be explained."""
    funnel = [("found", len(jobs))]
    jobs = dedupe(jobs)
    funnel.append(("unique", len(jobs)))
    if exclude_companies:
        jobs = without_companies(jobs, exclude_companies)
        funnel.append(("not from hidden companies", len(jobs)))
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
    return jobs, funnel
