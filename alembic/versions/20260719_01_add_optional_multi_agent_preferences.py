"""add optional multi-agent chat preferences

Revision ID: 20260719_01
Revises: 20260718_02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_01"
down_revision: str | Sequence[str] | None = "20260718_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "multi_agent_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "agent_runs",
        sa.Column(
            "execution_mode",
            sa.String(length=16),
            server_default="single",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_agent_runs_execution_mode",
        "agent_runs",
        "execution_mode IN ('single', 'multi')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_agent_runs_execution_mode", "agent_runs", type_="check")
    op.drop_column("agent_runs", "execution_mode")
    op.drop_column("chat_sessions", "multi_agent_enabled")
