"""One SQLAlchemy engine per database file, migrated to the latest schema the first time it's opened."""

import threading
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event

from job_search.database.migrate import upgrade

_engines: dict[str, Engine] = {}
_lock = threading.Lock()


def get_engine(path: Path) -> Engine:
    key = str(Path(path).resolve())
    with _lock:
        engine = _engines.get(key)
        if engine is None:
            Path(key).parent.mkdir(parents=True, exist_ok=True)
            # Web requests and search threads share the engine; SQLite waits up to 10 s for a write lock.
            engine = create_engine(
                URL.create("sqlite", database=key), connect_args={"timeout": 10, "check_same_thread": False}
            )
            event.listen(engine, "connect", _enable_foreign_keys)
            upgrade(engine)
            _engines[key] = engine
    return engine


def _enable_foreign_keys(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
