"""add outbox events

Revision ID: 20260526_02
Revises: 20260526_01
Create Date: 2026-05-26 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260526_02"
down_revision: Union[str, Sequence[str], None] = "20260526_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=64), nullable=False, comment="Outbox event ID"),
        sa.Column("event_type", sa.String(length=120), nullable=False, comment="Event type"),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False, comment="Aggregate type"),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False, comment="Aggregate ID"),
        sa.Column("target_backend", sa.String(length=50), nullable=False, comment="Target projection backend"),
        sa.Column("payload", sa.JSON(), nullable=False, comment="Event payload"),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False, comment="Idempotency key"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending", comment="Outbox lifecycle status"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0", comment="Attempt count"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3", comment="Max attempts"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True, comment="Next eligible dispatch time"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True, comment="Lock time"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True, comment="Processed time"),
        sa.Column("last_error", sa.Text(), nullable=True, comment="Last error"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_outbox_events_status_next_attempt", "outbox_events", ["status", "next_attempt_at"], unique=False)
    op.create_index("idx_outbox_events_backend_status", "outbox_events", ["target_backend", "status"], unique=False)
    op.create_index("idx_outbox_events_aggregate", "outbox_events", ["aggregate_type", "aggregate_id"], unique=False)
    op.create_index("idx_outbox_events_idempotency_key", "outbox_events", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_outbox_events_idempotency_key", table_name="outbox_events")
    op.drop_index("idx_outbox_events_aggregate", table_name="outbox_events")
    op.drop_index("idx_outbox_events_backend_status", table_name="outbox_events")
    op.drop_index("idx_outbox_events_status_next_attempt", table_name="outbox_events")
    op.drop_table("outbox_events")
