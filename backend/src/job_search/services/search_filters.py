"""Rules for the saved search filters: hidden companies (matched ignoring "Pvt Ltd", case and punctuation)."""

import re

from job_search.models import Job
from job_search.repositories.search_filters_repository import SearchFiltersRepository

MAX_COMPANIES = 300
_SUFFIXES = re.compile(r"\b(private|pvt|limited|ltd|llp|inc|incorporated|corp|corporation|co|company|technologies|india)\b")


class FilterError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def company_key(name: str) -> str:
    """'Acme Technologies Pvt. Ltd.' and 'ACME' both become 'acme'."""
    words = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    return re.sub(r"\s+", " ", _SUFFIXES.sub(" ", words)).strip() or words.strip()


def without_companies(jobs: list[Job], companies: list[str]) -> list[Job]:
    hidden = {company_key(name) for name in companies}
    return [job for job in jobs if company_key(job.company) not in hidden] if hidden else jobs


def clean_companies(names) -> list[str]:
    if not isinstance(names, list) or len(names) > MAX_COMPANIES:
        raise FilterError(f"Hidden companies must be a list of at most {MAX_COMPANIES} names.")
    seen, kept = set(), []
    for name in names:
        text = str(name or "").strip()[:120]
        if text and company_key(text) not in seen:
            seen.add(company_key(text))
            kept.append(text)
    return kept


class SearchFilterService:
    def __init__(self, repo: SearchFiltersRepository):
        self.repo = repo

    def get(self) -> dict:
        return self.repo.load()

    def save(self, body: dict) -> dict:
        changes = {}
        if "exclude_companies" in body:
            changes["exclude_companies"] = clean_companies(body["exclude_companies"])
        return self.repo.save(changes)

    def hide_company(self, name: str) -> dict:
        name = str(name or "").strip()
        if not name:
            raise FilterError("Which company?")
        return self.save({"exclude_companies": [*self.get()["exclude_companies"], name]})

    def show_company(self, name: str) -> dict:
        key = company_key(name)
        return self.save({"exclude_companies": [c for c in self.get()["exclude_companies"] if company_key(c) != key]})
