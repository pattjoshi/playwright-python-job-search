"""Answer Bank: saved answers to application questions and the other wordings of each question.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), server_default="", nullable=False),
        sa.Column("category", sa.Text(), server_default="other", nullable=False),
        sa.Column("kind", sa.Text(), server_default="text", nullable=False),
        sa.Column("options", sa.Text(), server_default="[]", nullable=False),
        sa.Column("status", sa.Text(), server_default="needs_answer", nullable=False),
        sa.Column("source", sa.Text(), server_default="you", nullable=False),
        sa.Column("asked_by", sa.Text(), server_default="", nullable=False),
        sa.Column("use_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_answers_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers")),
        sa.UniqueConstraint("user_id", "question", name=op.f("uq_answers_user_id")),
    )
    op.create_index(op.f("ix_answers_user_id"), "answers", ["user_id"], unique=False)
    op.create_table(
        "answer_wordings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("answer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["answer_id"], ["answers.id"], name=op.f("fk_answer_wordings_answer_id_answers"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_answer_wordings_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answer_wordings")),
        sa.UniqueConstraint("user_id", "key", name=op.f("uq_answer_wordings_user_id")),
    )
    op.create_index(op.f("ix_answer_wordings_answer_id"), "answer_wordings", ["answer_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_answer_wordings_answer_id"), table_name="answer_wordings")
    op.drop_table("answer_wordings")
    op.drop_index(op.f("ix_answers_user_id"), table_name="answers")
    op.drop_table("answers")
