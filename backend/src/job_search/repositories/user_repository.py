"""Accounts and their signed-in sessions (app database)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, insert, select, update

from job_search.database import get_engine
from job_search.database.tables import AuthSessionRecord, UserRecord


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    role: str
    created_at: str

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"


def _user(row) -> User:
    return User(row.id, row.email, row.name, row.role, row.created_at)


class UserRepository:
    def __init__(self, path: Path):
        self._engine = get_engine(path)

    def count(self) -> int:
        with self._engine.connect() as db:
            return db.execute(select(func.count()).select_from(UserRecord)).scalar_one()

    def create(self, email: str, name: str, password_hash: str, role: str) -> User:
        now = datetime.now().isoformat(timespec="seconds")
        with self._engine.begin() as db:
            user_id = db.execute(insert(UserRecord).values(
                email=email, name=name, password_hash=password_hash, role=role, created_at=now,
            )).inserted_primary_key[0]
        return User(user_id, email, name, role, now)

    def owner_id(self) -> int | None:
        """The owner's id (the account created first), for work that runs without a signed-in page (daily search)."""
        with self._engine.connect() as db:
            return db.execute(select(UserRecord.id).where(UserRecord.role == "owner").order_by(UserRecord.id).limit(1)).scalar()

    def by_id(self, user_id: int) -> User | None:
        with self._engine.connect() as db:
            row = db.execute(select(UserRecord).where(UserRecord.id == user_id)).first()
        return _user(row) if row else None

    def credentials(self, email: str) -> tuple[User, str] | None:
        """The user with this email (any case) and their password hash."""
        with self._engine.connect() as db:
            row = db.execute(select(UserRecord).where(func.lower(UserRecord.email) == email.lower())).first()
        return (_user(row), row.password_hash) if row else None

    def password_hash(self, user_id: int) -> str | None:
        with self._engine.connect() as db:
            return db.execute(select(UserRecord.password_hash).where(UserRecord.id == user_id)).scalar_one_or_none()

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        with self._engine.begin() as db:
            db.execute(update(UserRecord).where(UserRecord.id == user_id).values(password_hash=password_hash))

    # ---- sessions ----

    def add_session(self, token_hash: str, user_id: int, expires_at: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._engine.begin() as db:
            db.execute(insert(AuthSessionRecord).values(token_hash=token_hash, user_id=user_id, created_at=now, expires_at=expires_at))

    def session_user(self, token_hash: str, now: str) -> User | None:
        """The user signed in with this session, if it exists and hasn't expired."""
        query = (
            select(UserRecord).join(AuthSessionRecord, AuthSessionRecord.user_id == UserRecord.id)
            .where(AuthSessionRecord.token_hash == token_hash, AuthSessionRecord.expires_at > now)
        )
        with self._engine.connect() as db:
            row = db.execute(query).first()
        return _user(row) if row else None

    def remove_session(self, token_hash: str) -> None:
        with self._engine.begin() as db:
            db.execute(delete(AuthSessionRecord).where(AuthSessionRecord.token_hash == token_hash))

    def remove_sessions(self, user_id: int, keep: str | None = None) -> None:
        """Sign the user out everywhere (except the session `keep`, if given)."""
        query = delete(AuthSessionRecord).where(AuthSessionRecord.user_id == user_id)
        if keep:
            query = query.where(AuthSessionRecord.token_hash != keep)
        with self._engine.begin() as db:
            db.execute(query)

    def remove_expired_sessions(self, now: str) -> None:
        with self._engine.begin() as db:
            db.execute(delete(AuthSessionRecord).where(AuthSessionRecord.expires_at <= now))
