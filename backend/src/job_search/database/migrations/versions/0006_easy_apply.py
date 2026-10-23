"""Easy Apply on the job boards: a switch per board and a per-board daily limit.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BOARDS = ("naukri", "linkedin", "indeed")


def upgrade() -> None:
    with op.batch_alter_table("auto_apply_settings") as table:
        for board in BOARDS:
            table.add_column(sa.Column(board, sa.Boolean(), server_default="0", nullable=False))
        table.add_column(sa.Column("board_daily_limit", sa.Integer(), server_default="10", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("auto_apply_settings") as table:
        for name in (*BOARDS, "board_daily_limit"):
            table.drop_column(name)
