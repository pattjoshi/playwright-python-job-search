"""Database access.

- The app database (data/history.sqlite3) uses SQLAlchemy models (tables.py) with Alembic migrations
  (migrations/), applied automatically by get_engine().
- The cache (data/cache.sqlite3) is disposable and keeps using the small raw-SQLite helper `Database`.
"""

from job_search.database.base import Base
from job_search.database.connection import Database
from job_search.database.engine import get_engine

__all__ = ["Base", "Database", "get_engine"]
