"""`python -m job_search copy-to-cloud --to <DATABASE_URL>`: copy your data from this computer to the online database.

Copies your account (same email and password), applications with their history, notes, and seen / applied / hidden
jobs with the search history. Run it once, after the online app has been deployed and before you sign up there.
"""

import argparse
import sys

from sqlalchemy import Engine, create_engine, func, insert, select, text, update

from job_search.config import load_settings
from job_search.database import Base
from job_search.database import tables as _tables  # noqa: F401 (registers the table models on Base)
from job_search.database.engine import sqlalchemy_url, sqlite_engine
from job_search.database.migrate import upgrade

# In an order that respects the links between them (users first). Sign-in sessions aren't copied: sign in again.
TABLES = ("users", "applications", "application_events", "notes", "jobs", "runs")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m job_search copy-to-cloud", description=__doc__.splitlines()[0])
    parser.add_argument("--to", required=True, metavar="DATABASE_URL", help="The online database (postgres://…)")
    args = parser.parse_args(argv)
    url = sqlalchemy_url(args.to)
    if not url or not url.startswith("postgresql"):
        print("--to must be a Postgres address (postgres://… from Neon or Supabase).", file=sys.stderr)
        return 2

    source = sqlite_engine(load_settings().history_path)  # always this computer's file, even if DATABASE_URL is set
    upgrade(source)
    target = create_engine(url)
    upgrade(target)
    try:
        counts = copy_data(source, target)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print("Copied: " + ", ".join(f"{count} {name}" for name, count in counts.items()))
    print("Done. Open the online app and sign in with the same email and password.")
    return 0


def copy_data(source: Engine, target: Engine) -> dict[str, int]:
    tables = [Base.metadata.tables[name] for name in TABLES]
    with target.connect() as db:
        if db.execute(select(func.count()).select_from(tables[0])).scalar_one():
            raise ValueError("The online database already has an account: nothing was copied (it would mix two sets of data).")
    counts = {}
    with source.connect() as src, target.begin() as dst:
        for table in tables:
            rows = [dict(row) for row in src.execute(select(table)).mappings()]
            parents = {}
            if table.name == "notes":  # a page can sit inside a page created later: link them after all exist
                parents = {row["id"]: row["parent_id"] for row in rows if row["parent_id"] is not None}
                rows = [{**row, "parent_id": None} for row in rows]
            if rows:
                dst.execute(insert(table), rows)
            for note_id, parent_id in parents.items():
                dst.execute(update(table).where(table.c.id == note_id).values(parent_id=parent_id))
            if "id" in table.c and rows and target.dialect.name == "postgresql":
                # New rows online must get ids after the copied ones.
                dst.execute(text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), (SELECT MAX(id) FROM {table.name}))"))
            counts[table.name] = len(rows)
    return counts
