"""A job posting, and matching info filled in once it's scored."""

import re
from dataclasses import dataclass, field


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
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    experience: str = ""  # as the board shows it, e.g. "2-5 Yrs"
    is_new: bool = True  # False if shown in an earlier search
    apply_url: str = ""  # the company's own application page, when the board links to one ("Apply on company site")

    @property
    def dedupe_key(self) -> str:
        """Same role posted on several boards should collapse into one row."""
        return "|".join(_normalize(part) for part in (self.company, self.title, self.location))


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
