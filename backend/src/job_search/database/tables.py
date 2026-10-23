"""Tables of the app database (data/history.sqlite3). Change them only together with a migration.

Create a migration after editing this file:  cd backend && alembic revision --autogenerate -m "what changed"
"""

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
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


class AnswerRecord(Base):
    """One question in the Answer Bank and your answer to it, used to fill in application forms."""

    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("user_id", "question"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="", server_default="")
    category: Mapped[str] = mapped_column(Text, default="other", server_default="other")
    kind: Mapped[str] = mapped_column(Text, default="text", server_default="text")  # text | number | yes_no | choice
    options: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")  # JSON list: choices a form offered
    # answered | needs_review (an AI draft) | needs_answer (waiting for you)
    status: Mapped[str] = mapped_column(Text, default="needs_answer", server_default="needs_answer")
    source: Mapped[str] = mapped_column(Text, default="you", server_default="you")  # starter | resume | ai_draft | form | you
    asked_by: Mapped[str] = mapped_column(Text, default="", server_default="")  # the job whose form asked it first
    use_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)


class AnswerWordingRecord(Base):
    """Another way a form asked an answer's question ("How soon can you join?" for "Notice period").

    Also remembers every match the AI made, so the same wording is never sent to the AI twice.
    """

    __tablename__ = "answer_wordings"
    __table_args__ = (UniqueConstraint("user_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    answer_id: Mapped[int] = mapped_column(ForeignKey("answers.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(Text)  # normalized: lower case, no punctuation
    text: Mapped[str] = mapped_column(Text)  # as the form wrote it
    created_at: Mapped[str] = mapped_column(Text)


class AutoApplyJobRecord(Base):
    """A job in the auto-apply queue and what happened when it was applied to."""

    __tablename__ = "auto_apply_jobs"
    __table_args__ = (UniqueConstraint("user_id", "apply_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(Text)  # the board it was found on
    source_job_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(Text, default="", server_default="")
    job_url: Mapped[str] = mapped_column(Text)  # the board's job page
    apply_url: Mapped[str] = mapped_column(Text)  # the company's application page
    platform: Mapped[str] = mapped_column(Text, default="other", server_default="other")  # greenhouse | lever | ashby | ...
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")  # for the cover letter
    # queued | running | filled (dry run) | submitted | unconfirmed | needs_answer | blocked | failed
    status: Mapped[str] = mapped_column(Text, default="queued", server_default="queued")
    message: Mapped[str] = mapped_column(Text, default="", server_default="")
    cover_letter: Mapped[str] = mapped_column(Text, default="", server_default="")
    answers: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")  # JSON: what was put in each field
    screenshot: Mapped[str] = mapped_column(Text, default="", server_default="")  # file name in data/auto-apply
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class AutoApplySettingsRecord(Base):
    """How auto-apply behaves for one user (safety limits)."""

    __tablename__ = "auto_apply_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")  # fill forms, never submit
    min_score: Mapped[int] = mapped_column(Integer, default=75, server_default="75")
    daily_limit: Mapped[int] = mapped_column(Integer, default=15, server_default="15")
    show_browser: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    run_after_search: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    updated_at: Mapped[str] = mapped_column(Text)
