"""The auto-apply queue and settings. Every query is limited to one user's rows."""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from job_search.database import get_engine
from job_search.database.tables import AutoApplyJobRecord, AutoApplySettingsRecord

DEFAULT_SETTINGS = {"dry_run": True, "min_score": 75, "daily_limit": 15, "show_browser": False, "run_after_search": False}
SETTINGS = tuple(DEFAULT_SETTINGS)
FIELDS = (
    "source", "source_job_id", "title", "company", "location", "job_url", "apply_url", "platform", "score",
    "description", "status", "message", "cover_letter", "answers", "screenshot", "attempts", "finished_at",
)
# Finished attempts that count toward the daily limit (a dry run counts too, so a run always ends).
COUNTED = ("submitted", "unconfirmed", "filled")
_Job = AutoApplyJobRecord
_LIST_COLUMNS = [_Job.id, *(getattr(_Job, name) for name in FIELDS if name != "description"), _Job.created_at, _Job.updated_at]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row(row) -> dict:
    data = dict(row._mapping)
    data["answers"] = json.loads(data.get("answers") or "[]")
    return data


class AutoApplyRepository:
    def __init__(self, path: Path):
        self._engine = get_engine(path)

    # ---------- settings ----------

    def settings(self, user_id: int) -> dict:
        query = select(*(getattr(AutoApplySettingsRecord, name) for name in SETTINGS)).where(AutoApplySettingsRecord.user_id == user_id)
        with self._engine.connect() as db:
            row = db.execute(query).first()
        return dict(row._mapping) if row else dict(DEFAULT_SETTINGS)

    def save_settings(self, user_id: int, values: dict) -> dict:
        values = {**self.settings(user_id), **{k: v for k, v in values.items() if k in SETTINGS}, "updated_at": _now()}
        statement = sqlite_insert(AutoApplySettingsRecord).values(user_id=user_id, **values)
        statement = statement.on_conflict_do_update(index_elements=["user_id"], set_=values)
        with self._engine.begin() as db:
            db.execute(statement)
        return self.settings(user_id)

    # ---------- the queue ----------

    def enqueue(self, user_id: int, items: list[dict]) -> int:
        """Add jobs (each a dict of FIELDS); one already in the queue (same apply link) is left alone."""
        if not items:
            return 0
        now = _now()
        rows = [{"user_id": user_id, "created_at": now, "updated_at": now, "status": "queued",
                 **{k: v for k, v in item.items() if k in FIELDS}} for item in items]
        added = 0
        with self._engine.begin() as db:
            for row in rows:
                statement = sqlite_insert(_Job).values(**row).on_conflict_do_nothing(index_elements=["user_id", "apply_url"])
                added += db.execute(statement).rowcount
        return added

    def for_user(self, user_id: int) -> list[dict]:
        query = select(*_LIST_COLUMNS).where(_Job.user_id == user_id).order_by(_Job.updated_at.desc(), _Job.id.desc())
        with self._engine.connect() as db:
            return [_row(row) for row in db.execute(query)]

    def get(self, user_id: int, job_id: int) -> dict | None:
        query = select(_Job.id, *(getattr(_Job, name) for name in FIELDS), _Job.created_at, _Job.updated_at)
        with self._engine.connect() as db:
            row = db.execute(query.where(_Job.user_id == user_id, _Job.id == job_id)).first()
        return _row(row) if row else None

    def next_queued(self, user_id: int) -> dict | None:
        """The best-matching job still waiting."""
        query = (select(_Job.id).where(_Job.user_id == user_id, _Job.status == "queued")
                 .order_by(_Job.score.desc().nulls_last(), _Job.id).limit(1))
        with self._engine.connect() as db:
            job_id = db.execute(query).scalar()
        return self.get(user_id, job_id) if job_id else None

    def update(self, user_id: int, job_id: int, fields: dict) -> dict | None:
        values = {k: v for k, v in fields.items() if k in FIELDS}
        if "answers" in values:
            values["answers"] = json.dumps(values["answers"])
        with self._engine.begin() as db:
            db.execute(update(_Job).where(_Job.user_id == user_id, _Job.id == job_id).values(updated_at=_now(), **values))
        return self.get(user_id, job_id)

    def delete(self, user_id: int, job_id: int) -> bool:
        with self._engine.begin() as db:
            return db.execute(delete(_Job).where(_Job.user_id == user_id, _Job.id == job_id)).rowcount > 0

    def done_today(self, user_id: int, today: str) -> int:
        """Applications finished today that count toward the daily limit."""
        query = select(func.count()).where(_Job.user_id == user_id, _Job.status.in_(COUNTED), _Job.finished_at.startswith(today))
        with self._engine.connect() as db:
            return db.execute(query).scalar() or 0

    def requeue_interrupted(self) -> None:
        """Jobs left "running" by an app that was closed mid-run go back in the queue."""
        with self._engine.begin() as db:
            db.execute(update(_Job).where(_Job.status == "running").values(status="queued", updated_at=_now()))
