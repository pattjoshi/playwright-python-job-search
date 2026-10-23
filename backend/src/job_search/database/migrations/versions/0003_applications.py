"""Application tracker: applications and their timeline.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), server_default="", nullable=False),
        sa.Column("source", sa.Text(), server_default="manual", nullable=False),
        sa.Column("source_job_id", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), server_default="", nullable=False),
        sa.Column("salary", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.Text(), server_default="saved", nullable=False),
        sa.Column("applied_on", sa.Text(), nullable=True),
        sa.Column("follow_up_on", sa.Text(), nullable=True),
        sa.Column("contact", sa.Text(), server_default="", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_applications_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("user_id", "source", "source_job_id", name=op.f("uq_applications_user_id")),
    )
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)
    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=True),
        sa.Column("at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["applications.id"],
            name=op.f("fk_application_events_application_id_applications"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_events")),
    )
    op.create_index(op.f("ix_application_events_application_id"), "application_events", ["application_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_application_events_application_id"), table_name="application_events")
    op.drop_table("application_events")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_table("applications")
