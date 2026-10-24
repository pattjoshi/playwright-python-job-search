"""The candidate profile a search runs with: the AI's reading of the resume, and where to search."""

import logging
from pathlib import Path

from job_search.models import Profile, RunStats
from job_search.repositories import CacheRepository, resume_key
from job_search.services.llm_service import JobMatcherLLM
from job_search.services.location_service import normalize_location
from job_search.services.resume_service import read_resume_text

log = logging.getLogger(__name__)

DEFAULT_LOCATION = "India"
MAX_QUERIES = 10  # job titles searched per site: the main one plus its other common names
LONG_QUERY_WORDS = 4  # boards like Naukri want every word to match, so longer phrases find few jobs
PROFILE_VERSION = "titles-v2"  # bump when the resume prompt changes, so saved readings are made again


def read_profile(
    llm: JobMatcherLLM, resume_path: Path, model: str, cache: CacheRepository | None, stats: RunStats | None = None
) -> Profile:
    """The AI's reading of the resume, reused when the same file was read before."""
    key = f"{resume_key(resume_path, model)}:{PROFILE_VERSION}"
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


def resume_locations(profile: Profile) -> list[str]:
    """Up to two cities from the resume, or the whole country when it names none."""
    locations: list[str] = []
    for location in profile.locations:
        city = normalize_location(location)
        if city and city not in locations:
            locations.append(city)
    return locations[:2] or [DEFAULT_LOCATION]


def search_queries(keywords: list[str]) -> list[str]:
    """The keywords to search, without repeats (any case), at most MAX_QUERIES; long phrases get a warning."""
    queries: list[str] = []
    for keyword in keywords:
        query = " ".join(keyword.split())
        if query and query.lower() not in {q.lower() for q in queries}:
            queries.append(query)
    long = [query for query in queries[:MAX_QUERIES] if len(query.split()) > LONG_QUERY_WORDS]
    if long:
        log.warning("Long keywords find few jobs on Naukri (every word must match): %s. "
                    "Short job titles like \"AI Engineer\" work best.", "; ".join(long))
    return queries[:MAX_QUERIES]
