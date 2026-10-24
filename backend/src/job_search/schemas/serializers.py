"""Turns domain objects into the plain dicts the frontend expects."""

import math
from pathlib import Path

from job_search.models import Job, Profile
from job_search.models.search import SearchResult
from job_search.services.location_service import normalize_location
from job_search.services.reporting import SITE_NAMES


def suggest_experience(years: float | None) -> list[int] | None:
    """A sensible starting range around the resume's experience: 4 years -> [3, 5]."""
    if years is None or years < 0:
        return None
    return [max(0, math.floor(years) - 1), min(50, math.ceil(years) + 1)]


def resume_to_dict(resume_id: str, file_name: str, profile: Profile, suggested_experience) -> dict:
    locations = []
    for location in profile.locations:
        city = normalize_location(location)
        if city and city not in locations:
            locations.append(city)
    return {
        "resume_id": resume_id,
        "file_name": file_name,
        "profile": profile_to_dict(profile, profile.search_queries or profile.target_titles, locations),
        "suggested_experience": suggested_experience,
    }


def profile_to_dict(profile: Profile, queries: list[str], locations: list[str]) -> dict:
    return {
        "summary": profile.summary,
        "current_title": profile.current_title,
        "skills": profile.skills,
        "years_experience": profile.years_experience,
        "keywords": queries,
        "locations": locations,
    }


MAX_DESCRIPTION = 6000  # characters of a job description sent to the page (details panel)


def job_to_dict(job: Job) -> dict:
    return {
        "source": job.source,
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "posted_text": job.posted_text,
        "experience": job.experience,
        "is_new": job.is_new,
        "score": job.score,
        "match_reason": job.match_reason,
        "matched_skills": job.matched_skills,
        "missing_skills": job.missing_skills,
        "apply_url": job.apply_url,
        "hours_ago": None if job.hours_ago is None else round(job.hours_ago, 1),
        "description": job.description[:MAX_DESCRIPTION],
    }


def result_to_dict(result: SearchResult, output_dir: Path) -> dict:
    def report_url(path: Path) -> str:
        return f"/reports/{path.resolve().relative_to(output_dir.resolve()).as_posix()}"

    stats = result.stats
    return {
        "sites": [
            {"id": site, "name": SITE_NAMES.get(site, site.title()), "jobs": [job_to_dict(job) for job in jobs]}
            for site, jobs in result.top_by_site.items()
        ],
        "scored": len(result.jobs),
        "stats": {
            "duration_s": stats.duration_s,
            "ai_calls": stats.usage.calls,
            "tokens": stats.usage.input_tokens + stats.usage.output_tokens,
            "cached_tokens": stats.usage.cached_tokens,
            "cost_usd": stats.cost_usd,
            "scores_reused": stats.scores_reused,
            "descriptions_reused": stats.descriptions_reused,
        },
        "html_report": report_url(result.html_path),
        "excel_report": report_url(result.xlsx_path),
    }
