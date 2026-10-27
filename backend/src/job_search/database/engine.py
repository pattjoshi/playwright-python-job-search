"""One SQLAlchemy engine per database, migrated to the latest schema the first time it's opened.

On your computer the database is a SQLite file (data/history.sqlite3). Online (e.g. on Vercel, where files don't last)
set DATABASE_URL to a Postgres database: every repository then shares that one database, whatever path it was given.
"""

import os
import threading
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.pool import NullPool

from job_search.database.migrate import upgrade

_engines: dict[str, Engine] = {}
_lock = threading.Lock()


def database_url() -> str | None:
    """DATABASE_URL as SQLAlchemy wants it, or None (then each repository uses its SQLite file)."""
    return sqlalchemy_url(os.getenv("DATABASE_URL") or "")


def sqlalchemy_url(url: str) -> str | None:
    """ "postgres://…" as Neon/Supabase show it -> "postgresql+psycopg://…" (the driver this app installs)."""
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url or None


def get_engine(path: Path) -> Engine:
    url = database_url()
    key = url or str(Path(path).resolve())
    with _lock:
        engine = _engines.get(key)
        if engine is None:
            engine = _server_engine(url) if url else sqlite_engine(Path(key))
            upgrade(engine)
            _engines[key] = engine
    return engine


def _server_engine(url: str) -> Engine:
    # Serverless functions come and go: no pool to keep open between requests, and check the link before use.
    return create_engine(url, poolclass=NullPool, pool_pre_ping=True)


def sqlite_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Web requests and search threads share the engine; SQLite waits up to 10 s for a write lock.
    engine = create_engine(URL.create("sqlite", database=str(path)), connect_args={"timeout": 10, "check_same_thread": False})
    event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def _enable_foreign_keys(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
