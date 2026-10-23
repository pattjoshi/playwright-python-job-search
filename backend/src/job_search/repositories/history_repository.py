"""Remembers jobs across runs, so you can see only new ones and mark applied/hidden; plus the run history.

Statuses:
  seen     shown to you in an earlier search
  applied  you clicked "Applied"  -> never shown again
  hidden   you clicked "Hide"     -> never shown again
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, insert, literal_column, select, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from job_search.config import DATA_DIR
from job_search.database import get_engine
from job_search.database.tables import JobRecord, RunRecord
from job_search.models import Job

STATUSES = ("seen", "applied", "hidden")
DEFAULT_PATH = DATA_DIR / "history.sqlite3"
MAX_RUNS = 200  # run history keeps the newest runs only
_BATCH = 300  # stay well under SQLite's limit on query parameters

_JOB_COLUMNS = (
    JobRecord.source, JobRecord.job_id, JobRecord.title, JobRecord.company, JobRecord.url,
    JobRecord.status, JobRecord.first_seen, JobRecord.updated_at,
)


class JobHistoryRepository:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self._engine = get_engine(self.path)

    def statuses(self, jobs: list[Job]) -> dict[tuple[str, str], str]:
        """{(source, job_id): status} for the jobs we already know."""
        keys = list({(job.source, job.job_id) for job in jobs})
        known: dict[tuple[str, str], str] = {}
        with self._engine.connect() as db:
            for start in range(0, len(keys), _BATCH):
                query = select(JobRecord.source, JobRecord.job_id, JobRecord.status).where(
                    tuple_(JobRecord.source, JobRecord.job_id).in_(keys[start : start + _BATCH])
                )
                known.update({(source, job_id): status for source, job_id, status in db.execute(query)})
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
        if not jobs:
            return
        now = _now()
        rows = [
            {"source": j.source, "job_id": j.job_id, "title": j.title, "company": j.company, "url": j.url,
             "status": "seen", "first_seen": now, "updated_at": now}
            for j in jobs
        ]
        with self._engine.begin() as db:
            db.execute(sqlite_insert(JobRecord).on_conflict_do_nothing(index_elements=["source", "job_id"]), rows)

    def set_status(self, source: str, job_id: str, status: str, title: str = "", company: str = "", url: str = "") -> None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        now = _now()
        statement = sqlite_insert(JobRecord).values(
            source=source, job_id=job_id, title=title, company=company, url=url, status=status, first_seen=now, updated_at=now,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["source", "job_id"],
            set_={"status": statement.excluded.status, "updated_at": statement.excluded.updated_at},
        )
        with self._engine.begin() as db:
            db.execute(statement)

    def list_jobs(self, status: str, limit: int = 500) -> list[dict]:
        """Jobs with this status, most recently changed first."""
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}")
        query = (
            select(*_JOB_COLUMNS).where(JobRecord.status == status)
            .order_by(JobRecord.updated_at.desc(), literal_column("rowid").desc()).limit(limit)
        )
        with self._engine.connect() as db:
            return [dict(row._mapping) for row in db.execute(query)]

    def record_run(self, started_at: str, origin: str, status: str, data: dict) -> None:
        newest = select(RunRecord.id).order_by(RunRecord.id.desc()).limit(MAX_RUNS)
        with self._engine.begin() as db:
            db.execute(insert(RunRecord).values(
                started_at=started_at, origin=origin, status=status, data=json.dumps(data, default=str),
            ))
            db.execute(delete(RunRecord).where(RunRecord.id.not_in(newest.scalar_subquery())))

    def list_runs(self, limit: int = 50) -> list[dict]:
        """Newest first: {"id", "started_at", "origin", "status", **data}."""
        query = select(RunRecord.id, RunRecord.started_at, RunRecord.origin, RunRecord.status, RunRecord.data)
        with self._engine.connect() as db:
            rows = db.execute(query.order_by(RunRecord.id.desc()).limit(limit)).all()
        return [{"id": r.id, "started_at": r.started_at, "origin": r.origin, "status": r.status, **json.loads(r.data)} for r in rows]

    def counts(self) -> dict[str, int]:
        with self._engine.connect() as db:
            rows = db.execute(select(JobRecord.status, func.count()).group_by(JobRecord.status)).all()
        return {status: 0 for status in STATUSES} | {status: count for status, count in rows}

    def forget_seen(self) -> int:
        """Forget 'seen' jobs (they can show up as new again). Applied and hidden stay."""
        with self._engine.begin() as db:
            return db.execute(delete(JobRecord).where(JobRecord.status == "seen")).rowcount


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
