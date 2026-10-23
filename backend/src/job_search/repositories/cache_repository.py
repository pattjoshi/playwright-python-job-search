"""Local cache (SQLite) so repeat and daily runs skip work they've already done.

  job_details   job pages already opened (description, company apply link) -> not opened again
  scores        AI scores for a job + this resume profile + model + prompt -> not scored again
  profiles      AI reading of a resume file (by content hash) + model -> not sent again

Everything here is safe to delete at any time; it's rebuilt on the next run.
Old rows are removed by cleanup (KEEP_DAYS).
"""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from job_search.database import Database
from job_search.models import Job, Profile

_SCHEMA = """
DROP TABLE IF EXISTS descriptions;  -- replaced by job_details (it had no apply link); the cache is disposable
CREATE TABLE IF NOT EXISTS job_details (
    source TEXT NOT NULL, job_id TEXT NOT NULL,
    description TEXT NOT NULL, experience TEXT NOT NULL DEFAULT '', apply_url TEXT NOT NULL DEFAULT '',
    saved_at TEXT NOT NULL,
    PRIMARY KEY (source, job_id)
);
CREATE TABLE IF NOT EXISTS scores (
    source TEXT NOT NULL, job_id TEXT NOT NULL, profile_key TEXT NOT NULL,
    score INTEGER, reason TEXT NOT NULL, matched TEXT NOT NULL, missing TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (source, job_id, profile_key)
);
CREATE TABLE IF NOT EXISTS profiles (
    resume_key TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
"""


class CacheRepository:
    def __init__(self, path: Path):
        self._db = Database(path, _SCHEMA)

    @property
    def path(self) -> Path:
        return self._db.path

    # ---------- job descriptions ----------

    def fill_descriptions(self, jobs: list[Job]) -> list[Job]:
        """Fill descriptions we already have. Returns the jobs that still need fetching."""
        missing = []
        with self._db.lock, self._db.connect() as db:
            for job in jobs:
                row = db.execute(
                    "SELECT description, experience, apply_url FROM job_details WHERE source = ? AND job_id = ?",
                    (job.source, job.job_id),
                ).fetchone()
                if row:
                    job.description = row[0]
                    job.experience = job.experience or row[1]
                    job.apply_url = job.apply_url or row[2]
                else:
                    missing.append(job)
        return missing

    def save_descriptions(self, jobs: list[Job]) -> None:
        rows = [(j.source, j.job_id, j.description, j.experience, j.apply_url, _now()) for j in jobs if j.description]
        with self._db.lock, self._db.connect() as db:
            db.executemany("INSERT OR REPLACE INTO job_details VALUES (?, ?, ?, ?, ?, ?)", rows)

    # ---------- AI scores ----------

    def fill_scores(self, jobs: list[Job], profile_key: str) -> list[Job]:
        """Fill scores we already have for this profile. Returns the jobs that still need scoring."""
        missing = []
        with self._db.lock, self._db.connect() as db:
            for job in jobs:
                row = db.execute(
                    "SELECT score, reason, matched, missing FROM scores WHERE source = ? AND job_id = ? AND profile_key = ?",
                    (job.source, job.job_id, profile_key),
                ).fetchone()
                if row:
                    job.score, job.match_reason = row[0], row[1]
                    job.matched_skills, job.missing_skills = json.loads(row[2]), json.loads(row[3])
                else:
                    missing.append(job)
        return missing

    def save_scores(self, jobs: list[Job], profile_key: str) -> None:
        rows = [
            (j.source, j.job_id, profile_key, j.score, j.match_reason, json.dumps(j.matched_skills), json.dumps(j.missing_skills), _now())
            for j in jobs
            if j.score is not None  # a failed batch isn't cached, so it's retried next time
        ]
        with self._db.lock, self._db.connect() as db:
            db.executemany("INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

    # ---------- resume profiles ----------

    def get_profile(self, resume_key: str) -> Profile | None:
        with self._db.lock, self._db.connect() as db:
            row = db.execute("SELECT profile FROM profiles WHERE resume_key = ?", (resume_key,)).fetchone()
        return Profile(**json.loads(row[0])) if row else None

    def save_profile(self, resume_key: str, profile: Profile) -> None:
        with self._db.lock, self._db.connect() as db:
            db.execute("INSERT OR REPLACE INTO profiles VALUES (?, ?, ?)", (resume_key, json.dumps(asdict(profile)), _now()))

    # ---------- housekeeping ----------

    def delete_older_than(self, days: int) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        removed = 0
        with self._db.lock, self._db.connect() as db:
            for table in ("job_details", "scores", "profiles"):
                removed += db.execute(f"DELETE FROM {table} WHERE saved_at < ?", (cutoff,)).rowcount
        return removed


def resume_key(path: Path, model: str) -> str:
    """Same file content + same model -> same key, whatever the file is called."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"{model}:{digest}"


def profile_key(profile: Profile, experience: tuple[int, int] | None, model: str, prompt: str) -> str:
    """Changes whenever anything that affects a score changes (resume, wanted experience, model, prompt)."""
    payload = json.dumps(
        {"profile": asdict(profile), "experience": experience, "model": model, "prompt": prompt},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
