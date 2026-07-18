"""add ordered durable agent stream events

Revision ID: 20260718_01
Revises: 20260715_07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_01"
down_revision: str | Sequence[str] | None = "20260715_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column(
            "last_event_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "agent_runtime_events",
        sa.Column(
            "schema_version",
            sa.String(length=16),
            nullable=False,
            server_default="2",
        ),
    )
    op.add_column(
        "agent_runtime_events",
        sa.Column("sequence", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "agent_runtime_events",
        sa.Column("agent_role", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "agent_runtime_events",
        sa.Column("phase", sa.String(length=64), nullable=True),
    )
    op.execute(
        """
        WITH ordered AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY run_id
                    ORDER BY occurred_at, id
                ) AS event_sequence
            FROM agent_runtime_events
            WHERE run_id IS NOT NULL
        )
        UPDATE agent_runtime_events AS events
        SET sequence = ordered.event_sequence
        FROM ordered
        WHERE events.id = ordered.id
        """
    )
    op.execute(
        """
        UPDATE agent_runs AS runs
        SET
            last_event_sequence = latest.sequence,
            last_event_id = latest.sequence::text
        FROM (
            SELECT run_id, max(sequence) AS sequence
            FROM agent_runtime_events
            WHERE run_id IS NOT NULL AND sequence IS NOT NULL
            GROUP BY run_id
        ) AS latest
        WHERE runs.run_id = latest.run_id
        """
    )
    op.create_index(
        "uq_agent_runtime_events_run_sequence",
        "agent_runtime_events",
        ["run_id", "sequence"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_agent_runtime_events_run_sequence",
        table_name="agent_runtime_events",
    )
    op.drop_column("agent_runtime_events", "phase")
    op.drop_column("agent_runtime_events", "agent_role")
    op.drop_column("agent_runtime_events", "sequence")
    op.drop_column("agent_runtime_events", "schema_version")
    op.drop_column("agent_runs", "last_event_sequence")
