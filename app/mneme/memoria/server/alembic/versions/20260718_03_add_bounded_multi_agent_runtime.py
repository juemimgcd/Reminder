"""Add bounded multi-agent execution audit fields.

Revision ID: 20260718_03
Revises: 20260716_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260718_03"
down_revision: str | Sequence[str] | None = "20260716_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "answer_runs",
        sa.Column(
            "execution_mode",
            sa.String(length=16),
            nullable=False,
            server_default="single",
        ),
    )
    op.add_column(
        "answer_runs",
        sa.Column(
            "role_attempts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "answer_runs",
        sa.Column(
            "budget_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "answer_runs",
        sa.Column(
            "degraded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "answer_runs",
        sa.Column("stop_reason", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_answer_runs_execution_mode",
        "answer_runs",
        "execution_mode IN ('single', 'multi')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_answer_runs_execution_mode",
        "answer_runs",
        type_="check",
    )
    op.drop_column("answer_runs", "stop_reason")
    op.drop_column("answer_runs", "degraded")
    op.drop_column("answer_runs", "budget_usage")
    op.drop_column("answer_runs", "role_attempts")
    op.drop_column("answer_runs", "execution_mode")
