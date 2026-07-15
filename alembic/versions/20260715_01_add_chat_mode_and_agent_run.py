"""add chat answer mode and agent run

Revision ID: 20260715_01
Revises: 20260713_01
Create Date: 2026-07-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_01"
down_revision = "20260713_01"
branch_labels = None
depends_on = None

ANSWER_MODES = "'kb_qa', 'memory_query', 'profile_query', 'analysis_query', 'general_chat'"


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("answer_mode", sa.String(32), nullable=False, server_default="kb_qa"),
    )
    op.create_check_constraint(
        "ck_chat_sessions_answer_mode",
        "chat_sessions",
        f"answer_mode IN ({ANSWER_MODES})",
    )
    op.add_column("chat_messages", sa.Column("agent_run_id", sa.String(64), nullable=True))
    op.alter_column("chat_sessions", "knowledge_base_id", existing_type=sa.String(64), nullable=True)
    op.alter_column("chat_sessions", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=True)
    op.alter_column("chat_messages", "knowledge_base_id", existing_type=sa.String(64), nullable=True)
    op.alter_column("chat_messages", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM chat_messages WHERE knowledge_base_id IS NULL OR knowledge_base_pk IS NULL")
    op.execute("DELETE FROM chat_sessions WHERE knowledge_base_id IS NULL OR knowledge_base_pk IS NULL")
    op.alter_column("chat_messages", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("chat_messages", "knowledge_base_id", existing_type=sa.String(64), nullable=False)
    op.alter_column("chat_sessions", "knowledge_base_pk", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("chat_sessions", "knowledge_base_id", existing_type=sa.String(64), nullable=False)
    op.drop_column("chat_messages", "agent_run_id")
    op.drop_constraint("ck_chat_sessions_answer_mode", "chat_sessions", type_="check")
    op.drop_column("chat_sessions", "answer_mode")
