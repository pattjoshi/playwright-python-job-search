"""The job search itself. `run()` is the one entry point; the other names are used by tests and callers."""

from job_search.services.search.pipeline import results_for
from job_search.services.search.profile import read_profile
from job_search.services.search.runner import EventCallback, run
from job_search.services.search.sites import collect_jobs, collect_site, fetch_details

__all__ = ["EventCallback", "collect_jobs", "collect_site", "fetch_details", "read_profile", "results_for", "run"]
