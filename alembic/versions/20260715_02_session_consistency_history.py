"""add agent run idempotency and persisted session summaries

Revision ID: 20260715_02
Revises: 20260715_01
Create Date: 2026-07-15 00:00:01.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_02"
down_revision = "20260715_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("agent_run_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("sequence_no", sa.BigInteger(), nullable=True),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY session_id
                       ORDER BY created_at ASC,
                                CASE role WHEN 'user' THEN 0 WHEN 'assistant' THEN 1 ELSE 2 END,
                                id ASC
                   ) AS sequence_no
            FROM chat_messages
        )
        UPDATE chat_messages AS message
        SET sequence_no = ranked.sequence_no
        FROM ranked
        WHERE message.id = ranked.id
        """
    )
    op.create_index(
        "idx_chat_messages_agent_run_id",
        "chat_messages",
        ["agent_run_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_chat_messages_agent_run_role",
        "chat_messages",
        ["agent_run_id", "role"],
    )
    op.create_unique_constraint(
        "uq_chat_messages_session_sequence",
        "chat_messages",
        ["session_id", "sequence_no"],
    )
    op.add_column(
        "chat_sessions",
        sa.Column("context_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("context_summary_through_message_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_sessions", "context_summary_through_message_id")
    op.drop_column("chat_sessions", "context_summary")
    op.drop_constraint(
        "uq_chat_messages_session_sequence",
        "chat_messages",
        type_="unique",
    )
    op.drop_constraint(
        "uq_chat_messages_agent_run_role",
        "chat_messages",
        type_="unique",
    )
    op.drop_index("idx_chat_messages_agent_run_id", table_name="chat_messages")
    op.drop_column("chat_messages", "sequence_no")
    op.drop_column("chat_messages", "agent_run_id")
