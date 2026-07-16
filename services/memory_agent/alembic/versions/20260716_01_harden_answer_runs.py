"""Harden answer-run idempotency, tracing, and model-attempt audit.

Revision ID: 20260716_01
Revises: 20260715_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260716_01"
down_revision: str | Sequence[str] | None = "20260715_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("answer_runs", sa.Column("trace_id", sa.String(length=64), nullable=True))
    op.add_column("answer_runs", sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "answer_runs",
        sa.Column(
            "model_attempts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("answer_runs", sa.Column("selected_provider", sa.String(length=64), nullable=True))
    op.add_column("answer_runs", sa.Column("selected_model", sa.String(length=255), nullable=True))
    op.add_column(
        "answer_runs",
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE answer_runs SET trace_id = 'legacy_' || run_id WHERE trace_id IS NULL")
    op.alter_column("answer_runs", "trace_id", nullable=False)
    op.execute(
        """
        DELETE FROM answer_runs AS duplicate
        USING answer_runs AS keeper
        WHERE duplicate.owner_id = keeper.owner_id
          AND duplicate.request_id = keeper.request_id
          AND (duplicate.created_at, duplicate.run_id) > (keeper.created_at, keeper.run_id)
        """
    )
    op.create_unique_constraint(
        "uq_answer_runs_owner_request",
        "answer_runs",
        ["owner_id", "request_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_answer_runs_owner_request", "answer_runs", type_="unique")
    op.drop_column("answer_runs", "fallback_used")
    op.drop_column("answer_runs", "selected_model")
    op.drop_column("answer_runs", "selected_provider")
    op.drop_column("answer_runs", "model_attempts")
    op.drop_column("answer_runs", "response_json")
    op.drop_column("answer_runs", "trace_id")
