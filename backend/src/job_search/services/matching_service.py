"""Parsing and ranking helpers shared by the scrapers and the search service."""

import re

from job_search.models import Job


class SearchStopped(Exception):
    """Raised inside a search when the user pressed Stop."""


_UNIT_HOURS = {
    "second": 1 / 3600,
    "sec": 1 / 3600,
    "minute": 1 / 60,
    "min": 1 / 60,
    "hour": 1,
    "hr": 1,
    "day": 24,
    "week": 24 * 7,
    "month": 24 * 30,
    "year": 24 * 365,
}

_RELATIVE = re.compile(r"(\d+)\+?\s*(second|sec|minute|min|hour|hr|day|week|month|year)s?\b")


def parse_relative_age(text: str) -> float | None:
    """Turn job-board phrases like '3 hours ago' or 'Just posted' into hours.

    Returns None when the text can't be understood, so callers can decide
    whether to keep the job.
    """
    text = (text or "").strip().lower()
    if not text:
        return None
    if any(word in text for word in ("just now", "just posted", "today", "moments ago")):
        return 0.0
    if "few hours" in text:
        return 3.0
    if "yesterday" in text:
        return 24.0

    match = _RELATIVE.search(text)
    if match:
        return int(match.group(1)) * _UNIT_HOURS[match.group(2)]
    return None


_EXPERIENCE_RANGE = re.compile(r"(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)
_EXPERIENCE_MIN = re.compile(
    r"(?:(?:minimum|min\.?|at least)\s*(?:of\s*)?(\d{1,2})\s*\+?\s*(?:years?|yrs?))|(?:(\d{1,2})\s*\+\s*(?:years?|yrs?))",
    re.IGNORECASE,
)
_OPEN_ENDED_MAX = 40


def parse_experience(text: str) -> tuple[int, int] | None:
    """Years of experience a job asks for: '3-6 Yrs' -> (3, 6), '5+ years' -> (5, 40), 'Fresher' -> (0, 1)."""
    text = text or ""
    match = _EXPERIENCE_RANGE.search(text)
    if match:
        low, high = int(match.group(1)), int(match.group(2))
        return (min(low, high), max(low, high))
    match = _EXPERIENCE_MIN.search(text)
    if match:
        return (int(match.group(1) or match.group(2)), _OPEN_ENDED_MAX)
    if re.search(r"\bfreshers?\b", text, re.IGNORECASE):
        return (0, 1)
    return None


def experience_matches(job_range: tuple[int, int] | None, wanted: tuple[int, int] | None) -> bool:
    """True when the ranges overlap, or when either side is unknown (don't drop what we can't judge)."""
    if job_range is None or wanted is None:
        return True
    return job_range[0] <= wanted[1] and job_range[1] >= wanted[0]


def parse_experience_option(text: str) -> tuple[int, int]:
    """'1-2' / '1 to 2' / '3' -> (1, 2) / (1, 2) / (3, 3). Raises ValueError for anything else."""
    numbers = [int(n) for n in re.findall(r"\d+", text or "")]
    if not 1 <= len(numbers) <= 2 or not re.fullmatch(r"\s*\d+\s*(?:(?:-|to)\s*\d+\s*)?", text or ""):
        raise ValueError(f"experience must look like '1-2' or '3', got {text!r}")
    low, high = numbers[0], numbers[-1]
    if low > high:
        low, high = high, low
    if high > 50:
        raise ValueError("experience can be at most 50 years")
    return (low, high)


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


def shortlist_per_site(jobs: list[Job], terms: list[str], limits: dict) -> list[Job]:
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


def search_locations(scraper, locations: list[str]) -> list[str]:
    """Boards that accept several cities in one search get them in small groups (fewer requests, none missed)."""
    from job_search.services.location_service import is_remote  # local import breaks a config <-> matching_service cycle

    size = scraper.cities_per_search
    if size <= 1:
        return locations
    cities = [location for location in locations if not is_remote(location)]
    remote = [location for location in locations if is_remote(location)]
    return [", ".join(cities[i:i + size]) for i in range(0, len(cities), size)] + remote
