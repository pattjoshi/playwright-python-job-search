"""Tables of the app database (data/history.sqlite3). Change them only together with a migration.

Create a migration after editing this file:  cd backend && alembic revision --autogenerate -m "what changed"
"""

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from job_search.database.base import Base


class JobRecord(Base):
    """A job you were shown (seen), applied to or hid. Never deleted automatically."""

    __tablename__ = "jobs"

    source: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    company: Mapped[str] = mapped_column(Text, default="", server_default="")
    url: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(Text, default="seen", server_default="seen")  # seen | applied | hidden
    first_seen: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)


class RunRecord(Base):
    """One search (web, daily or command line) with its settings, funnel, timings, tokens and cost."""

    __tablename__ = "runs"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)  # web | daily | cli
    status: Mapped[str] = mapped_column(Text)  # done | stopped | error
    data: Mapped[str] = mapped_column(Text)  # JSON


class UserRecord(Base):
    """An account that can sign in. The first one is created on first run and is the owner."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text, default="", server_default="")
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, default="owner", server_default="owner")  # owner | member
    created_at: Mapped[str] = mapped_column(Text)


class AuthSessionRecord(Base):
    """A signed-in browser. Only a hash of the cookie's token is stored, so a copied database can't sign in."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(Text)
