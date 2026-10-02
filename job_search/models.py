"""Data classes shared across the pipeline."""

import re
from dataclasses import dataclass, field


@dataclass
class Profile:
    """What we learned about the candidate from their resume."""

    current_title: str = ""
    target_titles: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    years_experience: float | None = None
    locations: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class Job:
    source: str
    job_id: str
    title: str
    company: str
    location: str
    url: str
    posted_text: str = ""
    hours_ago: float | None = None
    description: str = ""
    score: int | None = None
    match_reason: str = ""

    @property
    def dedupe_key(self) -> str:
        """Same role posted on several boards should collapse into one row."""
        return "|".join(_normalize(part) for part in (self.company, self.title, self.location))


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
