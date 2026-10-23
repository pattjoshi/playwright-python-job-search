"""Brings a database up to date by running its Alembic migrations (done automatically on first use)."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def upgrade(engine: Engine) -> None:
    """Apply any migrations the database doesn't have yet."""
    logging.getLogger("alembic").setLevel(logging.WARNING)  # keep "Running upgrade…" out of the app log
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
