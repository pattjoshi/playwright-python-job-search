"""Tables of the app database (data/history.sqlite3). Change them only together with a migration.

Create a migration after editing this file:  cd backend && alembic revision --autogenerate -m "what changed"
"""

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
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


class ApplicationRecord(Base):
    """A job in the application tracker (Saved → Applied → … → Offer / Rejected), owned by one user."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "source", "source_job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    company: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, default="", server_default="")
    source: Mapped[str] = mapped_column(Text, default="manual", server_default="manual")  # linkedin | naukri | indeed | manual
    source_job_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # the site's job id, when tracked from a search
    location: Mapped[str] = mapped_column(Text, default="", server_default="")
    salary: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[str] = mapped_column(Text, default="saved", server_default="saved")
    applied_on: Mapped[str | None] = mapped_column(Text, nullable=True)  # YYYY-MM-DD
    follow_up_on: Mapped[str | None] = mapped_column(Text, nullable=True)  # YYYY-MM-DD
    contact: Mapped[str] = mapped_column(Text, default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)


class ApplicationEventRecord(Base):
    """The timeline of an application: when it was added and every status change."""

    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(Text)  # created | status
    from_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[str] = mapped_column(Text)


class NoteRecord(Base):
    """A notes page (Notion-style): a title, an icon and a list of blocks. Pages can sit inside other pages."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    icon: Mapped[str] = mapped_column(Text, default="", server_default="")  # an emoji
    content: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")  # JSON list of blocks
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # order among siblings
    created_at: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)
