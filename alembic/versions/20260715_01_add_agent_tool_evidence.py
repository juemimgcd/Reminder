"""add agent tool evidence to chat messages

Revision ID: 20260715_04
Revises: 20260715_03
Create Date: 2026-07-15 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_04"
down_revision = "20260715_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("tool_calls_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "tool_calls_json")
