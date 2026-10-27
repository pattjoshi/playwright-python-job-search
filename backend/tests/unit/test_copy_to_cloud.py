"""copy-to-cloud: your local data copied into the online database, once, with ids that keep working."""

import os

import pytest
from sqlalchemy import create_engine, select

from job_search.cli.copy_to_cloud import copy_data
from job_search.database import Base, tables
from job_search.database.engine import sqlite_engine
from job_search.database.migrate import upgrade
from job_search.repositories import ApplicationRepository, NoteRepository, UserRepository


def migrated(engine):
    upgrade(engine)
    return engine


def test_everything_is_copied_once(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    local = tmp_path / "history.sqlite3"
    users = UserRepository(local)
    owner = users.create("om@example.com", "Om", "hash", "owner")
    ApplicationRepository(local).create(owner.id, {"title": "QA", "company": "Acme", "status": "applied", "source": "manual"})
    notes = NoteRepository(local)
    child = notes.create(owner.id, None, "Child", "", [])
    parent = notes.create(owner.id, None, "Parent", "", [])  # created later, then the child moves inside it
    notes.update(owner.id, child["id"], {"parent_id": parent["id"]})

    online = os.getenv("TEST_DATABASE_URL", "").replace("postgresql://", "postgresql+psycopg://", 1)
    target_url = online or f"sqlite:///{tmp_path / 'cloud.sqlite3'}"
    target = migrated(create_engine(target_url))
    counts = copy_data(migrated(sqlite_engine(local)), target)

    assert counts["users"] == 1 and counts["applications"] == 1 and counts["notes"] == 2
    with target.connect() as db:
        assert db.execute(select(tables.UserRecord.email)).scalar_one() == "om@example.com"
        moved = db.execute(select(tables.NoteRecord.parent_id).where(tables.NoteRecord.id == child["id"])).scalar_one()
        assert moved == parent["id"]
    with pytest.raises(ValueError, match="already has an account"):
        copy_data(migrated(sqlite_engine(local)), target)
    assert Base.metadata.tables["notes"] is tables.NoteRecord.__table__
