"""The app database: migrations run automatically, keep old data, and match the table models."""

import os
import sqlite3

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from job_search.database import Base, get_engine
from job_search.database.migrate import alembic_config
from job_search.models import Job
from job_search.repositories import JobHistoryRepository

# The schema version 1 of the app created by hand, before migrations existed.
V1_SCHEMA = """
CREATE TABLE jobs (source TEXT NOT NULL, job_id TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'seen',
    first_seen TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (source, job_id));
CREATE TABLE runs (id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, origin TEXT NOT NULL,
    status TEXT NOT NULL, data TEXT NOT NULL);
"""


# These upgrade a database file from an older version of the app, so they only make sense for SQLite.
sqlite_only = pytest.mark.skipif(bool(os.getenv("TEST_DATABASE_URL")), reason="upgrades a SQLite file")


def head_revision() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(engine) -> str:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def test_new_database_is_created_at_the_latest_version(tmp_path):
    engine = get_engine(tmp_path / "new" / "history.sqlite3")

    assert {"jobs", "runs", "alembic_version"} <= set(inspect(engine).get_table_names())
    assert current_revision(engine) == head_revision()
    assert get_engine(tmp_path / "new" / "history.sqlite3") is engine  # one engine per file


@sqlite_only
def test_database_from_an_older_version_keeps_its_data(tmp_path):
    path = tmp_path / "history.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(V1_SCHEMA)
        db.execute("INSERT INTO jobs VALUES ('naukri', 'n1', 'SDET', 'Infosys', 'https://x', 'applied', '2026-01-01', '2026-01-02')")
        db.execute("INSERT INTO runs (started_at, origin, status, data) VALUES ('2026-01-01T09:00:00', 'daily', 'done', '{\"shown\": 5}')")

    history = JobHistoryRepository(path)

    assert current_revision(get_engine(path)) == head_revision()
    assert history.counts() == {"seen": 0, "applied": 1, "hidden": 0}
    assert history.list_jobs("applied")[0]["company"] == "Infosys"
    assert history.list_runs()[0]["shown"] == 5
    assert history.filter([Job("naukri", "n1", "SDET", "Infosys", "", "")], only_new=False) == []


def test_table_models_match_the_migrations(tmp_path):
    """Fails when tables.py changed without a migration (run: alembic revision --autogenerate)."""
    engine = get_engine(tmp_path / "history.sqlite3")
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert differences == []


@sqlite_only
def test_removed_features_lose_their_tables_and_nothing_else(tmp_path):
    """0008 drops the Auto-apply and Answer Bank tables; the account, applications and notes stay."""
    from alembic import command
    from sqlalchemy import create_engine

    path = tmp_path / "history.sqlite3"
    old = create_engine(f"sqlite:///{path}")
    config = alembic_config()
    with old.begin() as connection:  # a database made by the version that still had them
        config.attributes["connection"] = connection
        command.upgrade(config, "0007")
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users (email, name, password_hash, role, created_at) VALUES ('a@b.c', 'A', 'x', 'owner', 'now')")
        db.execute("INSERT INTO answers (user_id, question, answer, kind, category, status, created_at, updated_at) "
                   "VALUES (1, 'Notice period?', '30 days', 'text', 'other', 'answered', 'now', 'now')")
    old.dispose()

    engine = get_engine(path)
    tables = set(inspect(engine).get_table_names())
    assert not tables & {"answers", "answer_wordings", "auto_apply_jobs", "auto_apply_settings"}
    assert {"users", "applications", "notes", "jobs", "runs"} <= tables
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT email FROM users").scalar() == "a@b.c"

    with engine.begin() as connection:  # and back: the tables return, empty
        config.attributes["connection"] = connection
        command.downgrade(config, "0007")
    assert {"answers", "auto_apply_settings"} <= set(inspect(engine).get_table_names())
