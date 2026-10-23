"""Notes pages (one user's rows only): the page tree for the sidebar, and each page's blocks."""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, insert, select, update

from job_search.database import get_engine
from job_search.database.tables import NoteRecord

_TREE = (NoteRecord.id, NoteRecord.parent_id, NoteRecord.title, NoteRecord.icon, NoteRecord.position, NoteRecord.updated_at)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class NoteRepository:
    def __init__(self, path: Path):
        self._engine = get_engine(path)

    def tree(self, user_id: int) -> list[dict]:
        """Every page without its blocks, in sidebar order (parents' children by position)."""
        query = select(*_TREE).where(NoteRecord.user_id == user_id).order_by(NoteRecord.position, NoteRecord.id)
        with self._engine.connect() as db:
            return [dict(row._mapping) for row in db.execute(query)]

    def get(self, user_id: int, note_id: int) -> dict | None:
        with self._engine.connect() as db:
            row = db.execute(select(*_TREE, NoteRecord.content, NoteRecord.created_at)
                             .where(NoteRecord.user_id == user_id, NoteRecord.id == note_id)).first()
        if row is None:
            return None
        return {**dict(row._mapping), "content": json.loads(row.content or "[]")}

    def create(self, user_id: int, parent_id: int | None, title: str, icon: str, content: list) -> dict:
        now = _now()
        with self._engine.begin() as db:
            last = db.execute(select(func.max(NoteRecord.position)).where(
                NoteRecord.user_id == user_id, NoteRecord.parent_id.is_(None) if parent_id is None else NoteRecord.parent_id == parent_id,
            )).scalar()
            note_id = db.execute(insert(NoteRecord).values(
                user_id=user_id, parent_id=parent_id, title=title, icon=icon, content=json.dumps(content),
                position=(last if last is not None else -1) + 1, created_at=now, updated_at=now,
            )).inserted_primary_key[0]
        return self.get(user_id, note_id)

    def update(self, user_id: int, note_id: int, fields: dict) -> dict | None:
        values = {k: v for k, v in fields.items() if k in ("title", "icon", "content", "parent_id", "position")}
        if "content" in values:
            values["content"] = json.dumps(values["content"])
        with self._engine.begin() as db:
            db.execute(update(NoteRecord).where(NoteRecord.user_id == user_id, NoteRecord.id == note_id)
                       .values(updated_at=_now(), **values))
        return self.get(user_id, note_id)

    def delete(self, user_id: int, note_id: int) -> bool:
        """Deletes the page and every page inside it."""
        with self._engine.begin() as db:
            return db.execute(delete(NoteRecord).where(NoteRecord.user_id == user_id, NoteRecord.id == note_id)).rowcount > 0
