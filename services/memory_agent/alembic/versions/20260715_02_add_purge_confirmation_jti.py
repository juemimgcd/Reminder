"""add purge confirmation jti

Revision ID: 20260715_02
Revises: 20260715_01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_02"
down_revision: str | None = "20260715_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_action_audit",
        sa.Column("confirmation_jti", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "uq_memory_action_audit_confirmation_jti",
        "memory_action_audit",
        ["confirmation_jti"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_memory_action_audit_confirmation_jti",
        table_name="memory_action_audit",
    )
    op.drop_column("memory_action_audit", "confirmation_jti")
