"""Baseline: the jobs and runs tables.

Databases made by older versions (before migrations) already have these tables; they are kept as they
are, with their data, and only marked as up to date.

Revision ID: 0001
Revises:
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "jobs" not in existing:
        op.create_table(
            "jobs",
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("job_id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), server_default="", nullable=False),
            sa.Column("company", sa.Text(), server_default="", nullable=False),
            sa.Column("url", sa.Text(), server_default="", nullable=False),
            sa.Column("status", sa.Text(), server_default="seen", nullable=False),
            sa.Column("first_seen", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("source", "job_id", name=op.f("pk_jobs")),
        )
    if "runs" not in existing:
        op.create_table(
            "runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.Text(), nullable=False),
            sa.Column("origin", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("data", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
            sqlite_autoincrement=True,
        )


def downgrade() -> None:
    op.drop_table("runs")
    op.drop_table("jobs")
