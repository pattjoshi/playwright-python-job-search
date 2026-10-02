"""Remembers jobs across runs (SQLite), so you can see only new ones and mark applied/hidden.

Statuses:
  seen     shown to you in an earlier search
  applied  you clicked "Applied"  -> never shown again
  hidden   you clicked "Hide"     -> never shown again
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from job_search.models import Job

STATUSES = ("seen", "applied", "hidden")
DEFAULT_PATH = Path("data") / "history.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source      TEXT NOT NULL,
    job_id      TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    company     TEXT NOT NULL DEFAULT '',
    url         TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'seen',
    first_seen  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (source, job_id)
)
"""


class JobHistory:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as db:
            db.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        # A fresh connection per call keeps this safe to use from the web server's threads.
        return sqlite3.connect(self.path, timeout=10)

    def statuses(self, jobs: list[Job]) -> dict[tuple[str, str], str]:
        """{(source, job_id): status} for the jobs we already know."""
        if not jobs:
            return {}
        known: dict[tuple[str, str], str] = {}
        with self._lock, self._connect() as db:
            for job in jobs:
                row = db.execute(
                    "SELECT status FROM jobs WHERE source = ? AND job_id = ?", (job.source, job.job_id)
                ).fetchone()
                if row:
                    known[(job.source, job.job_id)] = row[0]
        return known

    def filter(self, jobs: list[Job], only_new: bool) -> list[Job]:
        """Drop applied/hidden jobs always, and earlier-seen jobs when only_new. Marks job.is_new."""
        known = self.statuses(jobs)
        kept = []
        for job in jobs:
            status = known.get((job.source, job.job_id))
            if status in ("applied", "hidden"):
                continue
            if status == "seen" and only_new:
                continue
            job.is_new = status is None
            kept.append(job)
        return kept

    def record_seen(self, jobs: list[Job]) -> None:
        now = _now()
        with self._lock, self._connect() as db:
            db.executemany(
                """INSERT INTO jobs (source, job_id, title, company, url, status, first_seen, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'seen', ?, ?)
                   ON CONFLICT (source, job_id) DO NOTHING""",
                [(j.source, j.job_id, j.title, j.company, j.url, now, now) for j in jobs],
            )

    def set_status(self, source: str, job_id: str, status: str, title: str = "", company: str = "", url: str = "") -> None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        now = _now()
        with self._lock, self._connect() as db:
            db.execute(
                """INSERT INTO jobs (source, job_id, title, company, url, status, first_seen, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (source, job_id) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at""",
                (source, job_id, title, company, url, status, now, now),
            )

    def list_jobs(self, status: str, limit: int = 500) -> list[dict]:
        """Jobs with this status, most recently changed first."""
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        with self._lock, self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                """SELECT source, job_id, title, company, url, status, first_seen, updated_at
                   FROM jobs WHERE status = ? ORDER BY updated_at DESC, rowid DESC LIMIT ?""",
                (status, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
        return {status: 0 for status in STATUSES} | dict(rows)

    def forget_seen(self) -> int:
        """Forget 'seen' jobs (they can show up as new again). Applied and hidden stay."""
        with self._lock, self._connect() as db:
            return db.execute("DELETE FROM jobs WHERE status = 'seen'").rowcount


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
