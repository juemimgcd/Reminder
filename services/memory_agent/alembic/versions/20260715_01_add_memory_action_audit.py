"""add memory action audit

Revision ID: 20260715_01
Revises: 20260714_05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_01"
down_revision: str | None = "20260714_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_action_audit",
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        "ix_memory_action_audit_scope_created",
        "memory_action_audit",
        ["owner_id", "knowledge_base_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_memory_action_audit_scope_created", table_name="memory_action_audit")
    op.drop_table("memory_action_audit")
