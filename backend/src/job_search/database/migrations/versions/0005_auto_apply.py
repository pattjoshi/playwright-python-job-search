"""Auto-apply: the queue of jobs to apply to (and what happened), and its safety settings.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _text(name: str, default: str | None = None) -> sa.Column:
    return sa.Column(name, sa.Text(), server_default=default, nullable=False)


def upgrade() -> None:
    op.create_table(
        "auto_apply_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        _text("source"), _text("source_job_id"), _text("title"), _text("company"), _text("location", ""),
        _text("job_url"), _text("apply_url"), _text("platform", "other"),
        sa.Column("score", sa.Integer(), nullable=True),
        _text("description", ""), _text("status", "queued"), _text("message", ""), _text("cover_letter", ""),
        _text("answers", "[]"), _text("screenshot", ""),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        _text("created_at"), _text("updated_at"),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_auto_apply_jobs_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auto_apply_jobs")),
        sa.UniqueConstraint("user_id", "apply_url", name=op.f("uq_auto_apply_jobs_user_id")),
    )
    op.create_index(op.f("ix_auto_apply_jobs_user_id"), "auto_apply_jobs", ["user_id"], unique=False)
    op.create_table(
        "auto_apply_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("min_score", sa.Integer(), server_default="75", nullable=False),
        sa.Column("daily_limit", sa.Integer(), server_default="15", nullable=False),
        sa.Column("show_browser", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("run_after_search", sa.Boolean(), server_default="0", nullable=False),
        _text("updated_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_auto_apply_settings_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_auto_apply_settings")),
    )


def downgrade() -> None:
    op.drop_table("auto_apply_settings")
    op.drop_index(op.f("ix_auto_apply_jobs_user_id"), table_name="auto_apply_jobs")
    op.drop_table("auto_apply_jobs")
