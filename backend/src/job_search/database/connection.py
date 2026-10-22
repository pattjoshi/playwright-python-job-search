"""Shared SQLite connection helper used by every repository.

A fresh connection per call (rather than one held open) keeps this safe to use
from the web server's threads; the lock serializes writes against one file.
"""

import sqlite3
import threading
from pathlib import Path


class Database:
    def __init__(self, path: Path, schema: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with self.connect() as db:
            db.executescript(schema)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)
