"""add chat messages and ai model configs

Revision ID: 20260707_01
Revises: c4a7b8e2d1f3
Create Date: 2026-07-07 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_01"
down_revision: Union[str, Sequence[str], None] = "c4a7b8e2d1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _get_inspector().get_table_names()


def _get_column_names(table_name: str) -> set[str]:
    return {item["name"] for item in _get_inspector().get_columns(table_name)}


def upgrade() -> None:
    if _has_table("chat_sessions"):
        columns = _get_column_names("chat_sessions")
        if "message_count" not in columns:
            op.add_column(
                "chat_sessions",
                sa.Column("message_count", sa.Integer(), server_default="0", nullable=False, comment="message count"),
            )
        if "last_message_at" not in columns:
            op.add_column("chat_sessions", sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True))
        if "archived_at" not in columns:
            op.add_column("chat_sessions", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_table("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.String(length=64), nullable=False, comment="message id"),
            sa.Column("session_id", sa.String(length=64), nullable=False, comment="chat session id"),
            sa.Column("user_id", sa.BigInteger(), nullable=False, comment="owner user id"),
            sa.Column("knowledge_base_id", sa.String(length=64), nullable=False, comment="knowledge base public id"),
            sa.Column("knowledge_base_pk", sa.BigInteger(), nullable=False, comment="knowledge base internal id"),
            sa.Column("role", sa.String(length=32), nullable=False, comment="user or assistant"),
            sa.Column("content", sa.Text(), nullable=False, comment="message content"),
            sa.Column("sources_json", sa.JSON(), nullable=True, comment="chat sources"),
            sa.Column("citations_json", sa.JSON(), nullable=True, comment="chat citations"),
            sa.Column("route_json", sa.JSON(), nullable=True, comment="query route"),
            sa.Column("model_config_id", sa.String(length=64), nullable=True, comment="AI model config id"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["knowledge_base_pk"], ["knowledge_bases.pk"]),
            sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_chat_messages_session_id", "chat_messages", ["session_id"])
        op.create_index("idx_chat_messages_user_id", "chat_messages", ["user_id"])
        op.create_index("idx_chat_messages_knowledge_base_pk", "chat_messages", ["knowledge_base_pk"])


def downgrade() -> None:
    if _has_table("chat_messages"):
        op.drop_index("idx_chat_messages_knowledge_base_pk", table_name="chat_messages")
        op.drop_index("idx_chat_messages_user_id", table_name="chat_messages")
        op.drop_index("idx_chat_messages_session_id", table_name="chat_messages")
        op.drop_table("chat_messages")

    if _has_table("chat_sessions"):
        columns = _get_column_names("chat_sessions")
        if "archived_at" in columns:
            op.drop_column("chat_sessions", "archived_at")
        if "last_message_at" in columns:
            op.drop_column("chat_sessions", "last_message_at")
        if "message_count" in columns:
            op.drop_column("chat_sessions", "message_count")
