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

    @property
    def dedupe_key(self) -> str:
        """Same role posted on several boards should collapse into one row."""
        city = self.location.split(",")[0]  # "Bengaluru, Karnataka, India" on one board is "Bengaluru" on another
        return "|".join((_company(self.company), _title(self.title), _normalize(city)))


_TITLE_WORDS = {"sr": "senior", "jr": "junior", "&": "and", "engg": "engineer", "dev": "developer", "mgr": "manager"}
_COMPANY_SUFFIX = re.compile(r"\b(private|pvt|limited|ltd|llp|inc|corp|corporation|technologies|india)\b")


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _title(text: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", text.lower().replace("&", " & "))  # "(Remote)", "(3-5 yrs)"
    return " ".join(_TITLE_WORDS.get(word, word) for word in re.findall(r"[a-z0-9]+|&", text))


def _company(text: str) -> str:
    return " ".join(_COMPANY_SUFFIX.sub(" ", _normalize(text)).split()) or _normalize(text)
