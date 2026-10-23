"""Application tracker rules: what a valid application looks like, and adding jobs from searches."""

import re
from datetime import date

from job_search.repositories.application_repository import ApplicationRepository

STATUSES = ("saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn")
SOURCES = ("linkedin", "naukri", "indeed", "manual", "other")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LIMITS = {"company": 200, "title": 300, "url": 1000, "location": 200, "salary": 100, "contact": 300, "notes": 5000}


class ApplicationError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def clean(fields: dict, creating: bool) -> dict:
    """Validated, trimmed fields. Raises ApplicationError with a friendly message."""
    cleaned: dict = {}
    for name, limit in _LIMITS.items():
        if name in fields:
            text = str(fields[name] or "").strip()
            if len(text) > limit:
                raise ApplicationError(f"{name.capitalize()} is too long (at most {limit} characters).")
            cleaned[name] = text
    for name in ("company", "title"):
        if (creating or name in cleaned) and not cleaned.get(name):
            raise ApplicationError(f"{name.capitalize()} is required.")
    if cleaned.get("url") and not cleaned["url"].startswith(("http://", "https://")):
        raise ApplicationError("The job link must start with http:// or https://")
    if "status" in fields:
        if fields["status"] not in STATUSES:
            raise ApplicationError(f"Status must be one of: {', '.join(STATUSES)}.")
        cleaned["status"] = fields["status"]
    if "source" in fields:
        cleaned["source"] = fields["source"] if fields["source"] in SOURCES else "other"
    if "source_job_id" in fields:
        cleaned["source_job_id"] = str(fields["source_job_id"]).strip()[:200] or None
    for name in ("applied_on", "follow_up_on"):
        if name in fields:
            value = str(fields[name] or "").strip()
            if value and not _DATE.match(value):
                raise ApplicationError(f"{'Applied on' if name == 'applied_on' else 'Follow-up'} must be a date like 2026-10-23.")
            cleaned[name] = value or None
    return cleaned


class ApplicationService:
    def __init__(self, repo: ApplicationRepository, today=date.today):
        self.repo, self.today = repo, today

    def create(self, user_id: int, fields: dict) -> dict:
        cleaned = clean(fields, creating=True)
        cleaned.setdefault("status", "saved")
        return self.repo.create(user_id, self._applied_date(cleaned, None))

    def update(self, user_id: int, app_id: int, fields: dict) -> dict:
        current = self.repo.get(user_id, app_id)
        if current is None:
            raise ApplicationError("That application doesn't exist.", 404)
        return self.repo.update(user_id, app_id, self._applied_date(clean(fields, creating=False), current))

    def track_job(self, user_id: int, job: dict, status: str = "saved") -> tuple[dict, bool]:
        """Add a job from a search (once). Returns (application, created). Moves Saved → Applied if asked."""
        existing = self.repo.find_by_job(user_id, job.get("source", ""), str(job.get("job_id", "")))
        if existing:
            if status == "applied" and existing["status"] == "saved":
                existing = self.update(user_id, existing["id"], {"status": "applied"})
            return existing, False
        fields = {
            "company": job.get("company") or "Unknown company", "title": job.get("title") or "Untitled job",
            "url": job.get("url", ""), "location": job.get("location", ""), "source": job.get("source", "other"),
            "source_job_id": str(job.get("job_id", "")), "status": status,
        }
        return self.create(user_id, fields), True

    def _applied_date(self, fields: dict, current: dict | None) -> dict:
        """Moving to Applied (or later) without a date sets Applied on to today."""
        status = fields.get("status", current["status"] if current else "saved")
        has_date = fields.get("applied_on") or (current or {}).get("applied_on")
        if status not in ("saved", "withdrawn") and not has_date and "applied_on" not in fields:
            fields["applied_on"] = self.today().isoformat()
        return fields
