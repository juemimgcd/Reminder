"""add persisted chat answer metadata

Revision ID: 20260715_02
Revises: 20260715_01
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_02"
down_revision = "20260715_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("answer_metadata_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "answer_metadata_json")
