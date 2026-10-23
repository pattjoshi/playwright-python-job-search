"""Applications in the tracker. Every query is limited to one user's rows (authorization by ownership)."""

from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, func, insert, or_, select, update

from job_search.database import get_engine
from job_search.database.tables import ApplicationEventRecord, ApplicationRecord

FIELDS = (
    "company", "title", "url", "source", "source_job_id", "location", "salary", "status",
    "applied_on", "follow_up_on", "contact", "notes",
)
_COLUMNS = [ApplicationRecord.id, *(getattr(ApplicationRecord, name) for name in FIELDS),
            ApplicationRecord.created_at, ApplicationRecord.updated_at]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ApplicationRepository:
    def __init__(self, path: Path):
        self._engine = get_engine(path)

    def for_user(self, user_id: int, query: str = "", status: str = "") -> list[dict]:
        select_ = select(*_COLUMNS).where(ApplicationRecord.user_id == user_id)
        if status:
            select_ = select_.where(ApplicationRecord.status == status)
        if query:
            like = f"%{query.lower()}%"
            select_ = select_.where(or_(*(func.lower(column).like(like) for column in (
                ApplicationRecord.company, ApplicationRecord.title, ApplicationRecord.location, ApplicationRecord.notes,
            ))))
        with self._engine.connect() as db:
            rows = db.execute(select_.order_by(ApplicationRecord.updated_at.desc(), ApplicationRecord.id.desc()))
            return [dict(row._mapping) for row in rows]

    def get(self, user_id: int, app_id: int) -> dict | None:
        with self._engine.connect() as db:
            row = db.execute(select(*_COLUMNS).where(ApplicationRecord.user_id == user_id, ApplicationRecord.id == app_id)).first()
        return dict(row._mapping) if row else None

    def find_by_job(self, user_id: int, source: str, source_job_id: str) -> dict | None:
        query = select(*_COLUMNS).where(
            ApplicationRecord.user_id == user_id, ApplicationRecord.source == source, ApplicationRecord.source_job_id == source_job_id,
        )
        with self._engine.connect() as db:
            row = db.execute(query).first()
        return dict(row._mapping) if row else None

    def create(self, user_id: int, fields: dict) -> dict:
        now = _now()
        with self._engine.begin() as db:
            app_id = db.execute(insert(ApplicationRecord).values(
                user_id=user_id, created_at=now, updated_at=now, **{k: v for k, v in fields.items() if k in FIELDS},
            )).inserted_primary_key[0]
            db.execute(insert(ApplicationEventRecord).values(
                application_id=app_id, kind="created", to_status=fields.get("status", "saved"), at=now,
            ))
        return self.get(user_id, app_id)

    def update(self, user_id: int, app_id: int, fields: dict) -> dict | None:
        """Save changed fields; a status change is added to the timeline."""
        current = self.get(user_id, app_id)
        if current is None:
            return None
        changes = {k: v for k, v in fields.items() if k in FIELDS and current.get(k) != v}
        if changes:
            now = _now()
            with self._engine.begin() as db:
                db.execute(update(ApplicationRecord).where(ApplicationRecord.id == app_id).values(updated_at=now, **changes))
                if "status" in changes:
                    db.execute(insert(ApplicationEventRecord).values(
                        application_id=app_id, kind="status", from_status=current["status"], to_status=changes["status"], at=now,
                    ))
        return self.get(user_id, app_id)

    def delete(self, user_id: int, app_id: int) -> bool:
        with self._engine.begin() as db:
            result = db.execute(delete(ApplicationRecord).where(ApplicationRecord.user_id == user_id, ApplicationRecord.id == app_id))
        return result.rowcount > 0

    def events(self, user_id: int, app_id: int) -> list[dict]:
        event = ApplicationEventRecord
        query = (
            select(event.kind, event.from_status, event.to_status, event.at)
            .join(ApplicationRecord, ApplicationRecord.id == ApplicationEventRecord.application_id)
            .where(ApplicationRecord.user_id == user_id, ApplicationRecord.id == app_id)
            .order_by(ApplicationEventRecord.id.desc())
        )
        with self._engine.connect() as db:
            return [dict(row._mapping) for row in db.execute(query)]

    def stats(self, user_id: int, today: date, days: int = 14) -> dict:
        """Counts per status, applications per day (last `days` days) and upcoming follow-ups."""
        mine = ApplicationRecord.user_id == user_id
        start = (today - timedelta(days=days - 1)).isoformat()
        with self._engine.connect() as db:
            by_status = dict(db.execute(
                select(ApplicationRecord.status, func.count()).where(mine).group_by(ApplicationRecord.status)
            ).all())
            per_day = dict(db.execute(
                select(ApplicationRecord.applied_on, func.count()).where(mine, ApplicationRecord.applied_on >= start)
                .group_by(ApplicationRecord.applied_on)
            ).all())
            follow_ups = db.execute(
                select(*_COLUMNS).where(mine, ApplicationRecord.follow_up_on.is_not(None),
                                        ApplicationRecord.status.not_in(("offer", "rejected", "withdrawn")))
                .order_by(ApplicationRecord.follow_up_on).limit(5)
            ).all()
        dates = [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]
        return {
            "by_status": by_status,
            "total": sum(by_status.values()),
            "per_day": [{"date": day, "count": per_day.get(day, 0)} for day in dates],
            "follow_ups": [dict(row._mapping) for row in follow_ups],
        }
