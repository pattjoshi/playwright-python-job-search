"""Remove auto-apply and the Answer Bank: their tables (and everything saved in them) are dropped.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-27
"""

import importlib.util
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The migrations that created these tables, in order (downgrade runs them again: empty tables).
CREATED_BY = ("0004_answers", "0005_auto_apply", "0006_easy_apply")


def upgrade() -> None:
    op.drop_index(op.f("ix_answer_wordings_answer_id"), table_name="answer_wordings")
    op.drop_table("answer_wordings")
    op.drop_index(op.f("ix_answers_user_id"), table_name="answers")
    op.drop_table("answers")
    op.drop_table("auto_apply_settings")
    op.drop_index(op.f("ix_auto_apply_jobs_user_id"), table_name="auto_apply_jobs")
    op.drop_table("auto_apply_jobs")


def downgrade() -> None:
    for name in CREATED_BY:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.upgrade()
