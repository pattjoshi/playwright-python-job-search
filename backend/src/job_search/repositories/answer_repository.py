"""The Answer Bank: questions, your answers, and the other wordings of each question. One user's rows only."""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from job_search.database import get_engine
from job_search.database.tables import AnswerRecord, AnswerWordingRecord

FIELDS = ("question", "answer", "category", "kind", "options", "status", "source", "asked_by")
_COLUMNS = [AnswerRecord.id, *(getattr(AnswerRecord, name) for name in FIELDS),
            AnswerRecord.use_count, AnswerRecord.created_at, AnswerRecord.updated_at]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row(row) -> dict:
    data = dict(row._mapping)
    data["options"] = json.loads(data["options"] or "[]")
    return data


class AnswerRepository:
    def __init__(self, path: Path):
        self._engine = get_engine(path)

    def for_user(self, user_id: int, status: str = "", category: str = "", query: str = "") -> list[dict]:
        """Answers with their other wordings, unanswered and to-review first, then by category and question."""
        select_ = select(*_COLUMNS).where(AnswerRecord.user_id == user_id)
        if status:
            select_ = select_.where(AnswerRecord.status == status)
        if category:
            select_ = select_.where(AnswerRecord.category == category)
        if query:
            like = f"%{query.lower()}%"
            select_ = select_.where(or_(func.lower(AnswerRecord.question).like(like), func.lower(AnswerRecord.answer).like(like)))
        with self._engine.connect() as db:
            rows = [_row(row) for row in db.execute(select_.order_by(AnswerRecord.category, AnswerRecord.id))]
            wordings = self._wordings(db, user_id, [row["id"] for row in rows])
        for row in rows:
            row["wordings"] = [w for w in wordings.get(row["id"], []) if w != row["question"]]
        return rows

    def get(self, user_id: int, answer_id: int) -> dict | None:
        with self._engine.connect() as db:
            row = db.execute(select(*_COLUMNS).where(AnswerRecord.user_id == user_id, AnswerRecord.id == answer_id)).first()
            if row is None:
                return None
            data = _row(row)
            data["wordings"] = [w for w in self._wordings(db, user_id, [answer_id]).get(answer_id, []) if w != data["question"]]
        return data

    def find_by_key(self, user_id: int, key: str) -> dict | None:
        """The answer a wording (normalized) belongs to, if any."""
        with self._engine.connect() as db:
            answer_id = db.execute(select(AnswerWordingRecord.answer_id).where(
                AnswerWordingRecord.user_id == user_id, AnswerWordingRecord.key == key,
            )).scalar()
        return self.get(user_id, answer_id) if answer_id else None

    def create(self, user_id: int, fields: dict, wordings: list[tuple[str, str]]) -> dict:
        """Add a question; `wordings` is [(key, text)] and should include the question itself."""
        now = _now()
        values = {k: v for k, v in fields.items() if k in FIELDS}
        values["options"] = json.dumps(values.get("options") or [])
        with self._engine.begin() as db:
            answer_id = db.execute(insert(AnswerRecord).values(
                user_id=user_id, created_at=now, updated_at=now, **values,
            )).inserted_primary_key[0]
            self._insert_wordings(db, user_id, answer_id, wordings, now)
        return self.get(user_id, answer_id)

    def update(self, user_id: int, answer_id: int, fields: dict, wordings: list[tuple[str, str]] | None = None) -> dict | None:
        """Save changed fields. `wordings`, when given, replaces the question's wordings."""
        if self.get(user_id, answer_id) is None:
            return None
        values = {k: v for k, v in fields.items() if k in FIELDS}
        if "options" in values:
            values["options"] = json.dumps(values["options"] or [])
        now = _now()
        with self._engine.begin() as db:
            if values:
                db.execute(update(AnswerRecord).where(AnswerRecord.id == answer_id).values(updated_at=now, **values))
            if wordings is not None:
                db.execute(delete(AnswerWordingRecord).where(AnswerWordingRecord.answer_id == answer_id))
                self._insert_wordings(db, user_id, answer_id, wordings, now)
        return self.get(user_id, answer_id)

    def add_wording(self, user_id: int, answer_id: int, key: str, text: str) -> None:
        with self._engine.begin() as db:
            self._insert_wordings(db, user_id, answer_id, [(key, text)], _now())

    def mark_used(self, answer_id: int) -> None:
        with self._engine.begin() as db:
            db.execute(update(AnswerRecord).where(AnswerRecord.id == answer_id).values(use_count=AnswerRecord.use_count + 1))

    def delete(self, user_id: int, answer_id: int) -> bool:
        with self._engine.begin() as db:
            result = db.execute(delete(AnswerRecord).where(AnswerRecord.user_id == user_id, AnswerRecord.id == answer_id))
        return result.rowcount > 0

    def counts(self, user_id: int) -> dict[str, int]:
        with self._engine.connect() as db:
            rows = db.execute(
                select(AnswerRecord.status, func.count()).where(AnswerRecord.user_id == user_id).group_by(AnswerRecord.status)
            ).all()
        return {"answered": 0, "needs_review": 0, "needs_answer": 0} | dict(rows)

    @staticmethod
    def _wordings(db, user_id: int, answer_ids: list[int]) -> dict[int, list[str]]:
        found: dict[int, list[str]] = {}
        if not answer_ids:
            return found
        query = (
            select(AnswerWordingRecord.answer_id, AnswerWordingRecord.text)
            .where(AnswerWordingRecord.user_id == user_id, AnswerWordingRecord.answer_id.in_(answer_ids))
            .order_by(AnswerWordingRecord.id)
        )
        for answer_id, text in db.execute(query):
            found.setdefault(answer_id, []).append(text)
        return found

    @staticmethod
    def _insert_wordings(db, user_id: int, answer_id: int, wordings: list[tuple[str, str]], now: str) -> None:
        """Add wordings; one a different question already owns stays with that question."""
        rows = [{"user_id": user_id, "answer_id": answer_id, "key": key, "text": text, "created_at": now}
                for key, text in dict(wordings).items() if key]
        if rows:
            db.execute(sqlite_insert(AnswerWordingRecord).on_conflict_do_nothing(index_elements=["user_id", "key"]), rows)
