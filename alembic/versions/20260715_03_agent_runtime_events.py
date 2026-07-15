"""add durable agent runtime events

Revision ID: 20260715_06
Revises: 20260715_05
Create Date: 2026-07-15 00:00:02.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_06"
down_revision = "20260715_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runtime_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("loop_index", sa.Integer(), nullable=True),
        sa.Column("tool_call_id", sa.String(length=128), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("input_tokens", sa.BigInteger(), nullable=True),
        sa.Column("output_tokens", sa.BigInteger(), nullable=True),
        sa.Column("error_kind", sa.String(length=64), nullable=True),
        sa.Column("selected_capability_ids", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("trace_id", "run_id", "session_id", "user_id", "event_type"):
        op.create_index(
            f"idx_agent_runtime_events_{column}",
            "agent_runtime_events",
            [column],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("agent_runtime_events")
